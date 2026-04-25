# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in CivicRecords AI, please report it
responsibly so we can address it before public disclosure.

**Please do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

Email: **security@scottconverse.dev**

Include in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept code if applicable)
- The affected version(s) and component(s)
- Any suggested mitigation or fix, if known
- Your name and contact info for follow-up (optional — anonymous reports accepted)

### What to Expect

- **Acknowledgement:** within 3 business days of your report.
- **Initial assessment:** within 7 business days, including severity triage and
  whether we accept the report as a valid vulnerability.
- **Fix timeline:** depends on severity. Critical issues are prioritized for
  the next patch release. We will keep you informed of progress.
- **Credit:** with your permission, we credit reporters in the release notes
  and CHANGELOG. Anonymous reports remain anonymous.
- **Coordinated disclosure:** we ask reporters to give us a reasonable window
  (typically 90 days) to ship a fix before public disclosure. We will work
  with you on timing.

## Supported Versions

Security fixes are backported to the latest minor release line only. Older
minor versions do not receive security patches — please upgrade.

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :x:                |
| < 1.2   | :x:                |

## Scope

In scope:

- The CivicRecords AI backend (FastAPI, SQLAlchemy, worker pipelines)
- The CivicRecords AI frontend (React app)
- Official Docker images and install scripts shipped from this repo
- Configuration defaults that ship with the project

Out of scope:

- Third-party dependencies (please report upstream — we will track CVEs)
- Self-hosted operator misconfigurations (e.g., exposing the DB to the public
  internet without a firewall)
- Issues requiring physical access to a deployed instance
- Social-engineering attacks against operators or end users

Thank you for helping keep CivicRecords AI and its operators secure.
