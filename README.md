# SQLCraft

A standalone SQL practice app for business analytics, product analytics and data engineering. All 40 original questions, hints and solution explanations support English and Hinglish. SQL identifiers use English. Django provides the frontend pages and backend APIs; DuckDB executes practice SQL in a separate private runner.

The GitHub Pages site is a static question-bank demo. Hosting the full app enables verified accounts, execution, server-saved drafts and cross-device progress.

## Sections

- **Accounts:** verified email/password, optional Google sign-in, password reset/change, email management, POST sign-out and account language preferences.
- **Catalog:** 40 bilingual questions, difficulty/topic/status filters, search, schema/sample data and a learning guide.
- **Workspace:** public Run, three-dataset Submit, editor save/reset, saved drafts, result comparison, hints and explanations. Failed SQL submissions are recorded; runner outages are not graded.
- **Progress:** solved status, accepted submission rate, attempted count, UTC practice streak, resume drafts, paginated/filterable submission history and downloadable practice data. Progress reset affects only the signed-in account.
- **Deployment:** container packaging, private runner, PostgreSQL, HTTPS settings, health endpoints, CI and browser checkpoints.

The five SQL section pull requests have been integrated into `development`. Use `development` to build and host the complete application. Individual section branches remain available for review; see [checkpoint documentation](handbook/CHECKPOINTS.md). `main` remains unchanged. GitHub Pages publishes the static 40-question demo from `development` → `/docs`; it does not run accounts, progress or SQL execution.

## Local development

Python 3.12+ on Linux; use Docker on Windows for SQL resource limits.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock
export DJANGO_DEBUG=true
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createcachetable
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Visit http://127.0.0.1:8000, create an account, follow the verification link printed in the development console, and sign in. Passwords must have at least 12 characters. There is no default production account. Environment values must be exported or injected by the host; Django does not automatically read `.env`.

## Verification

```bash
DJANGO_DEBUG=true .venv/bin/python manage.py check
DJANGO_DEBUG=true .venv/bin/python manage.py makemigrations --check --dry-run
DJANGO_DEBUG=true .venv/bin/python manage.py collectstatic --noinput
DJANGO_DEBUG=true .venv/bin/python manage.py test practice
.venv/bin/python -m scripts.check_runner
python verify_offline.py
node --check static/app.js
```

CI runs the integration suite against SQLite and PostgreSQL, migrations, private-runner HTTP checks, production settings checks, and the production Docker image with a non-root constrained SQL worker. Browser checkpoints exercise the actual frontend and backend with a disposable account. The offline script validates content and SQLite-portable SQL; it does not replace DuckDB or Django checks.

Read [hosting instructions](handbook/HOSTING.md) for deployment, health probes, Google callbacks, email configuration, backups and release checks. Real Google OAuth, SMTP delivery and your hosting/network controls require testing on your selected host. No production credentials are included.

## Question references

Coverage and difficulty are informed by [LeetCode SQL 50](https://leetcode.com/studyplan/top-sql-50/), [HackerRank SQL](https://www.hackerrank.com/domains/sql), and [DataLemur](https://datalemur.com/questions). SQLCraft has no affiliation with these services. Wording, solutions and synthetic datasets are original; proprietary question statements and datasets are not copied.

To add a question, use `question(...)` in `practice/questions.py`; define English/Hinglish title, prompt, hint and explanation, exact output aliases, ordering, ties, NULL semantics and business rules. Add fixtures in `practice/fixtures.py`, independent edge-case assertions, then run the checks. Regenerate the optional Pages demo with `python -m scripts.build_pages`.

Python/pandas, DSA, contests, billing and a question-authoring CMS are outside this SQL release.

## Security and licensing

See [security design](SECURITY.md) and [contribution rules](CONTRIBUTING.md). Application source is MIT licensed; dependencies retain their upstream licenses. `requirements.lock` pins runtime dependencies; review and validate updates. Security is an ongoing process, not a guarantee of complete protection.
