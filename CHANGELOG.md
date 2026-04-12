# Changelog

All notable changes to CivicRecords AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-12

### Added
- **Design System:** shadcn/ui component library with civic design tokens (#1F5A84 primary), Inter typography scale, sidebar layout shell
- **Sidebar Navigation:** Grouped navigation (Workflow / Setup / Administration) replacing top nav bar, 44px touch targets, active page indicator
- **11 Pages:** Dashboard, Search, Requests, Request Detail, Exemptions, Sources, Ingestion, Users, Onboarding Interview, City Profile, Discovery Dashboard
- **Onboarding Interview:** 3-phase wizard (City Profile, System Identification, Gap Map) for first-time city deployment
- **City Profile API:** GET/POST/PATCH /city-profile for persistent city configuration with gap map
- **Municipal Systems Catalog:** 12 functional domains, 25+ vendor systems in bundled JSON with auto-loader on startup
- **Request Timeline:** Event history on every request with automatic logging on status transitions
- **Request Messages:** Internal/external messaging thread on each request
- **Fee Tracking:** Fee line items per request with automatic total calculation
- **Response Letter Generation:** LLM-assisted draft letters with template fallback, labeled as AI-generated draft
- **Notification Service:** Template-based notification system with queue_notification() helper, template CRUD API
- **Operational Analytics:** GET /analytics/operational with response time, deadline compliance, overdue count, status breakdown
- **Connector Framework:** Universal connector protocol (authenticate/discover/fetch/health_check) with file system implementation
- **Tier 1 PII Expansion:** Credit card (Luhn-validated), bank routing/account numbers, state-specific driver's license patterns (CO, CA, TX, NY, FL)
- **Context Manager:** Token budgeting for local LLM calls with priority-based context assembly
- **11 Request Statuses:** received, clarification_needed, assigned, searching, in_review, ready_for_release, drafted, approved, fulfilled, closed
- **StatusBadge Component:** Color+icon mapping for all statuses across request, document, and exemption domains (colorblind accessible)
- **StatCard, PageHeader, EmptyState, DataTable:** Reusable design system components with loading, empty, and error states
- **Skip-to-content Link:** Screen reader accessibility (WCAG 2.4.1)
- **Discovery Dashboard Shell:** v1.1 preview page with feature explanation

### Changed
- **UI Redesign:** All pages migrated from raw Tailwind to shadcn/ui design system with civic color tokens
- **Ingestion Filenames:** UUID prefixes stripped from display — original filenames shown
- **Timestamps:** Relative display ("3 hours ago") alongside absolute dates
- **Search Scores:** RRF scores normalized to 0-100% with visual progress bar
- **Empty States:** Smart contextual guidance instead of blank screens ("No flags reviewed yet" instead of "0.0%")
- **Request Forms:** Collapsible inline forms replaced with Dialog modals
- **Status Badges:** Color-only badges replaced with icon+color badges for accessibility
- **Navigation:** Top nav bar replaced with sidebar layout (240px fixed, 56px header)

### Fixed
- **Dockerfile.backend:** Added missing `data/` directory copy for systems catalog
- **Catalog Loader:** Graceful handling when systems_catalog.json not found (no crash on startup)
- **Sidebar Footer:** Shows user email instead of UUID (via /users/me endpoint)

### Security
- All new endpoints require role-based authentication
- All mutations audit-logged
- Notification credentials never logged or displayed after entry
- Response letters labeled as "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW"
- CJIS compliance gate designed for public safety connectors (Section 12)

## [0.1.0] - 2026-04-12

### Added
- **Foundation:** Docker Compose stack with PostgreSQL+pgvector, Redis 7.2, Ollama, FastAPI, Celery, React frontend
- **Authentication:** JWT-based auth with 4 roles (Admin, Staff, Reviewer, Read-Only) via fastapi-users
- **Service Accounts:** API key generation for federation between CivicRecords AI instances
- **Audit Logging:** Hash-chained, append-only audit log with CSV/JSON export and chain verification
- **Document Ingestion:** Two-track pipeline — 7 file type parsers (PDF, DOCX, XLSX, CSV, email, HTML, text) + Gemma 4 multimodal OCR with Tesseract fallback
- **Chunking:** Sentence-aware text chunking with configurable overlap
- **Embeddings:** nomic-embed-text via Ollama with batch support, stored in pgvector
- **Hybrid Search:** pgvector semantic similarity + PostgreSQL full-text search combined via Reciprocal Rank Fusion
- **LLM Synthesis:** Optional AI-generated answer summaries from search results (labeled as AI draft)
- **Search Sessions:** Query history tracking with iterative refinement
- **Request Tracking:** Records request lifecycle management with status workflow (received → searching → in_review → drafted → approved → sent)
- **Document Attachment:** Link search results to requests with automatic document caching for legal defensibility
- **Deadline Management:** Approaching deadline and overdue alerts on request dashboard
- **Exemption Detection:** Rules-primary engine with built-in PII patterns (SSN, phone, email, credit card, DOB) + per-state keyword rules
- **LLM Exemption Suggestions:** Optional secondary exemption detection via Ollama, confidence capped at 0.7
- **Colorado CORA Pilot:** Pre-configured exemption rules for Colorado Open Records Act categories
- **Exemption Review Workflow:** Accept/reject flags with audit trail and acceptance rate dashboard
- **Disclosure Templates:** Configurable compliance document templates (AI disclosure, response letters)
- **Model Transparency:** Admin panel showing Ollama model info (name, size, details)
- **Data Sovereignty:** Verification script confirming no outbound data transmission
- **Cross-Platform:** Windows (Docker Desktop), macOS, and Linux support with platform-specific install scripts
- **React Admin Panel:** 8 pages — Login, Dashboard, Search, Requests, Request Detail, Exemptions, Data Sources, Ingestion, Users
- **80 automated tests** covering auth, audit, search, requests, exemptions, parsers, chunking, embeddings

### Security
- All audit logs hash-chained with SHA-256 for tamper evidence
- Human-in-the-loop enforced at API layer (no auto-redaction, no auto-approval)
- All LLM outputs labeled as AI-generated drafts
- No telemetry, analytics, or outbound data transmission
- JWT secrets from environment configuration (not hardcoded)
- API keys hashed before storage (SHA-256)
