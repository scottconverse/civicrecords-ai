# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in CivicRecords AI, please report it by opening a [GitHub issue](https://github.com/scottconverse/civicrecords-ai/issues) marked with the **security** label. Do not include sensitive details in the title — keep exploit specifics in the issue body. We aim to respond within 72 hours.

For sensitive disclosures that should not be public, you may also use [GitHub's private vulnerability reporting](https://github.com/scottconverse/civicrecords-ai/security/advisories/new) (Security tab → Report a vulnerability).

---

## Supported Versions

Only the latest minor release line receives security patches. Older minor releases are not back-patched.

| Version | Supported |
|---------|-----------|
| latest minor (current `main`) | ✅ |
| previous minors | ❌ |

---

## Scope

CivicRecords AI is open-source municipal FOIA management software. In-scope vulnerabilities include:

- Authentication / authorization bypass (UserRole.PUBLIC, ADMIN, STAFF role boundaries)
- SQL injection, XSS, CSRF, SSRF in the FastAPI backend or React frontend
- Tenant isolation failures (cross-tenant data leakage)
- Encryption-at-rest weaknesses (`EncryptedJSONB`, Fernet envelope on `data_sources.connection_config`)
- Secret exposure (API keys, credentials, internal URLs in client bundles or commits)
- Dependency vulnerabilities with a viable exploitation path against this codebase

Out of scope:

- Vulnerabilities in third-party dependencies that have no exploitation path in CivicRecords AI's deployment model
- Self-hosted operator misconfiguration (weak admin passwords, unencrypted backups, public ENCRYPTION_KEY rotation)
- Issues only reproducible against unsupported, modified, or forked builds

---

## Acknowledgement Policy

Reporters who follow responsible disclosure are credited in the release notes for the patched version unless they request anonymity.
