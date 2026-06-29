# nodeManager installation

1. Copy this plugin directory to CyberPanel:

   ```bash
   sudo cp -a nodeManager /usr/local/CyberCP/nodeManager
   sudo cp pre_install post_install uninstall /usr/local/CyberCP/nodeManager/
   ```

2. Add the URL include to `/usr/local/CyberCP/CyberCP/urls.py`:

   ```python
   path('nodejs/', include(('nodeManager.urls', 'nodeManager'), namespace='nodeManager')),
   ```

3. Ensure `nodeManager` is installed as a Django app if your CyberPanel version requires explicit app registration.

4. Run installation checks:

   ```bash
   cd /usr/local/CyberCP/nodeManager
   sudo bash pre_install
   sudo bash post_install
   ```

5. Run migrations:

   ```bash
   sudo /usr/local/CyberCP/bin/python /usr/local/CyberCP/manage.py migrate nodeManager
   ```

If plugin migrations are unavailable in the target CyberPanel installation, create the two tables from `nodeManager/migrations/0001_initial.py` manually or run `manage.py sqlmigrate nodeManager 0001` on a compatible staging server and apply the generated SQL.

6. Restart CyberPanel:

   ```bash
   sudo systemctl restart lscpd
   ```

7. Visit:

   ```text
   https://<panel-host>:8090/nodejs/
   ```

## Uninstall

Run:

```bash
sudo bash /usr/local/CyberCP/nodeManager/uninstall
```

The uninstall script intentionally does not remove user app files, PM2 processes, OLS proxy blocks, or database records without an explicit manual cleanup decision.
