import json
import os
import shlex
import subprocess


RUN_AS_HELPER = "/usr/local/CyberCP/nodeManager/bin/node_manager_run_as_user"
HELPER_SETUP_ERROR = (
    "nodeManager run-as-user helper is not installed at %s. "
    "Run sudo bash post_install from the installed plugin directory and restart lscpd."
) % RUN_AS_HELPER
SUBPROCESS_TEXT_KWARGS = {"text": True, "encoding": "utf-8", "errors": "replace"}


def _run_as_user(linux_user, args, cwd=None, env=None, timeout=300):
    if os.path.exists(RUN_AS_HELPER):
        command_args = args
        if env:
            command_args = ["env"] + ["%s=%s" % (key, value) for key, value in sorted(env.items())] + args
        command = ["sudo", "-n", RUN_AS_HELPER, linux_user, cwd or "-"] + command_args
        result = subprocess.run(
            command,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **SUBPROCESS_TEXT_KWARGS,
            timeout=timeout,
        )
        return result.returncode, result.stdout
    return 1, HELPER_SETUP_ERROR


def _command_exists(linux_user, command):
    code, _output = _run_as_user(linux_user, ["sh", "-lc", "command -v %s" % shlex.quote(command)], timeout=30)
    return code == 0


def _low_priority_process_args(linux_user, executable, command_args):
    if not _command_exists(linux_user, "nice"):
        return executable, command_args
    return "nice", ["-n", "10", executable] + command_args


def command_to_pm2_args(command):
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Empty start command.")
    executable = parts[0]
    args = parts[1:]
    return executable, args


def start_app(app, linux_user):
    executable, command_args = command_to_pm2_args(app.start_command)
    executable, command_args = _low_priority_process_args(linux_user, executable, command_args)
    env = {"PORT": str(app.port), "HOST": "127.0.0.1", "NODE_ENV": "production"}
    delete_app(app, linux_user)
    args = [
        "pm2",
        "start",
        executable,
        "--name",
        app.pm2_name,
        "--cwd",
        app.app_root,
        "--instances",
        "1",
        "--max-restarts",
        "5",
        "--min-uptime",
        "10s",
    ]
    if app.memory_limit:
        args += ["--max-memory-restart", app.memory_limit]
    if command_args:
        args += ["--"] + command_args
    return _run_as_user(linux_user, args, cwd=app.app_root, env=env, timeout=120)


def stop_app(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "stop", app.pm2_name], timeout=60)


def restart_app(app, linux_user):
    return start_app(app, linux_user)


def delete_app(app, linux_user):
    code, output = _run_as_user(linux_user, ["pm2", "jlist"], timeout=60)
    if code != 0:
        return _run_as_user(linux_user, ["pm2", "delete", app.pm2_name], timeout=60)
    try:
        processes = json.loads(output or "[]")
    except ValueError:
        return _run_as_user(linux_user, ["pm2", "delete", app.pm2_name], timeout=60)
    pm_ids = [
        str(process.get("pm_id"))
        for process in processes
        if process.get("name") == app.pm2_name and process.get("pm_id") is not None
    ]
    if not pm_ids:
        return 0, "No PM2 process named %s exists." % app.pm2_name
    return _run_as_user(linux_user, ["pm2", "delete"] + pm_ids, timeout=120)


def get_status(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "describe", app.pm2_name], timeout=60)


def get_logs(app, linux_user, lines=200):
    return _run_as_user(linux_user, ["pm2", "logs", app.pm2_name, "--lines", str(lines), "--nostream"], timeout=60)


def save_pm2(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "save"], timeout=60)
