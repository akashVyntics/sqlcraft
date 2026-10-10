# Security

Use Django session cookies with HttpOnly/Secure and CSRF protection; keep allauth verification and throttling enabled. Private APIs require a verified account and scope records to that account. Dynamic UI text is inserted using `textContent`; HTML templates escape submitted SQL. CSP prevents arbitrary scripts and framing. Data exports contain only the authenticated account's practice data.

The judge parses one read-only query, rejects external table/file access, checks bounded runner responses, and compares exact aliases/order/duplicate rows with numerical tolerance. Queries execute in disposable DuckDB processes without application credentials. The production runner must also be isolated by container/network/OS controls. A subprocess or SQL parser alone is not a complete security boundary against engine vulnerabilities.

Keep dependencies and base images patched, configure ingress rate limits, restrict staff accounts, rotate credentials after exposure, and verify backups. Do not place the runner on a public endpoint. CI fixtures are non-production credentials.

For suspected vulnerabilities, use GitHub private vulnerability reporting if enabled for the repository, or contact the owner privately. Do not publish active credentials or account data in public issues. No application is guaranteed completely secure; external penetration testing and hosting configuration review remain valuable before a public launch.
