# nodeManager

`nodeManager` is a CyberPanel Django plugin that adds a client-facing Node.js application manager, similar in intent to cPanel's "Setup Node.js App" feature.

The plugin lets CyberPanel users manage Node.js apps for domains they own, while administrators retain global visibility and control.

## Status

This project is an MVP implementation and should be validated on a staging CyberPanel server before live customer use.

The local repository has been syntax-checked, but the following behaviors must be verified on the target CyberPanel/OpenLiteSpeed environment:

- CyberPanel app registration and `/nodejs/` routing
- Django migration behavior for third-party plugins
- PM2 execution as the website Linux user
- `sudo` permissions for Git, PM2, ownership changes, and OpenLiteSpeed reloads
- OpenLiteSpeed reverse proxy syntax on the installed OLS version
- End-to-end client and administrator permission boundaries

## Features

- Client dashboard at `/nodejs/`
- Admin dashboard at `/nodejs/admin/`
- Admin settings at `/nodejs/settings/`
- Per-user domain ownership enforcement
- Create Node.js apps from Git repositories
- Optional application folder selection relative to the website home directory
- Configurable package manager, install command, build command, and start command
- Environment variable editor with key validation
- Internal port allocation from a configurable range
- PM2 start, stop, restart, delete, and log retrieval
- OpenLiteSpeed reverse proxy configuration to `127.0.0.1:<internal_port>`
- Marker-based vhost config updates with backups

## CyberPanel Integration

The implementation follows CyberPanel patterns found in the public CyberPanel source:

- Current user resolution uses `request.session['userID']`.
- Users and roles come from `loginSystem.models.Administrator`.
- Website ownership comes from `websiteFunctions.models.Websites.admin`.
- Child domains come from `websiteFunctions.models.ChildDomains`.
- Website Linux users come from `Websites.externalApp`.
- OpenLiteSpeed vhost configs are expected at `/usr/local/lsws/conf/vhosts/<domain>/vhost.conf`.

Detailed inspection notes are in [docs/CYBERPANEL_FINDINGS.md](docs/CYBERPANEL_FINDINGS.md).

## Installation

Copy the Django app package into CyberPanel:

```bash
sudo mkdir -p /usr/local/CyberCP/nodeManager
sudo cp -a /home/nodeManager/nodeManager/nodeManager/. /usr/local/CyberCP/nodeManager/
sudo cp -a /home/nodeManager/nodeManager/docs /usr/local/CyberCP/nodeManager/
sudo cp -a /home/nodeManager/nodeManager/README.md /usr/local/CyberCP/nodeManager/
sudo cp -a /home/nodeManager/nodeManager/pre_install /usr/local/CyberCP/nodeManager/
sudo cp -a /home/nodeManager/nodeManager/post_install /usr/local/CyberCP/nodeManager/
sudo cp -a /home/nodeManager/nodeManager/uninstall /usr/local/CyberCP/nodeManager/
sudo mkdir -p /usr/local/CyberCP/static/nodeManager
sudo cp -a /home/nodeManager/nodeManager/static/nodeManager/. /usr/local/CyberCP/static/nodeManager/
```

The installed layout should include:

```text
/usr/local/CyberCP/nodeManager/post_install
/usr/local/CyberCP/nodeManager/apps.py
/usr/local/CyberCP/nodeManager/static/nodeManager/nodeManager.css
/usr/local/CyberCP/static/nodeManager/nodeManager.css
```

Register the Django app in `/usr/local/CyberCP/CyberCP/settings.py`:

```python
'nodeManager.apps.NodeManagerConfig',
```

Add the URL include in `/usr/local/CyberCP/CyberCP/urls.py`:

```python
path('nodejs/', include(('nodeManager.urls', 'nodeManager'), namespace='nodeManager')),
```

Run checks and migrations:

```bash
cd /usr/local/CyberCP
sudo /usr/local/CyberCP/bin/python manage.py check
sudo /usr/local/CyberCP/bin/python manage.py migrate nodeManager
sudo /usr/local/CyberCP/bin/python manage.py showmigrations nodeManager
```

Expected migration state:

```text
nodeManager
 [X] 0001_initial
```

Restart CyberPanel:

```bash
sudo systemctl restart lscpd
```

Full installation notes are in [docs/INSTALLATION.md](docs/INSTALLATION.md).

If `/static/nodeManager/nodeManager.css` or `/static/nodeManager/nodeManager.js` returns HTML or 404, rerun:

```bash
cd /usr/local/CyberCP/nodeManager
sudo bash post_install
ls -l /usr/local/CyberCP/static/nodeManager/nodeManager.css
ls -l /usr/local/CyberCP/static/nodeManager/nodeManager.js
```

## Security Model

`nodeManager` does not trust hidden form fields or client-submitted domain/app IDs. Server-side checks are performed for every page and action.

Important constraints:

- Normal users can only see domains and apps they own.
- Resellers are limited to their own and child-account domains where CyberPanel ownership supports it.
- Administrators can see and manage all apps.
- App roots are constrained under `/home/<website.domain>/nodejs`.
- Node apps are intended to run through PM2 as `Websites.externalApp`, not root.
- User-controlled commands must match allow-lists and pass blocked-token checks.
- Node apps bind internally and are exposed through OpenLiteSpeed reverse proxy only.

More detail is in [docs/SECURITY.md](docs/SECURITY.md).

## Testing

Use [docs/TESTING_CHECKLIST.md](docs/TESTING_CHECKLIST.md) before enabling the plugin for real hosting clients.

Minimum staging checks:

```bash
cd /usr/local/CyberCP
sudo /usr/local/CyberCP/bin/python manage.py check
sudo /usr/local/CyberCP/bin/python manage.py showmigrations nodeManager
```

Then verify:

- Normal user can access `/nodejs/`.
- Normal user only sees owned domains.
- Manual POST attempts for another user's domain/app are rejected.
- A public Git app deploys, installs, starts with PM2, and is reachable through OpenLiteSpeed.
- Logs are visible only to the owner or admin.
- Delete removes the PM2 process and proxy block without deleting app files.

## Uninstall

Run:

```bash
sudo bash /usr/local/CyberCP/nodeManager/uninstall
```

The uninstall script intentionally does not delete customer app files, PM2 processes, OpenLiteSpeed proxy blocks, or database records without explicit manual cleanup.

## Known Limitations

- No Docker mode.
- No GitHub webhook deploys.
- No rollback support.
- No private Git SSH key manager.
- No nvm or per-app Node version management.
- PM2 startup persistence may need distribution-specific service setup.
- OpenLiteSpeed proxy syntax must be validated against the target server version before production use.
