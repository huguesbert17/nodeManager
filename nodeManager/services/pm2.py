import os
import shlex
import subprocess


def _run_as_user(linux_user, args, cwd=None, env=None, timeout=300):
    command = ["sudo", "-u", linux_user] + args
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def command_to_pm2_args(command):
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Empty start command.")
    executable = parts[0]
    args = parts[1:]
    return executable, args


def start_app(app, linux_user):
    executable, command_args = command_to_pm2_args(app.start_command)
    env = {"PORT": str(app.port), "HOST": "127.0.0.1", "NODE_ENV": "production"}
    args = ["pm2", "start", executable, "--name", app.pm2_name, "--cwd", app.app_root]
    if command_args:
        args += ["--"] + command_args
    return _run_as_user(linux_user, args, cwd=app.app_root, env=env, timeout=120)


def stop_app(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "stop", app.pm2_name], timeout=60)


def restart_app(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "restart", app.pm2_name, "--update-env"], cwd=app.app_root, timeout=120)


def delete_app(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "delete", app.pm2_name], timeout=60)


def get_status(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "describe", app.pm2_name], timeout=60)


def get_logs(app, linux_user, lines=200):
    return _run_as_user(linux_user, ["pm2", "logs", app.pm2_name, "--lines", str(lines), "--nostream"], timeout=60)


def save_pm2(app, linux_user):
    return _run_as_user(linux_user, ["pm2", "save"], timeout=60)
