from . import pm2
from .users import get_linux_user, get_primary_website


def get_pm2_logs(app, lines=200):
    website = get_primary_website(app.domain)
    code, output = pm2.get_logs(app, get_linux_user(website), lines=lines)
    if code != 0:
        return output or "Unable to read PM2 logs."
    return output


def append_deploy_log(app, message):
    app.deploy_log = ("%s\n%s" % (app.deploy_log or "", message)).strip()[-60000:]
    app.save(update_fields=["deploy_log", "updated_at"])
