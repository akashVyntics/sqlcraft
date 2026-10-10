# SQL release checkpoints

Each section is a separate branch. Branches are stacked so the final one includes the previous sections. Review/merge in this order, targeting `development` once the previous section has been integrated. Do not merge a later pull request into its parent feature branch and accidentally lose its review history.

| Section | Branch | Checkpoint |
| --- | --- | --- |
| Accounts | `section/accounts` | Settings/preferences; password change/reset; verified email enforcement; sign-out and user isolation |
| Catalog | `section/catalog` | 40 original bilingual questions; topic/difficulty/status search; learning guide; product-funnel and NULL/tie edge cases |
| Workspace | `section/workspace` | Explicit draft controls; query/result handling; failed submission records; malformed/partial runner responses; resource/time limits |
| Progress | `section/progress` | Account-scoped paginated history, filters, metrics, draft resume, streak and streamed export |
| Deployment | `section/deployment` | SQLite/PostgreSQL tests, real private-runner HTTP, production image, migration/configuration checks and full browser journey |

The first four branches run Application checks. The final branch additionally runs the expanded database/container suite and Browser checkpoints. When previous branches merge, retarget the next pull request to `development`. `main` and the Pages deployment remain unchanged during section review.

Production account/provider checks remain host-dependent. Refer to HOSTING.md for real SMTP/OAuth, TLS, ingress limits, backup restore and container network checks. Those are deployment prerequisites, not claims that CI has tested your external services.
