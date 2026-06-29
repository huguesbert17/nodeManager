from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from plogical.httpProc import httpProc

from .forms import NodeAppCreateForm, NodeManagerSettingsForm
from .models import NodeApp, NodeManagerSettings
from .services import deploy, openlitespeed, pm2
from .services.logs import get_pm2_logs
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
    form = NodeAppCreateForm(request.POST or None, domains=domains, settings_obj=settings_obj)
    if request.method == "POST" and form.is_valid():
        domain = form.cleaned_data["domain"]
        if not can_manage_domain(user, domain):
            return HttpResponseForbidden("You cannot manage this domain.")
        active_count = NodeApp.objects.exclude(status=NodeApp.STATUS_DELETED).filter(owner_user_id=user.pk).count()
        if not is_admin(user) and active_count >= settings_obj.max_apps_per_user:
            form.add_error(None, "Maximum Node.js applications reached.")
        else:
            website = get_primary_website(domain)
            app_name = form.cleaned_data["app_name"]
            app_root = deploy.build_app_root(website, domain, app_name)
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
                pm2_name=deploy.make_pm2_name(user.userName, domain, app_name),
            )
            try:
                deploy.deploy_app(app, env_text=form.cleaned_data["environment"])
                messages.success(request, "Node.js application created and deployed.")
                return redirect("nodeManager:detail", app_id=app.pk)
            except Exception:
                messages.error(request, "Deployment failed. Review the application detail and logs.")
                return redirect("nodeManager:detail", app_id=app.pk)
    return render_cp(request, "nodeManager/create.html", {"form": form})


@cyberpanel_login_required
def detail(request, app_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, pk=app_id)
    if not can_view_node_app(user, app):
        return HttpResponseForbidden("You cannot view this application.")
    return render_cp(request, "nodeManager/detail.html", {"app": app, "is_admin": is_admin(user)})


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


def _get_action_app(request, app_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, pk=app_id)
    if not can_manage_node_app(user, app):
        return None, HttpResponseForbidden("You cannot manage this application.")
    return app, None


@cyberpanel_login_required
@require_POST
def start(request, app_id):
    app, error = _get_action_app(request, app_id)
    if error:
        return error
    website = get_primary_website(app.domain)
    code, output = pm2.start_app(app, get_linux_user(website))
    app.deploy_log = ("%s\n%s" % (app.deploy_log or "", output)).strip()[-60000:]
    app.status = NodeApp.STATUS_RUNNING if code == 0 else NodeApp.STATUS_ERROR
    app.last_error = "" if code == 0 else "PM2 start failed."
    app.save()
    return redirect("nodeManager:detail", app_id=app.pk)


@cyberpanel_login_required
@require_POST
def stop(request, app_id):
    app, error = _get_action_app(request, app_id)
    if error:
        return error
    website = get_primary_website(app.domain)
    code, output = pm2.stop_app(app, get_linux_user(website))
    app.deploy_log = ("%s\n%s" % (app.deploy_log or "", output)).strip()[-60000:]
    app.status = NodeApp.STATUS_STOPPED if code == 0 else NodeApp.STATUS_ERROR
    app.last_error = "" if code == 0 else "PM2 stop failed."
    app.save()
    return redirect("nodeManager:detail", app_id=app.pk)


@cyberpanel_login_required
@require_POST
def restart(request, app_id):
    app, error = _get_action_app(request, app_id)
    if error:
        return error
    website = get_primary_website(app.domain)
    code, output = pm2.restart_app(app, get_linux_user(website))
    app.deploy_log = ("%s\n%s" % (app.deploy_log or "", output)).strip()[-60000:]
    app.status = NodeApp.STATUS_RUNNING if code == 0 else NodeApp.STATUS_ERROR
    app.last_error = "" if code == 0 else "PM2 restart failed."
    app.save()
    return redirect("nodeManager:detail", app_id=app.pk)


@cyberpanel_login_required
@require_POST
def redeploy(request, app_id):
    app, error = _get_action_app(request, app_id)
    if error:
        return error
    try:
        deploy.deploy_app(app)
        messages.success(request, "Application redeployed.")
    except Exception:
        messages.error(request, "Redeploy failed.")
    return redirect("nodeManager:detail", app_id=app.pk)


@cyberpanel_login_required
def logs(request, app_id):
    user = get_current_cyberpanel_user(request)
    app = get_object_or_404(NodeApp, pk=app_id)
    if not can_view_logs(user, app):
        return HttpResponseForbidden("You cannot view these logs.")
    pm2_logs = get_pm2_logs(app, lines=200)
    return render_cp(request, "nodeManager/logs.html", {"app": app, "pm2_logs": pm2_logs})


@cyberpanel_login_required
@require_POST
def delete(request, app_id):
    app, error = _get_action_app(request, app_id)
    if error:
        return error
    website = get_primary_website(app.domain)
    pm2.delete_app(app, get_linux_user(website))
    openlitespeed.remove_reverse_proxy(app)
    openlitespeed.reload_litespeed()
    app.status = NodeApp.STATUS_DELETED
    app.save(update_fields=["status", "updated_at"])
    messages.success(request, "Application removed from Node Manager. Files were left on disk.")
    return redirect("nodeManager:index")
