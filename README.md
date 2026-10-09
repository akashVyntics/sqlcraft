# SQLCraft

SQL-first practice application with original business, analytics and data-engineering questions. Every question, hint and solution explanation has English and Hinglish variants. SQL identifiers remain in English in both modes.

## Current status

The source has been implemented. It has **not been deployed or runtime-verified** in this workspace: dependency installation could not complete because network access was unavailable. Python compilation, JavaScript syntax and dependency-free curriculum checks can run locally. The included Django/DuckDB integration tests must pass before launch. Google OAuth, email delivery and production hosting are not configured.

This is a first implementation, not a security certification. No application can be guaranteed 100% secure.

## Implemented behavior

- 24 questions: 6 basic, 7 intermediate, 5 advanced analytics, 6 data-engineering scenarios.
- Difficulty/status filters, search and English/Hinglish switching.
- Public schema and complete sample-data preview.
- SQL editor, server-saved drafts, Run and Submit, result comparison, hints and explained solutions.
- Server-side answer checking across one public and two additional test datasets. Different queries can pass; exact output columns and requested ordering matter. Run does not mark a question solved.
- Email/password accounts with mandatory email verification, password-reset support and POST sign-out.
- Google OAuth integration, shown only when configured. No automatic account linking solely on a matching email address.
- Per-account solved status, attempt counts and recent submissions, persisted in the server database.
- Explicit progress deletion, limited to the authenticated account.
- Framework-admin access for staff. Questions live in a structured Python content module; a question-authoring web UI is not included.

## Local setup (Linux / macOS)

Python 3.12+ is recommended. SQL worker resource limits and production runner packaging require Linux; use Docker for Windows.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.in
export DJANGO_DEBUG=true
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createcachetable
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000`. Register an email and password; local verification/reset emails are printed to the server console. Follow the verification link and sign in. A minimum 12-character password is required. No default user or administrator password is created.

Environment variables must actually be exported by the shell or injected by the hosting system; `.env.example` is documentation, and Django does not automatically load it. Do not commit `.env`, database files, OAuth secrets or SMTP credentials.

Only local development may run the SQL child process inside the application container. Production execution requires the separate runner service.

## Checks

```bash
python verify_offline.py
python -m compileall -q config practice manage.py runner.py
node --check static/app.js
DJANGO_DEBUG=true .venv/bin/python manage.py check
DJANGO_DEBUG=true .venv/bin/python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=true .venv/bin/python manage.py test practice
```

The offline script checks all 24 bilingual records and runs 20 SQL-portable solutions unchanged against SQLite on three fixtures. Four DuckDB-specific date queries are skipped. It is a curriculum smoke check, not evidence of DuckDB or authentication correctness.

The integration suite covers reference SQL, write/file-access rejection, result limits, cross-account isolation, CSRF, unverified email login, redirects, private APIs, draft ownership, hidden-data checking and API rate limits. Run it before deployment. Google consent and callback need an end-to-end test with your real OAuth configuration.

After the first successful installation, generate and review an exact dependency lock with `pip freeze > requirements.lock`. Use that reviewed lock in CI and production instead of floating ranges. Monitor dependency security updates.

## Configure Google sign-in

Create a Google OAuth web client, then inject `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` server-side. Configure the exact callback:

```text
https://YOUR_DOMAIN/accounts/google/login/callback/
```

For local testing add `http://127.0.0.1:8000/accounts/google/login/callback/` as a separate callback. Configure the Google consent screen and test users as required by Google. Secrets never go into browser JavaScript. OAuth account connections should be tested before public launch.

## Production deployment

The Sites publishing helpers are not installed in this workspace, and Sites' provided authentication uses ChatGPT rather than the standard Google/email accounts requested here. This standalone Django application needs Python/container hosting. No hosting account was created and no paid service was enabled.

1. Select a free hosting plan that supports this workload, plus a durable database and an email service. Check current plan limits; open-source software does not make unlimited compute or email free. Free plans may sleep, cap usage or lack persistent storage.
2. Prefer PostgreSQL for a hosted multi-worker deployment. Set `DATABASE_URL`, HTTPS origins, a random `DJANGO_SECRET_KEY`, SMTP configuration and optional Google credentials. SQLite is suitable for local development; a hosted SQLite file requires a durable volume and suitable backup/locking behavior.
3. Run SQL in the private `runner` container from `compose.yaml`. Give the runner no application database access, SMTP credentials, Google credentials or public port. Its network is internal, filesystem read-only, capabilities removed, and process/memory/CPU constrained. Inject a random shared `SQL_RUNNER_TOKEN` of at least 32 characters into app and runner. Never accept the token from a visitor.
4. Put a trusted HTTPS reverse proxy in front of the app. It must discard user-supplied forwarded headers before setting its own; only then use `TRUST_PROXY_HTTPS=true`. Do not expose the app's upstream port publicly.
5. Use the configured application environment to run `python manage.py migrate`, `python manage.py createcachetable`, `python manage.py check --deploy`, and the integration suite. Create a staff account only if needed. Collectstatic runs during the Docker image build.
6. Configure backups, test restore, monitor rate/error logs, and test two separate accounts on the hosted app. Verify email delivery, Google callback and persistence across app restarts.

The supplied Compose topology assumes secrets are injected from the host environment. Database and SMTP are external. Container builds and live hosting were not tested here.

## Security design and limits

- Django sessions use HttpOnly cookies; production requires Secure cookies, HTTPS redirects and HSTS. CSRF protects mutating browser actions. CSP restricts script sources; UI inserts dynamic text through `textContent`.
- Passwords use Django's password hashers and validators. django-allauth owns login, email confirmation and reset flows, with authentication throttling and enumeration protection. Never disable verification to make setup easier.
- Every learner-data query is scoped to the server-authenticated user. Supplied `user_id` values are ignored. Anonymous private API requests fail.
- SQL is parsed as one read-only query. Mutations, external tables and table functions are rejected. DuckDB external access is disabled; it uses a disposable in-memory database with no application credentials, output limits, engine-memory limits, CPU time limits and a wall-clock timeout.
- The production runner container is an additional boundary. A Python subprocess alone is not a complete OS security sandbox; parser checks are not protection against engine vulnerabilities. Keep DuckDB patched and review container/network isolation before accepting public traffic. Container memory/CPU limits constrain the runner as a whole.
- Rate limits reduce abuse, but do not replace hosting-level protections against distributed attacks. Review and configure trusted client-IP handling with the selected reverse proxy for authentication throttling.
- These are small practice fixtures, not warehouse-scale production performance tests. Test datasets are server-owned but finite; they cannot prove arbitrary SQL correct on every possible input.
- The first version has no paid APIs, AI grading, public leaderboard, contests, Python execution, subscription system or question-editor UI. Accounts and progress do not become available across devices until the server and durable database are hosted.

## Question authoring

Add a `question(...)` entry in `practice/questions.py`. Provide both language variants for title, prompt, hint and explanation; provide a reference SQL query, level, topic and tables. State output aliases, ordering, ties, NULL behavior, date boundaries and business definitions explicitly. Add scenario datasets in `practice/fixtures.py` and rerun the tests. No proprietary interview question content was copied.

## Technology

Django and django-allauth handle accounts; DuckDB and SQLGlot handle practice SQL; vanilla HTML/CSS/JavaScript handle the interface. WhiteNoise serves static assets and Gunicorn serves the application. These dependencies are open source; their upstream licenses still apply.
