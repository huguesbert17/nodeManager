# nodeManager installation

1. Copy the repository root to CyberPanel.

   If your downloaded repository is at `/home/nodeManager/nodeManager` and contains `docs`, `nodeManager`, `post_install`, `pre_install`, `README.md`, and `uninstall`, copy its contents like this:

   ```bash
   sudo mkdir -p /usr/local/CyberCP/nodeManager
   sudo cp -a /home/nodeManager/nodeManager/. /usr/local/CyberCP/nodeManager/
   ```

   After copying, the installed layout should include:

   ```text
   /usr/local/CyberCP/nodeManager/post_install
   /usr/local/CyberCP/nodeManager/pre_install
   /usr/local/CyberCP/nodeManager/nodeManager/apps.py
   /usr/local/CyberCP/nodeManager/nodeManager/static/nodeManager/nodeManager.css
   /usr/local/CyberCP/nodeManager/nodeManager/static/nodeManager/nodeManager.js
   ```

   Verify it:

   ```bash
   ls -l /usr/local/CyberCP/nodeManager/post_install
   ls -l /usr/local/CyberCP/nodeManager/nodeManager/apps.py
   ls -l /usr/local/CyberCP/nodeManager/nodeManager/static/nodeManager/nodeManager.css
   ls -l /usr/local/CyberCP/nodeManager/nodeManager/static/nodeManager/nodeManager.js
   ```

2. Register the Django app in `/usr/local/CyberCP/CyberCP/settings.py`.

   Add `nodeManager.apps.NodeManagerConfig` to `INSTALLED_APPS`:

   ```python
   INSTALLED_APPS = [
       # existing CyberPanel apps...
       'nodeManager.apps.NodeManagerConfig',
   ]
   ```

   This must be done before importing `nodeManager.urls` or running migrations. If it is missing, CyberPanel will fail while loading `/usr/local/CyberCP/CyberCP/urls.py` because `nodeManager.urls` imports views and models.

3. Add the URL include to `/usr/local/CyberCP/CyberCP/urls.py`:

   ```python
   path('nodejs/', include(('nodeManager.urls', 'nodeManager'), namespace='nodeManager')),
   ```

4. Verify CyberPanel can import the plugin:

   ```bash
   cd /usr/local/CyberCP
   sudo /usr/local/CyberCP/bin/python manage.py check
   ```

5. Run installation checks:

   ```bash
   cd /usr/local/CyberCP/nodeManager
   sudo bash pre_install
   sudo bash post_install
   ```

   `post_install` creates `/usr/local/CyberCP/static/nodeManager` and copies static assets there. If `/static/nodeManager/nodeManager.css` returns HTML or 404 in the browser, rerun `post_install` and confirm these files exist:

   ```bash
   cd /usr/local/CyberCP/nodeManager
   sudo bash post_install
   ls -l /usr/local/CyberCP/static/nodeManager/nodeManager.css
   ls -l /usr/local/CyberCP/static/nodeManager/nodeManager.js
   ```

6. Run migrations:

   ```bash
   cd /usr/local/CyberCP
   sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py migrate nodeManager
   ```

   Verify Django sees the plugin migration:

   ```bash
   sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py showmigrations nodeManager
   ```

   Expected output includes:

   ```text
   nodeManager
    [X] 0001_initial
   ```

If plugin migrations are unavailable in the target CyberPanel installation, create the two tables from `nodeManager/migrations/0001_initial.py` manually or run `manage.py sqlmigrate nodeManager 0001` on a compatible staging server and apply the generated SQL.

   If `migrate nodeManager` prints `No migrations to apply` and then warns that CyberPanel's built-in apps have model changes, that warning is not a nodeManager install failure. Do not run `makemigrations` for CyberPanel's built-in apps on a live server unless you are intentionally maintaining that CyberPanel fork. Confirm only `showmigrations nodeManager` and the `node_manager_apps` / `node_manager_settings` tables.

7. Restart CyberPanel:

   ```bash
   sudo systemctl restart lscpd
   ```

8. Visit:

   ```text
   https://<panel-host>:8090/nodejs/
   ```

## Uninstall

Run:

```bash
sudo bash /usr/local/CyberCP/nodeManager/uninstall
```

The uninstall script intentionally does not remove user app files, PM2 processes, OLS proxy blocks, or database records without an explicit manual cleanup decision.
