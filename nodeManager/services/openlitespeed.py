import os
import re
import shutil
import subprocess
from datetime import datetime

MARKER_START = "# nodeManager:start:%s"
MARKER_END = "# nodeManager:end:%s"


def get_vhost_config_path(domain):
    return "/usr/local/lsws/conf/vhosts/%s/vhost.conf" % domain


def _safe_name(app):
    raw = "%s_%s" % (app.domain, app.app_name)
    return re.sub(r"[^A-Za-z0-9_]", "_", raw)


def render_proxy_block(app, path="/"):
    name = "nodeManager_%s" % _safe_name(app)
    marker = "%s:%s" % (app.domain, app.app_name)
    return """
%s
extprocessor %s {
  type                    proxy
  address                 http://127.0.0.1:%s
  maxConns                100
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}

context %s {
  type                    proxy
  handler                 %s
  addDefaultCharset       off
}
%s
""".strip() % (MARKER_START % marker, name, app.port, path, name, MARKER_END % marker)


def backup_config(config_path):
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_path = "%s.nodeManager.%s.bak" % (config_path, stamp)
    shutil.copy2(config_path, backup_path)
    return backup_path


def upsert_reverse_proxy(app, path="/"):
    config_path = get_vhost_config_path(app.domain)
    if not os.path.exists(config_path):
        raise RuntimeError("OpenLiteSpeed vhost config does not exist: %s" % config_path)
    backup_config(config_path)
    marker = "%s:%s" % (app.domain, app.app_name)
    block = render_proxy_block(app, path=path)
    with open(config_path, "r") as handle:
        content = handle.read()
    pattern = re.compile(r"\n?# nodeManager:start:%s.*?# nodeManager:end:%s\n?" % (re.escape(marker), re.escape(marker)), re.S)
    if pattern.search(content):
        content = pattern.sub("\n" + block + "\n", content)
    else:
        content = content.rstrip() + "\n\n" + block + "\n"
    with open(config_path, "w") as handle:
        handle.write(content)


def remove_reverse_proxy(app):
    config_path = get_vhost_config_path(app.domain)
    if not os.path.exists(config_path):
        return
    backup_config(config_path)
    marker = "%s:%s" % (app.domain, app.app_name)
    pattern = re.compile(r"\n?# nodeManager:start:%s.*?# nodeManager:end:%s\n?" % (re.escape(marker), re.escape(marker)), re.S)
    with open(config_path, "r") as handle:
        content = handle.read()
    content = pattern.sub("\n", content)
    with open(config_path, "w") as handle:
        handle.write(content)


def reload_litespeed():
    candidates = [
        ["sudo", "/usr/local/lsws/bin/lshttpd", "-r"],
        ["sudo", "/usr/local/lsws/bin/lswsctrl", "restart"],
        ["sudo", "systemctl", "restart", "lsws"],
    ]
    last_output = ""
    for command in candidates:
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120)
        except OSError as exc:
            last_output = str(exc)
            continue
        last_output = result.stdout
        if result.returncode == 0:
            return True, last_output
    return False, last_output
