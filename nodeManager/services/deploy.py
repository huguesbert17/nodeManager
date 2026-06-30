import os
import shlex
import subprocess

from django.utils import timezone

from ..models import NodeApp
from . import openlitespeed, pm2
from .logs import append_deploy_log
from .users import get_app_base_dir, get_linux_user, get_primary_website
from .validation import parse_env_text


def make_pm2_name(owner_username, domain, app_name):
    safe_domain = domain.replace(".", "-")
    return "node-%s-%s-%s" % (owner_username, safe_domain, app_name)


def build_app_root(website, domain, app_name, relative_root=""):
    relative_root = (relative_root or "").strip().strip("/")
    if relative_root:
        base = os.path.realpath(os.path.join("/home", website.domain, relative_root))
        allowed = os.path.realpath(os.path.join("/home", website.domain))
    else:
        base = os.path.realpath(os.path.join(get_app_base_dir(website), domain, app_name))
        allowed = os.path.realpath(get_app_base_dir(website))
    if not base.startswith(allowed + os.sep):
        raise RuntimeError("Resolved application root is outside the allowed website directory.")
    return base


def _run(command, linux_user, cwd=None, timeout=600):
    result = subprocess.run(
        ["sudo", "-u", linux_user] + command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def _write_env_file(app, env_text, linux_user):
    if not env_text.strip():
        return ""
    env = parse_env_text(env_text)
    path = os.path.join(app.app_root, ".env")
    lines = []
    for key, value in sorted(env.items()):
        escaped = value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        lines.append('%s="%s"' % (key, escaped))
    proc = subprocess.run(
        ["sudo", "-u", linux_user, "tee", path],
        input="\n".join(lines) + "\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        append_deploy_log(app, "Unable to write .env file.")
        raise RuntimeError("Unable to write environment file.")
    _run(["chmod", "600", ".env"], linux_user, cwd=app.app_root, timeout=60)
    app.env_file_path = path
    app.save(update_fields=["env_file_path", "updated_at"])
    return path


def prepare_app_directory(app, linux_user):
    code, output = _run(["mkdir", "-p", app.app_root], linux_user, timeout=120)
    append_deploy_log(app, "$ mkdir -p %s\n%s" % (app.app_root, output))
    if code != 0:
        raise RuntimeError("Unable to create application directory as %s." % linux_user)
    _run(["chmod", "750", app.app_root], linux_user, timeout=60)


def clone_or_update(app, linux_user):
    if not app.git_url:
        return 0, "No Git repository configured."
    if os.path.exists(os.path.join(app.app_root, ".git")):
        return _run(["git", "pull", "--ff-only"], linux_user, cwd=app.app_root, timeout=300)
    branch_args = ["--branch", app.branch] if app.branch else []
    return _run(["git", "clone"] + branch_args + [app.git_url, app.app_root], linux_user, timeout=600)


def run_package_command(app, linux_user, command, status):
    if not command:
        return
    if not os.path.exists(os.path.join(app.app_root, "package.json")) and not app.git_url:
        append_deploy_log(app, "Skipped %s because no package.json exists in an empty non-Git app directory." % command)
        return
    app.status = status
    app.save(update_fields=["status", "updated_at"])
    code, output = _run(shlex.split(command), linux_user, cwd=app.app_root, timeout=900)
    append_deploy_log(app, "$ %s\n%s" % (command, output))
    if code != 0:
        raise RuntimeError("Command failed: %s" % command)


def deploy_app(app, env_text=""):
    website = get_primary_website(app.domain)
    linux_user = get_linux_user(website)
    try:
        prepare_app_directory(app, linux_user)
        code, output = clone_or_update(app, linux_user)
        append_deploy_log(app, output)
        if code != 0:
            raise RuntimeError("Git deployment failed.")
        _write_env_file(app, env_text, linux_user)
        run_package_command(app, linux_user, app.install_command, NodeApp.STATUS_INSTALLING)
        run_package_command(app, linux_user, app.build_command, NodeApp.STATUS_BUILDING)
        code, output = pm2.start_app(app, linux_user)
        append_deploy_log(app, output)
        if code != 0:
            raise RuntimeError("PM2 start failed.")
        pm2.save_pm2(app, linux_user)
        openlitespeed.upsert_reverse_proxy(app, path="/")
        ok, reload_output = openlitespeed.reload_litespeed()
        append_deploy_log(app, reload_output)
        if not ok:
            raise RuntimeError("OpenLiteSpeed reload failed.")
        app.status = NodeApp.STATUS_RUNNING
        app.last_error = ""
        app.last_deploy_at = timezone.now()
        app.save(update_fields=["status", "last_error", "last_deploy_at", "updated_at"])
    except Exception as exc:
        app.status = NodeApp.STATUS_ERROR
        app.last_error = str(exc)
        app.save(update_fields=["status", "last_error", "updated_at"])
        raise
