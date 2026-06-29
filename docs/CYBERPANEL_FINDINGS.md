# CyberPanel inspection findings

Inspected source: public `usmannasir/cyberpanel` repository, shallow clone at HEAD `59f2bf3ec90e3cf3d87a37a76f2f22fb0f726cd7`.

Required findings:

- CyberPanel version or branch: public GitHub default branch at commit `59f2bf3ec90e3cf3d87a37a76f2f22fb0f726cd7`; no local installed CyberPanel checkout was present in this workspace.
- Plugin installation mechanism found: `pluginHolder/views.py` reads installed plugin metadata from `/home/cyberpanel/plugins` and `/usr/local/CyberCP/<plugin>/meta.xml`. Example plugin directories exist at `examplePlugin` and `testPlugin`.
- Existing plugin examples found: `examplePlugin` is minimal; `testPlugin` is a richer Django plugin with models, templates, static assets, `meta.xml`, and app URLs.
- Template base used: plugin templates extend `baseTemplate/index.html`.
- URL registration method: core URLs are explicit `path(..., include(...))` entries in `CyberCP/urls.py`. A `/nodejs/` route requires adding `path('nodejs/', include('nodeManager.urls'))`.
- Permission/admin-check method: most CyberPanel code uses `request.session['userID']` to load `loginSystem.models.Administrator`. `Administrator.type == 1` is treated as admin in several modules. The richer `testPlugin` also uses Django `request.user`, but normal CyberPanel modules rely on the session.
- User/role model location: `loginSystem.models.Administrator` with fields `userName`, `type`, `owner`, and `acl`. ACL flags live in `loginSystem.models.ACL`.
- Website/domain ownership model location: `websiteFunctions.models.Websites.admin` points to `Administrator`; `websiteFunctions.models.ChildDomains.master` points to parent `Websites`.
- Linux user mapping for websites/domains: `Websites.externalApp` is used throughout website management as the Linux user for file/process operations. Main website home is commonly `/home/<website.domain>`, with public HTML under `/home/<website.domain>/public_html`.
- OpenLiteSpeed vhost config handling method: vhost configs are read and modified at `/usr/local/lsws/conf/vhosts/<domain>/vhost.conf` using helpers from `plogical.virtualHostUtilities` and direct file edits in `websiteFunctions/website.py`.
- Existing helper methods for restarting/reloading OpenLiteSpeed: `plogical.processUtilities.ProcessUtilities.restartLitespeed()` uses `systemctl restart lsws` or `/usr/local/lsws/bin/lswsctrl restart`; other code also calls `/usr/local/lsws/bin/lshttpd -r`.

Integration notes:

- This plugin uses the CyberPanel session user and `Administrator` model instead of trusting Django `request.user`.
- Normal clients only see domains returned from `Websites.admin == current_user` and child domains under those websites.
- Reseller support is conservative: users with `type == 2` can see their own domains plus websites owned by child `Administrator` records whose `owner` is the reseller id.
- App files are placed under `/home/<website.domain>/nodejs/<domain>/<app_name>` and executed as `Websites.externalApp`.
- OpenLiteSpeed edits are marker-based and backed up before modification.
