# Hosting the full application

The full frontend consists of Django-rendered HTML plus vanilla CSS/JavaScript. The backend provides accounts, session cookies and `/api/` routes. Deploy both through **one public HTTPS origin**. You can run infrastructure separately behind a gateway, but the current frontend is not an independent static SPA and does not support unrelated frontend/backend origins or cross-site cookies. This preserves secure session/CSRF behavior without exposing tokens to JavaScript.

## Services and environment

Run a public application service and a private SQL runner using the supplied Dockerfile and `compose.yaml`. Provision durable PostgreSQL and an SMTP service. Open-source software has no license fee; compute, storage and email allowances depend on your hosting provider. No paid services are activated by this repository.

Inject the names in `.env.example` using your host's secret manager. Production startup refuses missing secret keys, PostgreSQL URLs, explicit hostnames, runner URL/token, SMTP host/sender, or partially configured Google OAuth. Use independent random values for `DJANGO_SECRET_KEY` and `SQL_RUNNER_TOKEN`; the runner token must be at least 32 characters.

The runner must receive **only its runner token**, not database, SMTP, OAuth or application credentials. Keep it private, with no public port, no internet route, a read-only filesystem, no Linux capabilities, no privilege escalation, and memory/CPU/process limits. HTTP runner URLs are suitable only on a private trusted network; use HTTPS and network access controls if the runner traverses hosts. Readiness proves connectivity, not OS isolation.

## Release commands

Build one reviewed release image. In the application's configured environment run:

```bash
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py check --deploy --fail-level WARNING
```

Collectstatic runs during the image build. Run schema migrations once as a release job, not concurrently in every web process. With Compose, use `docker compose run --rm app python manage.py migrate --noinput` and equivalent release commands before starting traffic. PostgreSQL and SMTP are external services in this topology. Do not use an ephemeral SQLite file in production.

The app uses Gunicorn on port 8000. Put your host's HTTPS ingress in front of it. Permit only the trusted proxy to reach the upstream, discard incoming forwarded headers, then set the proxy's own scheme header before enabling `TRUST_PROXY_HTTPS=true`. Match `DJANGO_ALLOWED_HOSTS` to exact hostnames and `CSRF_TRUSTED_ORIGINS` to exact HTTPS origins. The Compose health probe assumes this trusted proxy configuration.

## Health and operations

- `/health/live/`: process liveness, no database/SQL query.
- `/health/ready/`: database connectivity and private runner health. Returns generic HTTP 503 on failure, without connection details.
- Runner `/health`: private, requires the runner bearer token.

Terminate probes through the HTTPS ingress or use trusted host/scheme headers internally. Restrict readiness probe frequency at the gateway. Monitor 5xx rates, readiness, runner timeouts, database storage and email failures. Application rate limits reduce abuse but are not a substitute for ingress rate limiting or DDoS controls. Database-cache authentication throttles are not guaranteed atomic across workers; set host-level authentication and query limits as well.

Enable PostgreSQL backups and test a restore into a separate database before launch. Preserve SMTP/OAuth and application secrets outside backups committed to Git. For rollback, deploy a previous image only when its schema is compatible; otherwise restore a tested backup into a separate database and switch deliberately. Do not automatically reverse migrations on production data.

## Email and Google

Set SMTP host, port, credentials, TLS and sender identity; verify delivery using a real signup and password reset on your domain. Development console mail is not a production email service.

Google OAuth is optional. Create a web OAuth client with:

```text
https://YOUR_DOMAIN/accounts/google/login/callback/
```

Inject both Google values server-side. Configure the consent screen/test users with Google. Test consent, callback, cancellation, logout and an existing-email conflict. Never enable automatic account linking solely on a matching email address. OAuth-only users can set a password from Account.

## Final host checks

Before accepting public traffic, verify real email delivery and Google callbacks, two-account isolation, CSRF rejection, draft persistence across restart, accepted/failed submissions, history, export, progress reset, TLS/proxy headers, container isolation, backup restore, and health failures. CI covers application behavior; it cannot validate your chosen host's firewall, credentials, recovery policy or ongoing security.
