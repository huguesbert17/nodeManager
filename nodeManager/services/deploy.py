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


def build_app_root(website, domain, app_name):
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
    with open(path, "w") as handle:
        for key, value in sorted(env.items()):
            escaped = value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
            handle.write('%s="%s"\n' % (key, escaped))
    os.chmod(path, 0o600)
    subprocess.run(["sudo", "chown", "%s:%s" % (linux_user, linux_user), path], check=False)
    app.env_file_path = path
    app.save(update_fields=["env_file_path", "updated_at"])
    return path


def prepare_app_directory(app, linux_user):
    os.makedirs(app.app_root, mode=0o750, exist_ok=True)
    subprocess.run(["sudo", "chown", "-R", "%s:%s" % (linux_user, linux_user), app.app_root], check=False)


def clone_or_update(app, linux_user):
    if not app.git_url:
        return 0, "No Git repository configured."
    if os.path.exists(os.path.join(app.app_root, ".git")):
        return _run(["git", "pull", "--ff-only"], linux_user, cwd=app.app_root, timeout=300)
    parent = os.path.dirname(app.app_root)
    os.makedirs(parent, mode=0o750, exist_ok=True)
    branch_args = ["--branch", app.branch] if app.branch else []
    return _run(["git", "clone"] + branch_args + [app.git_url, app.app_root], linux_user, timeout=600)


def run_package_command(app, linux_user, command, status):
    if not command:
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
