import logging

from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from plogical.httpProc import httpProc

from .forms import NodeAppCreateForm, NodeAppEditForm, NodeManagerSettingsForm
from .models import NodeApp, NodeManagerSettings
from .services import deploy, openlitespeed, pm2
from .services.logs import append_deploy_log, get_pm2_logs, sanitize_log_text
from .services.permissions import (
    can_manage_domain,
    can_manage_node_app,
    can_view_logs,
    can_view_node_app,
    cyberpanel_admin_required,
    cyberpanel_login_required,
    get_current_cyberpanel_user,
    get_domains_for_user,
    is_admin,
)
from .services.ports import reserve_port
from .services.users import get_linux_user, get_primary_website


logger = logging.getLogger(__name__)


def _deleted_value(value, suffix, max_length):
    suffix = "-deleted-%s" % suffix
    return "%s%s" % (value[: max_length - len(suffix)], suffix)


def release_deleted_app_constraints(app):
    app.app_name = _deleted_value(app.app_name, app.pk, 64)
    app.pm2_name = _deleted_value(app.pm2_name, app.pk, 180)
    app.port = -abs(app.pk)


def release_legacy_deleted_app_constraints():
    for app in NodeApp.objects.filter(status=NodeApp.STATUS_DELETED, port__gt=0):
        release_deleted_app_constraints(app)
        app.save(update_fields=["app_name", "pm2_name", "port", "updated_at"])


def relative_app_root(app):
    prefix = "/home/%s/" % app.domain
    if app.app_root.startswith(prefix):
        return app.app_root[len(prefix) :]
    return ""


def app_form_initial(app, include_environment=False):
    initial = {
        "domain": app.domain,
        "app_name": app.app_name,
        "app_root": relative_app_root(app),
        "git_url": app.git_url,
        "branch": app.branch,
        "package_manager": app.package_manager,
        "install_command": app.install_command,
        "build_command": app.build_command,
        "start_command": app.start_command,
        "memory_limit": app.memory_limit,
    }
    if include_environment:
        initial["environment"] = deploy.read_env_file(app)
    return initial


def render_cp(request, template, context=None):
    proc = httpProc(request, template, context or {}, "admin")
    return proc.render()


def visible_apps_for(user):
    qs = NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED)
    if is_admin(user):
        return qs
    domains = get_domains_for_user(user)
    return qs.filter(domain__in=domains)


@cyberpanel_login_required
def index(request):
    user = get_current_cyberpanel_user(request)
    apps = visible_apps_for(user)
    return render_cp(request, "nodeManager/index.html", {"apps": apps, "is_admin": is_admin(user)})


@cyberpanel_login_required
def create(request):
    user = get_current_cyberpanel_user(request)
    settings_obj = NodeManagerSettings.current()
    domains = get_domains_for_user(user)
    form = NodeAppCreateForm(request.POST or None, request.FILES or None, domains=domains, settings_obj=settings_obj)
    if request.method == "POST":
        if form.is_valid():
            domain = form.cleaned_data["domain"]
            if not can_manage_domain(user, domain):
                return HttpResponseForbidden("You cannot manage this domain.")
            release_legacy_deleted_app_constraints()
            active_count = NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED).filter(owner_user_id=user.pk).count()
            if not is_admin(user) and active_count >= settings_obj.max_apps_per_user:
                form.add_error(None, "Maximum Node.js applications reached.")
                messages.error(request, "Application was not created. Maximum Node.js applications reached.")
            else:
                try:
                    website = get_primary_website(domain)
                    app_name = form.cleaned_data["app_name"]
                    existing_app = NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED).filter(owner_user_id=user.pk, domain=domain, app_name=app_name).first()
                    if existing_app:
                        messages.error(request, "A Node.js application with this name already exists for this domain.")
                        return redirect("nodeManager:detail", public_id=existing_app.public_id)
                    app_root = deploy.build_app_root(website, domain, app_name, form.cleaned_data["app_root"])
                    port = reserve_port(settings_obj)
                    app = NodeApp.objects.create(
                        owner_user_id=user.pk,
                        owner_username=user.userName,
                        domain=domain,
                        website_id=website.pk,
                        app_name=app_name,
                        app_root=app_root,
                        git_url=form.cleaned_data["git_url"],
                        branch=form.cleaned_data["branch"],
                        port=port,
                        package_manager=form.cleaned_data["package_manager"],
                        install_command=form.cleaned_data["install_command"],
                        build_command=form.cleaned_data["build_command"],
                        start_command=form.cleaned_data["start_command"],
                        memory_limit=form.cleaned_data["memory_limit"],
                        pm2_name=deploy.make_pm2_name(user.userName, domain, app_name),
                    )
                except IntegrityError:
                    logger.exception("nodeManager create hit a database uniqueness constraint")
                    form.add_error(None, "Application could not be created because a matching app record or port already exists.")
                    messages.error(request, "Application was not created because a matching app record or port already exists.")
                except DatabaseError:
                    logger.exception("nodeManager create failed while writing the application record")
                    form.add_error(None, "Application could not be created. Check that nodeManager migrations are applied.")
                    messages.error(request, "Application was not created. Check that nodeManager migrations are applied.")
                except Exception:
                    logger.exception("nodeManager create failed before deployment")
                    form.add_error(None, "Application could not be created. Review the CyberPanel error logs.")
                    messages.error(request, "Application was not created.")
                else:
                    try:
                        deploy.deploy_app(app, env_text=form.cleaned_data["environment"])
                    except Exception:
                        messages.error(request, "Application record was created, but deployment failed. Review the application detail and logs.")
                        return redirect("nodeManager:detail", public_id=app.public_id)
                    messages.success(request, "Node.js application created and deployed.")
                    return redirect("nodeManager:detail", public_id=app.public_id)
        else:
            messages.error(request, "Application was not created. Fix the highlighted fields and submit again.")
    return render_cp(request, "nodeManager/create.html", {"form": form})


@cyberpanel_login_required
def detail(request, public_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, public_id=public_id)
    if not can_view_node_app(user, app):
        return HttpResponseForbidden("You cannot view this application.")
    return render_cp(request, "nodeManager/detail.html", {"app": app, "is_admin": is_admin(user)})


@cyberpanel_login_required
def edit(request, public_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, public_id=public_id)
    if not can_manage_node_app(user, app):
        return HttpResponseForbidden("You cannot manage this application.")
    settings_obj = NodeManagerSettings.current()
    domains = get_domains_for_user(user)
    if app.domain not in domains:
        domains = list(domains) + [app.domain]
    form = NodeAppEditForm(
        request.POST or None,
        request.FILES or None,
        domains=domains,
        settings_obj=settings_obj,
        lock_identity=True,
        initial=app_form_initial(app, include_environment=True),
    )
    if request.method == "POST":
        if form.is_valid():
            try:
                website = get_primary_website(app.domain)
                app.app_root = deploy.build_app_root(website, app.domain, app.app_name, form.cleaned_data["app_root"])
                app.git_url = form.cleaned_data["git_url"]
                app.branch = form.cleaned_data["branch"]
                app.package_manager = form.cleaned_data["package_manager"]
                app.install_command = form.cleaned_data["install_command"]
                app.build_command = form.cleaned_data["build_command"]
                app.start_command = form.cleaned_data["start_command"]
                app.memory_limit = form.cleaned_data["memory_limit"]
                app.save(
                    update_fields=[
                        "app_root",
                        "git_url",
                        "branch",
                        "package_manager",
                        "install_command",
                        "build_command",
                        "start_command",
                        "memory_limit",
                        "updated_at",
                    ]
                )
            except Exception:
                logger.exception("nodeManager edit failed while saving application settings")
                form.add_error(None, "Application settings could not be saved. Review the CyberPanel error logs.")
                messages.error(request, "Application settings were not saved.")
            else:
                if "save_redeploy" in request.POST:
                    try:
                        deploy.deploy_app(app, env_text=form.cleaned_data["environment"])
                    except Exception:
                        messages.error(request, "Application settings saved, but redeploy failed. Review the application detail and logs.")
                        return redirect("nodeManager:detail", public_id=app.public_id)
                    messages.success(request, "Application settings saved and redeployed.")
                else:
                    if form.cleaned_data["environment"]:
                        try:
                            deploy.write_env_file(app, form.cleaned_data["environment"])
                        except Exception:
                            messages.error(request, "Application settings saved, but .env update failed. Review the application detail and logs.")
                            return redirect("nodeManager:detail", public_id=app.public_id)
                    messages.success(request, "Application settings saved.")
                return redirect("nodeManager:detail", public_id=app.public_id)
        else:
            messages.error(request, "Application settings were not saved. Fix the highlighted fields and submit again.")
    return render_cp(request, "nodeManager/edit.html", {"form": form, "app": app})


@cyberpanel_login_required
def legacy_detail_redirect(request, app_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, pk=app_id)
    if not can_view_node_app(user, app):
        return HttpResponseForbidden("You cannot view this application.")
    return redirect("nodeManager:detail", public_id=app.public_id)


@cyberpanel_admin_required
def admin_index(request):
    apps = NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED)
    owner = request.GET.get("owner")
    domain = request.GET.get("domain")
    status = request.GET.get("status")
    if owner:
        apps = apps.filter(owner_username__icontains=owner)
    if domain:
        apps = apps.filter(domain__icontains=domain)
    if status:
        apps = apps.filter(status=status)
    return render_cp(request, "nodeManager/admin_index.html", {"apps": apps})


@cyberpanel_admin_required
def settings(request):
    settings_obj = NodeManagerSettings.current()
    form = NodeManagerSettingsForm(request.POST or None, instance=settings_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Node Manager settings saved.")
        return redirect("nodeManager:settings")
    return render_cp(request, "nodeManager/settings.html", {"form": form})


def _get_action_app(request, public_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, public_id=public_id)
    if not can_manage_node_app(user, app):
        return None, HttpResponseForbidden("You cannot manage this application.")
    return app, None


def _action_redirect(app):
    return redirect("nodeManager:detail", public_id=app.public_id)


def _short_error(value):
    value = sanitize_log_text(value).strip()
    if len(value) > 4000:
        return value[-4000:]
    return value


def _save_action_result(request, app, action_name, success_status, failure_error, code, output):
    try:
        append_deploy_log(app, output)
        if code == 0:
            app.status = success_status
            app.last_error = ""
            messages.success(request, "Application %s." % action_name)
        else:
            app.status = NodeApp.STATUS_ERROR
            detail = output.strip().splitlines()[-1] if output and output.strip() else failure_error
            app.last_error = _short_error("%s: %s" % (failure_error, detail))
            messages.error(request, failure_error)
        app.save(update_fields=["status", "last_error", "updated_at"])
    except Exception:
        logger.exception("nodeManager failed to persist PM2 action result")
        messages.error(request, "%s Review the CyberPanel error logs." % failure_error)


def _save_action_exception(request, app, message, exc):
    try:
        app.status = NodeApp.STATUS_ERROR
        app.last_error = _short_error(exc)
        append_deploy_log(app, "%s\n%s" % (message, exc))
        app.save(update_fields=["status", "last_error", "updated_at"])
    except Exception:
        logger.exception("nodeManager failed to persist PM2 action exception")
    messages.error(request, "%s Review the application logs." % message)


@cyberpanel_login_required
@require_POST
def start(request, public_id):
    app, error = _get_action_app(request, public_id)
    if error:
        return error
    try:
        website = get_primary_website(app.domain)
        code, output = pm2.start_app(app, get_linux_user(website))
        _save_action_result(request, app, "started", NodeApp.STATUS_RUNNING, "PM2 start failed.", code, output)
    except Exception as exc:
        _save_action_exception(request, app, "PM2 start failed.", exc)
    return _action_redirect(app)


@cyberpanel_login_required
@require_POST
def stop(request, public_id):
    app, error = _get_action_app(request, public_id)
    if error:
        return error
    try:
        website = get_primary_website(app.domain)
        code, output = pm2.stop_app(app, get_linux_user(website))
        _save_action_result(request, app, "stopped", NodeApp.STATUS_STOPPED, "PM2 stop failed.", code, output)
    except Exception as exc:
        _save_action_exception(request, app, "PM2 stop failed.", exc)
    return _action_redirect(app)


@cyberpanel_login_required
@require_POST
def restart(request, public_id):
    app, error = _get_action_app(request, public_id)
    if error:
        return error
    try:
        website = get_primary_website(app.domain)
        code, output = pm2.restart_app(app, get_linux_user(website))
        _save_action_result(request, app, "restarted", NodeApp.STATUS_RUNNING, "PM2 restart failed.", code, output)
    except Exception as exc:
        _save_action_exception(request, app, "PM2 restart failed.", exc)
    return _action_redirect(app)


@cyberpanel_login_required
@require_POST
def redeploy(request, public_id):
    app, error = _get_action_app(request, public_id)
    if error:
        return error
    try:
        deploy.deploy_app(app)
        messages.success(request, "Application redeployed.")
    except Exception as exc:
        messages.error(request, "Redeploy failed. Review the application logs.")
        if not app.last_error:
            app.last_error = _short_error(exc)
            app.save(update_fields=["last_error", "updated_at"])
    return _action_redirect(app)


@cyberpanel_login_required
def logs(request, public_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, public_id=public_id)
    if not can_view_logs(user, app):
        return HttpResponseForbidden("You cannot view these logs.")
    pm2_logs = get_pm2_logs(app, lines=200)
    return render_cp(request, "nodeManager/logs.html", {"app": app, "pm2_logs": pm2_logs})


@cyberpanel_login_required
@require_POST
def delete(request, public_id):
    app, error = _get_action_app(request, public_id)
    if error:
        return error
    try:
        website = get_primary_website(app.domain)
        pm2.delete_app(app, get_linux_user(website))
        openlitespeed.remove_reverse_proxy(app)
        openlitespeed.reload_litespeed()
        app.status = NodeApp.STATUS_DELETED
        app.last_error = ""
        release_deleted_app_constraints(app)
        app.save(update_fields=["status", "last_error", "app_name", "pm2_name", "port", "updated_at"])
        messages.success(request, "Application removed from Node Manager. Files were left on disk.")
        return redirect("nodeManager:index")
    except Exception as exc:
        _save_action_exception(request, app, "Application delete failed.", exc)
        return _action_redirect(app)
