CivicRecords AI
===============

Open-source, locally-hosted AI that helps American cities respond to open records requests.

CivicRecords AI runs entirely on a single machine inside your city's network -- no cloud
subscriptions, no vendor lock-in, no resident data leaving the building. It ingests your
city's documents, makes them searchable with AI-powered natural language queries, detects
potential exemptions, and manages the full request lifecycle from intake to response.


WHY THIS EXISTS
---------------

Every city in America processes open records requests (FOIA, CORA, and state equivalents).
Staff manually search file shares, email archives, and databases -- then review every
document for exemptions before release. It's slow, error-prone, and a growing burden as
request volumes increase.

No open-source tool exists for the responder side of open records at the municipal level.
CivicRecords AI fills that gap.


KEY FEATURES
------------

- AI-Powered Search: Natural language hybrid search (semantic + keyword) across all
  ingested city documents with source attribution, normalized relevance scores, and
  optional AI-generated summaries

- Document Ingestion: Automatic parsing of PDF, DOCX, XLSX, CSV, email, HTML, and text
  files. Scanned documents processed via multimodal AI (Gemma 4) with Tesseract OCR
  fallback

- Exemption Detection: Tier 1 PII detection (SSN, credit card with Luhn validation,
  phone, email, bank accounts, state-specific driver's licenses) plus per-state statutory
  keyword matching across all 50 states and DC (180 rules). Optional LLM secondary review.
  All flags require human confirmation

- Request Management: Full lifecycle tracking with 10 statuses: intake, clarification,
  assignment, search, review, drafting, approval, fulfillment, closure. Timeline,
  messaging, fee tracking, and response letter generation

- Guided Onboarding: 3-phase wizard helps cities configure their profile, identify data
  systems across 12 municipal domains, and surface coverage gaps

- Municipal Systems Catalog: Curated knowledge base of 25+ municipal software vendors
  across 12 functional domains (finance, public safety, permitting, HR, etc.) with
  discovery hints and connector templates

- Universal Connector Framework: Standardized protocol (authenticate/discover/fetch/
  health_check) for connecting to city data sources. Ships with file system, generic
  REST API (API key / Bearer / OAuth2 client-credentials / Basic auth; JSON/XML/CSV;
  page/offset/cursor pagination), and ODBC (SQL databases via pyodbc, row-as-document
  with SQL-injection guards) connectors. IMAP email, SMB/NFS, and SharePoint connectors
  on roadmap

- Scheduled Sync & Idempotent Ingestion: Per-source cron scheduling (5-field expressions
  via croniter, evaluated in UTC with local-time disclosure, rolling 7-day min-interval
  validation, 5-minute floor) with schedule_enabled pause toggle. Idempotent pipeline:
  binary sources dedup by content hash, structured REST/ODBC sources dedup by stable
  source-path with canonical JSON serialization. Concurrent-update races prevented via
  SELECT FOR UPDATE + partial UNIQUE indexes; content updates atomically replace chunks
  and embeddings in the same transaction

- Sync Failure Tracking & Circuit Breaker: Per-record failure tracking with two-layer
  retry (task-level exponential backoff + record-level per-tick retry with N=100/T=90s
  cap). Automatic circuit breaker after 5 consecutive full-run failures (sync_paused)
  with admin-feedback unpause grace period. health_status (healthy/degraded/circuit_open)
  computed live from failure counts. Admin UI: colored health badge, failed records panel
  with bulk retry/dismiss, Sync Now button with real-time polling progress

- Operational Analytics: Real-time metrics: average response time, deadline compliance
  rate, overdue requests, status breakdown

- Notification Service: Template-based notification system with SMTP email delivery via
  Celery beat (60s interval). Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME,
  SMTP_PASSWORD in .env to enable

- Compliance by Design: Hash-chained audit logs, human-in-the-loop enforcement, AI
  content labeling, data sovereignty verification. Designed for Colorado CAIA and
  50-state regulatory compliance. CJIS compliance gate for public safety connectors

- Civic Design System: Professional UI built with shadcn/ui, civic blue design tokens,
  sidebar navigation. WCAG 2.2 AA targeted (44px touch targets, skip navigation,
  icon+color status badges)

- Federation-Ready: REST API with service accounts enables future cross-jurisdiction
  record discovery between CivicRecords AI instances

- Department Access Controls: Staff are scoped to their assigned department -- they see
  only their department's requests, documents, and sources. Admins retain full visibility

- Compliance Templates: Five ready-to-use compliance documents: AI Use Disclosure,
  Response Letter Disclosure, CAIA Impact Assessment, AI Governance Policy, and Data
  Residency Attestation


QUICK START
-----------

Requirements:
  - Docker Desktop (Windows 10/11, macOS 13+) or Docker Engine (Linux)
  - 8+ CPU cores, 32 GB RAM, 50 GB free disk space
  - No internet connection required after initial setup

Windows:
  git clone https://github.com/scottconverse/civicrecords-ai.git
  cd civicrecords-ai
  .\install.ps1

macOS / Linux:
  git clone https://github.com/scottconverse/civicrecords-ai.git
  cd civicrecords-ai
  bash install.sh

First Use:
  1. Open http://localhost:8080 in your browser
  2. Sign in with the admin credentials you configured in .env
  3. Go to Sources -> Add Source -> enter a directory path to your documents
  4. Click Ingest Now -- documents are parsed, chunked, and indexed automatically
  5. Go to Search -- type a natural language query and get cited results


ARCHITECTURE
------------

   Browser (React 18 + shadcn/ui)
          |
          v
   nginx frontend (:8080)
          |
          v
   FastAPI backend (:8000)
     |       |       |
     v       v       v
  PostgreSQL  Redis  Ollama
  + pgvector  (:6379) (:11434)
  (:5432)       |
                v
           Celery Worker
           Celery Beat

7 Docker services: PostgreSQL 17 + pgvector, Redis 7.2, Ollama (local LLM), FastAPI,
Celery worker, Celery beat, nginx frontend.

Tech stack: Python 3.12, FastAPI, SQLAlchemy 2.0, React 18, shadcn/ui, Tailwind CSS,
Alembic, Celery, pgvector, nomic-embed-text, Gemma 4 (recommended).


CONFIGURATION
-------------

All configuration is via environment variables in .env:

  DATABASE_URL           PostgreSQL connection string
  JWT_SECRET             Secret key for JWT tokens (required, min 32 chars)
  FIRST_ADMIN_EMAIL      Initial admin account email
  FIRST_ADMIN_PASSWORD   Initial admin account password (required)
  OLLAMA_BASE_URL        Ollama API endpoint (default: http://ollama:11434)
  REDIS_URL              Redis connection string (default: redis://redis:6379/0)
  SMTP_HOST              SMTP server for email notifications (optional)
  SMTP_PORT              SMTP port (default: 587)
  SMTP_USERNAME          SMTP authentication username (optional)
  SMTP_PASSWORD          SMTP authentication password (optional)
  AUDIT_RETENTION_DAYS   Audit log retention period (default: 1095, 3 years)


SUPPORTED PLATFORMS
-------------------

  - Windows 10/11 (Docker Desktop)
  - macOS 13+ (Docker Desktop)
  - Ubuntu 22.04+ / Debian 12+ (Docker Engine)

All platforms use identical Docker containers -- the application runs in Linux containers
regardless of host OS.

GPU support: NVIDIA (CUDA), AMD (ROCm on Linux, DirectML on Windows), Intel (DirectML).
CPU fallback supported but slower for large document sets.


DATA SOVEREIGNTY
----------------

CivicRecords AI is designed for environments where resident data must never leave the
network:

  - Runs entirely on local hardware -- no cloud dependencies
  - No telemetry, analytics, or crash reporting
  - All LLM inference runs locally via Ollama
  - Verification script confirms no outbound connections:
      bash scripts/verify-sovereignty.sh   (Linux/macOS)
      .\scripts\verify-sovereignty.ps1     (Windows)


STATUS
------

v1.1+ -- Internal staff platform complete.

New since v1.1.0:
  - P7: Sync failure tracking, circuit breaker, SourceCard Option B layout,
    FailedRecordsPanel, Sync Now polling, 429/Retry-After cap, REST + ODBC connectors,
    cron scheduler, idempotency contract split, department scoping, compliance templates
  - 423 backend + 5 frontend automated tests passing

Roadmap:
  v1.2 -- Public-facing requester portal (submission, status tracking, notifications)
  v2.0 -- Transparency layer (open records library, reporting, federation)


DOCUMENTATION
-------------

  User Manual (PDF):   docs/civicrecords-ai-manual.pdf
  User Manual (Word):  docs/civicrecords-ai-manual.docx
  User Manual (Web):   docs/civicrecords-ai-manual.html
  Landing Page:        docs/index.html
  Canonical Spec:      docs/UNIFIED-SPEC.md
  Architecture:        docs/architecture/system-architecture.html
  CHANGELOG:           CHANGELOG.md
  Contributing:        CONTRIBUTING.md


LICENSE
-------

Apache License 2.0 -- see LICENSE file.

All dependencies use permissive (MIT, Apache 2.0, BSD) or weak-copyleft (LGPL, MPL)
licenses. No AGPL, SSPL, or BSL dependencies.

Copyright (c) 2026 CivicRecords AI Contributors
https://github.com/scottconverse/civicrecords-ai
