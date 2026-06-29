# nodeManager security notes

- Every view resolves the active CyberPanel user from `request.session['userID']`.
- Normal users can only list and submit domains owned by their `Administrator` account.
- App action endpoints reload the app record and re-check ownership server-side.
- Application roots are resolved with `realpath` and must remain below `/home/<website.domain>/nodejs`.
- PM2 and deployment commands are run with `sudo -u <Websites.externalApp>` where possible.
- Node apps are started with `HOST=127.0.0.1` and an internal port; public traffic is routed through OpenLiteSpeed.
- Client users cannot submit arbitrary commands. Commands must match global allow-lists and blocked shell tokens are rejected.
- Environment variable keys must match `^[A-Z_][A-Z0-9_]*$`.
- Git deploy only allows `https://...` and `git@...` URLs. Private key management is intentionally out of MVP scope.
- OLS vhost configs are backed up before marker-based edits.

Known limitations:

- This MVP does not manage multiple Node versions through nvm.
- This MVP does not implement private Git deploy key storage.
- PM2 startup persistence may need per-distribution tuning after `pm2 save`.
- OLS proxy syntax should be smoke-tested on the exact CyberPanel/OpenLiteSpeed build before production rollout.
