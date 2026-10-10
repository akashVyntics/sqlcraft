# SQL release checkpoints

Each SQL section was built on a separate branch and reviewed as a stacked pull request. All five pull requests are now merged into `development`, which is the integrated application branch for hosting. The individual section branches and closed pull requests preserve each checkpoint. `main` remains unchanged.

| Section | Branch | Checkpoint |
| --- | --- | --- |
| Accounts | `section/accounts` | Settings/preferences; password change/reset; verified email enforcement; sign-out and user isolation |
| Catalog | `section/catalog` | 40 original bilingual questions; topic/difficulty/status search; learning guide; product-funnel and NULL/tie edge cases |
| Workspace | `section/workspace` | Explicit draft controls; query/result handling; failed submission records; malformed/partial runner responses; resource/time limits |
| Progress | `section/progress` | Account-scoped paginated history, filters, metrics, draft resume, streak and streamed export |
| Deployment | `section/deployment` | SQLite/PostgreSQL tests, real private-runner HTTP, production image, migration/configuration checks and full browser journey |

Merged pull requests: [accounts #12](https://github.com/akashVyntics/sqlcraft/pull/12), [catalog #13](https://github.com/akashVyntics/sqlcraft/pull/13), [workspace #14](https://github.com/akashVyntics/sqlcraft/pull/14), [progress #15](https://github.com/akashVyntics/sqlcraft/pull/15), and [deployment #16](https://github.com/akashVyntics/sqlcraft/pull/16).

The integrated branch runs Application checks (46 tests on both SQLite and PostgreSQL, private-runner HTTP, migrations, production settings and a constrained non-root Docker image), Browser checkpoints, and Pages demo checks. The real CI browser journey covers accounts, preference persistence, draft save/reset/reload, Run/Submit, errors, history, export, progress and mobile widths. GitHub Pages remains a static demo; full application hosting follows HOSTING.md.

Production account/provider checks remain host-dependent. Refer to HOSTING.md for real SMTP/OAuth, TLS, ingress limits, backup restore and container network checks. Those are deployment prerequisites, not claims that CI has tested your external services.
