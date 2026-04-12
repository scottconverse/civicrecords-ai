# CivicRecords AI — Unified Design Specification

**Version:** 2.0
**Date:** April 12, 2026
**Status:** Draft for review
**Supersedes:** `docs/superpowers/specs/2026-04-11-civicrecords-ai-master-design.md` (v0.1.0 build spec)
**Incorporates:** Master Design Spec v1, Municipal Open Records UX Style Guide, Design Critique (April 2026), Context-Mode architecture patterns, Universal Discovery & Connection Architecture

---

## How to read this document

This is the single source of truth for CivicRecords AI. Every feature, data model change, design decision, and implementation detail lives here. Each feature is tagged with a phase:

- **[BUILT]** — Implemented and tested in v0.1.0
- **[REDESIGN]** — Built but needs UI/UX overhaul
- **[MVP-NOW]** — Must be added before v1.0 release
- **[v1.1]** — Next release after initial deployment
- **[v2.0]** — Future capability, architecture should not preclude it

---

## 1. Product Summary

### What It Is

Open-source, locally-hosted AI system for municipal open records request processing. Runs on commodity hardware via Docker. No cloud, no vendor lock-in, no telemetry.

### North-Star Statement

> Any resident should be able to search for public records, request what is missing, and understand the status of their request without needing insider knowledge of city government.

Staff corollary: Any records clerk should be able to triage, search, review, redact, and respond to records requests from a single calm interface without falling back to email, spreadsheets, or paper.

### What It Is Not

- Not a records management system — it indexes and searches what already exists.
- Not a legal advisor — it surfaces suggestions, staff make all decisions.
- Not a cloud service — every deployment is a sovereign instance owned by the city.
- Not a public-facing portal in v1.0 — internal staff tool first. Public portal in v1.1.

### Design Stance

Transparent, calm, accessible, and government-appropriate. Civic and competent: calmer than a startup SaaS product, but cleaner and more modern than a legacy government form portal. The aesthetic target is **trust through clarity**, not visual excitement.

### Core Design Principles

1. **Clarity over bureaucracy** — residents should not need to understand government structure to make a good request.
2. **Transparency over mystery** — statuses, timelines, costs, and next actions should always be visible.
3. **Consistency over one-off screens** — shared patterns reduce confusion and development cost.
4. **Accessibility over compliance theater** — forms and documents must be usable, not merely technically valid.
5. **Operational calm over case chaos** — staff views should help triage and decision-making, not add clutter.
6. **Human-in-the-loop always** — no auto-redaction, no auto-denial, no auto-release. Every AI output is a draft.

---

## 2. User Groups

### Staff Users (v1.0)

| User Group | Primary Need | Design Response |
|---|---|---|
| **City clerk / records officer** | Triage, route, communicate, and complete requests. | Queue views, routing rules, templates, SLA timers, full event history. |
| **Department liaison** | Provide documents and answer scoped questions quickly. | Scoped assignment view, internal notes, due dates, one-click return to records team. |
| **Legal / reviewer** | Review exemptions, redactions, and sensitive material. | Review queue, exemption tags, redaction ledger, approval state. |
| **City IT administrator** | Install, configure, and maintain the system. | Docker Compose, admin panel, model management, audit export. |

### Public Users (v1.1)

| User Group | Primary Need | Design Response |
|---|---|---|
| **Resident / first-time requester** | Submit a request without knowing the exact record title or department. | Guided request flow, plain-language examples, estimated turnaround, visible help. |
| **Journalist / researcher** | Search existing records and request additional material efficiently. | Robust search, saved filters, exportable results, request history. |

### RBAC Roles

| Role | Scope | Phase |
|---|---|---|
| `admin` | Full system access, user management, configuration | [BUILT] |
| `staff` | Request management, search, ingestion, exemption review | [BUILT] |
| `reviewer` | Read-only access plus exemption review approval | [BUILT] |
| `read_only` | View dashboards and reports only | [BUILT] |
| `liaison` | Scoped to assigned department, can attach documents and add notes | [MVP-NOW] |
| `public` | Submit requests, track own requests, search published records | [v1.1] |

---

## 3. Information Architecture

### Staff Workbench (v1.0) — 11 pages

| Page | Purpose | Phase |
|---|---|---|
| **Dashboard** | System health, operational metrics, SLA overview, coverage gaps | [REDESIGN] |
| **Search** | Hybrid RAG search across ingested documents | [REDESIGN] |
| **Requests** | Request queue with triage, routing, SLA timers | [REDESIGN] |
| **Request Detail** | Single request: details, workflow, documents, timeline, response letter | [REDESIGN] |
| **Exemptions** | Exemption rules management and flag review dashboard | [REDESIGN] |
| **Sources** | Data source configuration, file upload, and connector management | [REDESIGN] |
| **Ingestion** | Document processing status and pipeline monitoring | [REDESIGN] |
| **Users** | User management and role assignment | [REDESIGN] |
| **Onboarding** | LLM-guided city profile interview and gap map (Section 12.2) | [MVP-NOW] |
| **City Profile** | City systems inventory, gap map, and IT environment settings (Section 12.2.2) | [MVP-NOW] |
| **Discovery Dashboard** | Network scan results, confidence scoring, source confirmation (Section 12.3.3) | [v1.1] |

### Public Portal (v1.1) — 5 pages

| Page | Purpose | Phase |
|---|---|---|
| **Home** | Search bar, common categories, response-time guidance, top tasks | [v1.1] |
| **Search Records** | Published records index with filters | [v1.1] |
| **Make a Request** | Guided intake wizard with scope helper | [v1.1] |
| **Track a Request** | Public timeline, messages, delivered files, fees | [v1.1] |
| **Help & Policy** | Open records law summary, fee schedule, exemptions, contact info | [v1.1] |

### Navigation Rules

- Staff workbench: sidebar navigation (not top nav). Better for 8+ items, standard for admin panels. Active page highlighted with left border accent.
- Public portal: top navigation with no more than 6 top-level choices. Complex routing inside guided flows.
- Every page must be identifiable from peripheral vision — unique page icon, header treatment, or accent color.

---

## 4. System Architecture

### Docker Compose Stack [BUILT]

```
Services:
  1. postgres    — PostgreSQL 17 + pgvector (data, vectors, audit)
  2. redis       — Redis 7.2 (BSD license, pinned <8.0)
  3. api         — FastAPI application server (port 8000)
  4. worker      — Celery worker(s) for async ingestion/embedding/notifications
  5. beat        — Celery Beat scheduler for periodic tasks
  6. ollama      — Local LLM runtime (Gemma 4 + nomic-embed-text)
  7. frontend    — React/nginx (port 8080)
```

### Application Layer (FastAPI) [BUILT]

| Module | Responsibility | Phase |
|---|---|---|
| Auth Module | fastapi-users, JWT, RBAC, service accounts | [BUILT] |
| Search API | RAG queries, hybrid retrieval, source attribution, session context | [BUILT] |
| Workflow API | Request CRUD, status transitions, document association, deadline mgmt | [BUILT] |
| Audit Logger | Hash-chained append-only logging, CSV/JSON export | [BUILT] |
| LLM Abstraction | Model-agnostic Ollama wrapper, chat + embedding endpoints | [BUILT] |
| Exemption Engine | Rules engine (regex, keyword, statutory) + LLM suggestions | [BUILT] |
| Context Manager | Smart prompt assembly with token budgeting for local LLM | [MVP-NOW] |
| Notification Service | Email templates via Celery tasks, SMTP integration | [MVP-NOW] |
| Fee Tracking | Fee estimation, payment status, waiver management | [MVP-NOW] |
| Response Generator | Template-based response letter generation with LLM assist | [MVP-NOW] |
| Analytics API | Operational metrics, SLA compliance, workload reporting | [MVP-NOW] |
| Federation API | REST endpoints for inter-instance queries via service accounts | [BUILT] |
| Public API | Read-only endpoints for public portal with rate limiting | [v1.1] |
| Connector Framework | Universal connector protocol: authenticate/discover/fetch/health_check (Section 12.4) | [MVP-NOW] |
| Onboarding Service | LLM-guided city profile interview with catalog lookup (Section 12.2) | [MVP-NOW] |
| Discovery Engine | Network scanning, fingerprinting, confidence scoring (Section 12.3) | [v1.1] |
| Health Monitor | Heartbeat scheduler, self-healing logic, schema drift detection (Section 12.5) | [v1.1] |
| Coverage Analyzer | Cross-reference requests vs. connected sources for gap analysis (Section 12.5.3) | [v1.1] |

### Context Management for Local LLM [MVP-NOW]

Local LLMs (Ollama) have limited context windows (8K-128K tokens). Municipal documents are large. The system must be deliberate about what enters the LLM prompt.

**Architecture (adapted from context-mode patterns):**

1. **Token budget system** — Each LLM call has a configurable maximum context budget, partitioned into reserved sections:

```
Prompt Budget (example: 8192 tokens for Gemma 4)
├── System instruction:    ~500 tokens (fixed)
├── Request context:       ~500 tokens (requester, deadline, description)
├── Retrieved chunks:      ~5000 tokens (top-k from hybrid search)
├── Exemption rules:       ~500 tokens (applicable state rules)
├── Output reservation:    ~1500 tokens (response generation space)
└── Safety margin:         ~192 tokens
```

2. **Smart context assembly** — Never send raw documents. Always:
   - Pre-filter with PostgreSQL FTS (`tsvector`) for keyword relevance
   - Rank with pgvector for semantic relevance
   - Select top-k chunks that fit within budget
   - Include metadata (source filename, page number, date) but not full text of non-relevant sections

3. **Chunked processing for large documents** — When scanning a 200-page document for exemptions:
   - Process in chunk batches (e.g., 10 chunks per LLM call)
   - Aggregate results across batches
   - Use FTS as a fast pre-filter to skip chunks unlikely to contain exempt material

4. **Prompt templates** — Stored in database (`prompt_templates` table), versioned, editable by admin. Each template defines its token budget allocation.

5. **Model-aware budgeting** — Context budget reads from `model_registry` table. When the admin switches from Gemma 4 (8K) to Llama 3.3 (128K), budgets auto-adjust.

---

## 5. Data Model

### Auth & Administration [BUILT]

```
users
  id, email, hashed_password, display_name, role, department_id,
  is_active, is_verified, created_at

  role ENUM: admin, staff, reviewer, read_only, liaison    -- liaison is [MVP-NOW]
  department_id FK → departments.id (nullable)             -- [MVP-NOW]

departments                                                -- [MVP-NOW]
  id, name, code, contact_email, created_at

audit_log
  id, user_id, action, resource_type, resource_id,
  details (JSON), ip_address, previous_hash, current_hash,
  created_at

service_accounts
  id, name, api_key_hash (SHA-256), role, scopes (JSON),
  created_by, is_active
```

### Documents & Ingestion [BUILT]

```
data_sources
  id, name, type (file_share/database/email/upload/sharepoint/api),
  connection_config (encrypted JSON), schedule, status, created_by,
  discovered_source_id (FK),                               -- [MVP-NOW] Section 12
  connector_template_id (FK),                              -- [MVP-NOW] Section 12
  sync_schedule, last_sync_at, last_sync_status,           -- [MVP-NOW] Section 12
  health_status, schema_hash                               -- [v1.1] Section 12

documents
  id, source_id, source_path, filename, display_name,     -- display_name [MVP-NOW]
  file_type, file_hash (SHA-256), file_size,
  ingestion_status, ingested_at, metadata (JSON),
  department_id,                                           -- [MVP-NOW]
  redaction_status (none/pending/partial/complete),         -- [MVP-NOW] Section 12
  derivative_path, original_locked (boolean)               -- [MVP-NOW] Section 12

document_chunks
  id, document_id, chunk_index, content_text,
  embedding Vector(768), token_count

document_cache
  id, document_id, cached_file_path, file_size, cached_at
```

### Search & RAG [BUILT]

```
search_sessions
  id, user_id, created_at

search_queries
  id, session_id, query_text, filters (JSON),
  results_count, ai_summary, created_at

search_results
  id, query_id, chunk_id, similarity_score, rank,
  normalized_score                                         -- [MVP-NOW] 0-100 scale

saved_searches                                             -- [v1.1]
  id, user_id, name, query_text, filters (JSON), created_at
```

### Request Tracking [BUILT + MVP-NOW additions]

```
records_requests
  id, requester_name, requester_email, requester_phone,    -- phone [MVP-NOW]
  requester_type,                                          -- [MVP-NOW] resident/journalist/attorney/agency/other
  date_received, statutory_deadline,
  description, scope_assessment,                           -- [MVP-NOW] narrow/moderate/broad
  status, assigned_to, department_id,                      -- department_id [MVP-NOW]
  estimated_fee, fee_status, fee_waiver_requested,         -- fee fields [MVP-NOW]
  priority,                                                -- [MVP-NOW] normal/urgent/expedited
  created_by, closed_at, closure_reason

  status ENUM:
    received              -- Request logged
    clarification_needed  -- [MVP-NOW] Waiting for requester response
    assigned              -- [MVP-NOW] Routed to department liaison
    searching             -- Staff actively searching for responsive documents
    in_review             -- Documents collected, under legal/exemption review
    ready_for_release     -- [MVP-NOW] Review complete, awaiting final approval
    drafted               -- Response letter drafted
    approved              -- Supervisor approved response
    fulfilled             -- [MVP-NOW] Records delivered to requester
    closed                -- [MVP-NOW] Request closed (fulfilled, denied, withdrawn, or no responsive records)

request_documents
  id, request_id, document_id, relevance_note,
  exemption_flags (JSON),
  inclusion_status (included/excluded/pending)

request_timeline                                           -- [MVP-NOW]
  id, request_id, event_type, actor_id, actor_role,
  description, internal_note, created_at

  event_type ENUM:
    status_change, note_added, document_attached,
    document_removed, fee_updated, clarification_sent,
    clarification_received, deadline_extended,
    response_drafted, response_approved, records_released,
    request_closed

request_messages                                           -- [MVP-NOW]
  id, request_id, sender_type (staff/requester/system),
  sender_id, message_text, is_internal, created_at

response_letters                                           -- [MVP-NOW]
  id, request_id, template_id, generated_content,
  edited_content, status (draft/approved/sent),
  generated_by, approved_by, sent_at
```

### Exemption Detection [BUILT]

```
exemption_rules
  id, state_code, category, rule_type (regex/keyword/llm_prompt),
  rule_definition, enabled, created_by

exemption_flags
  id, chunk_id, rule_id, request_id, category, confidence,
  status (flagged/reviewed/accepted/rejected),
  reviewed_by, reviewed_at, review_note,                   -- review_note [MVP-NOW]
  detection_tier (1/2/3),                                  -- [MVP-NOW] Section 12
  detection_method, auto_detected (boolean)                -- [MVP-NOW] Section 12

redaction_ledger                                           -- [v1.1]
  id, request_id, document_id, page_number,
  redaction_type, exemption_basis, redacted_by, created_at
```

### Fees [MVP-NOW]

```
fee_schedules
  id, jurisdiction, fee_type (per_page/flat/hourly/waived),
  amount, description, effective_date, created_by

fee_line_items
  id, request_id, fee_schedule_id, description,
  quantity, unit_price, total, status (estimated/invoiced/paid/waived)
```

### Notifications [MVP-NOW]

```
notification_templates
  id, event_type, channel (email/in_app), subject_template,
  body_template, is_active, created_by

notification_log
  id, template_id, recipient_email, request_id,
  channel, status (queued/sent/failed), sent_at, error_message
```

### Prompt Management [MVP-NOW]

```
prompt_templates
  id, name, purpose (search_synthesis/exemption_scan/scope_assessment/
                     response_generation/clarification_draft),
  system_prompt, user_prompt_template, token_budget (JSON),
  model_id, version, is_active, created_by
```

### Compliance & Configuration [BUILT]

```
disclosure_templates
  id, template_type, state_code, content, version, updated_by

model_registry
  id, model_name, model_version, parameter_count, license,
  context_window_size, model_card_url, is_active,          -- context_window_size [MVP-NOW]
  supports_ner (boolean), supports_vision (boolean)        -- [v1.1] Section 12 redaction tier routing

published_records                                          -- [v1.1]
  id, document_id, collection_id, title, description,
  department_id, published_at, published_by

record_collections                                         -- [v2.0]
  id, name, description, topic, department_id,
  freshness_label, is_featured, created_by
```

### Analytics [MVP-NOW]

```
operational_metrics (materialized view or computed on-demand)
  - average_response_time_days
  - median_response_time_days
  - requests_by_status
  - requests_by_department
  - deadline_compliance_rate
  - clarification_frequency
  - top_request_topics
  - self_service_search_rate (v1.1, once public portal exists)
```

> **Note:** Additional tables for the Universal Discovery & Connection Architecture (city_profile, system_catalog, discovered_sources, discovery_runs, source_health_log, connector_templates, coverage_gaps) are fully defined in Section 12.9. Extended columns on data_sources, documents, exemption_flags, and model_registry are shown inline above and also listed in Appendix A.

---

## 6. Visual Design System

### Design Tokens

```json
{
  "color": {
    "brand": {
      "primary": "#1F5A84",
      "primaryLight": "#E8F0F7",
      "primaryDark": "#163D59"
    },
    "text": {
      "default": "#1F2933",
      "muted": "#5B6975",
      "inverse": "#FFFFFF"
    },
    "surface": {
      "default": "#FFFFFF",
      "subtle": "#F6F9FB",
      "border": "#C8D3DC",
      "elevated": "#FFFFFF"
    },
    "status": {
      "success": "#2B6E4F",
      "successLight": "#E6F4ED",
      "warning": "#8A5A0A",
      "warningLight": "#FEF3E2",
      "danger": "#8B2E2E",
      "dangerLight": "#FBE9E9",
      "info": "#1F5A84",
      "infoLight": "#E8F0F7"
    }
  },
  "space": [4, 8, 12, 16, 24, 32, 48],
  "radius": {
    "sm": 4,
    "md": 8,
    "lg": 12
  },
  "type": {
    "h1": { "size": 36, "weight": 700, "lineHeight": 1.2 },
    "h2": { "size": 28, "weight": 600, "lineHeight": 1.3 },
    "h3": { "size": 22, "weight": 600, "lineHeight": 1.35 },
    "h4": { "size": 18, "weight": 500, "lineHeight": 1.4 },
    "body": { "size": 16, "weight": 400, "lineHeight": 1.5 },
    "small": { "size": 14, "weight": 400, "lineHeight": 1.5 },
    "label": { "size": 13, "weight": 500, "lineHeight": 1.4, "case": "uppercase", "letterSpacing": "0.05em" }
  },
  "shadow": {
    "sm": "0 1px 2px rgba(0,0,0,0.06)",
    "md": "0 4px 8px rgba(0,0,0,0.08)",
    "lg": "0 8px 24px rgba(0,0,0,0.12)"
  },
  "layout": {
    "maxWidth": 1280,
    "sidebarWidth": 240,
    "gutter": 24
  }
}
```

### Typography

- Font stack: Inter (primary), system sans-serif fallback
- Heading scale: H1 36px / H2 28px / H3 22px / H4 18px
- Body: 16px, line height 1.5
- Labels: 13px, uppercase, 0.05em letter-spacing, `text.muted` color
- Line length target: 60-75 characters in content areas
- Sentence case for headings, labels, and buttons. No title case overload.

**Current state vs. target:**
| Element | Current | Target |
|---|---|---|
| H2 (page title) | 20px / 600 weight | 28px / 600 weight |
| H3 (section header) | 14px / 500 weight | 22px / 600 weight |
| Nav links | 14px / no padding | 14px / 12px vertical padding, 44px min touch target |
| Stat card numbers | Mixed sizes | 36px / 700 weight for primary metrics |

### Color Mapping for Status

| Status | Color Role | Badge Style | Icon |
|---|---|---|---|
| Received | `info` | Blue bg, blue text | Inbox |
| Clarification needed | `warning` | Amber bg, amber text | MessageCircle |
| Assigned | `info` | Blue bg, blue text | UserCheck |
| Searching | `info` | Blue bg, blue text | Search |
| In review | `warning` | Amber bg, amber text | Eye |
| Ready for release | `success` | Green bg, green text | CheckCircle |
| Drafted | `info` | Blue bg, blue text | FileText |
| Approved | `success` | Green bg, green text | ShieldCheck |
| Fulfilled | `success` | Green bg, green text | Send |
| Closed | `neutral` | Gray bg, gray text | Archive |

Every badge includes an icon — never color-only. Accessible for colorblind users.

### Component Library

Use **shadcn/ui** (already specified in CLAUDE.md). Map design tokens into shadcn's CSS variable system:

```css
/* globals.css — token mapping */
:root {
  --primary: 207 62% 32%;          /* #1F5A84 */
  --primary-foreground: 0 0% 100%;
  --muted: 207 12% 40%;            /* #5B6975 */
  --muted-foreground: 207 12% 40%;
  --background: 0 0% 100%;
  --card: 207 33% 97%;             /* #F6F9FB */
  --border: 207 20% 82%;           /* #C8D3DC */
  --destructive: 0 50% 36%;        /* #8B2E2E */
  --ring: 207 62% 32%;
  --radius: 0.5rem;
}
```

### Button Variants (3 only)

| Variant | Use | Style |
|---|---|---|
| **Primary** | Main page action (New Request, Submit for Review) | Filled `brand.primary`, white text |
| **Secondary** | Supporting actions (Search & Attach, Export) | Outlined `brand.primary` border, transparent bg |
| **Ghost** | Tertiary actions (Sign out, Cancel, Back) | Text-only, hover bg `surface.subtle` |

### Card Component

- Background: `surface.default` (white) or `surface.subtle` (#F6F9FB)
- Border: 1px `surface.border`
- Border radius: `radius.md` (8px)
- Padding: 24px
- Shadow: `shadow.sm` on hover only
- Stat cards: label in `text.muted` at `label` size, value at `h1` size

---

## 7. Page Designs

### 7.1 Layout Shell

```
┌──────────────────────────────────────────────────────────────┐
│  ┌──────┐                                        User ▾  │
│  │ Logo │  CivicRecords AI            [notifications] [?] │
│  └──────┘                                                  │
├────────────┬─────────────────────────────────────────────────┤
│            │                                                 │
│  Search    │  Page Title                                     │
│  ─────     │  ─────────                                      │
│  Requests  │                                                 │
│  Exemptions│  [ Page content ]                               │
│  ─────     │                                                 │
│  Sources   │                                                 │
│  Ingestion │                                                 │
│  ─────     │                                                 │
│  Dashboard │                                                 │
│  Users     │                                                 │
│  Settings  │                                                 │
│            │                                                 │
├────────────┴─────────────────────────────────────────────────┤
│  CivicRecords AI v1.0 · Apache 2.0 · [Help] [Audit Log]     │
└──────────────────────────────────────────────────────────────┘
```

- **Sidebar** (240px): grouped navigation with section dividers. Workflow pages (Search, Requests, Exemptions) above admin pages (Sources, Ingestion, Dashboard, Users, Settings).
- **Header** (56px): logo/wordmark left, notification bell + help icon + user dropdown right.
- **Content area**: max-width 1280px, 24px gutter, scrollable.
- **Footer**: version, license, quick links.

### 7.2 Dashboard [REDESIGN]

**Current problems (from design critique):**
- H3 section headers same size as body text
- Stat card numbers all have equal visual weight
- No operational metrics (SLA, response time, workload)
- Empty lower half of page

**Redesigned content:**

```
Row 1: Priority stat cards (4)
  [Open Requests: 12] [Overdue: 2 🔴] [Avg Response: 4.2 days] [Deadline Compliance: 94%]

Row 2: Service health (compact inline, not full cards)
  ● Database  ● LLM Engine  ● Task Queue    All systems operational

Row 3: Two-column
  Left: Recent activity timeline (last 10 events across all requests)
  Right: Requests by status (mini bar chart or stacked badges)

Row 4: Two-column
  Left: Approaching deadlines (next 5, with days remaining)
  Right: Quick actions: [New Request] [Search Records] [Export Audit Log]
```

### 7.3 Search [REDESIGN]

**Current problems:**
- No guidance in empty state
- Search scores show raw RRF values (1.1-1.6%)
- No saved searches or export

**Redesigned content:**

```
Empty state:
  "Search across all ingested documents"
  [Search bar — large, prominent]
  [File type filter]  [Date range]  [Department]
  Example searches: "water quality 2025" · "police incident January" · "council budget"

Results state:
  [N results found · sorted by relevance · Export ▾]
  Result card:
    Document title (original filename, not UUID)
    Relevance: ████████░░ 82%     (normalized 0-100)
    Source: Water Department · Ingested 3 days ago
    "...matching excerpt with **highlighted** terms..."
    [Attach to Request ▾]  [View Full Document]

  AI Summary panel (if "Generate AI summary" checked):
    Bordered card with "AI-generated draft" label
    Summary text with cited sources [1] [2] [3]
```

### 7.4 Requests [REDESIGN]

**Current problems:**
- All stat cards have equal visual weight
- "None" for empty deadlines (should say "No deadline set")
- No priority indicators
- No filtering or sorting

**Redesigned content:**

```
Header row:
  [Records Requests]                        [+ New Request]

Priority stat cards:
  [Overdue: 2 🔴] [Due This Week: 5 🟡] [In Review: 3] [Total Open: 14]

Filter bar:
  [Status ▾] [Assigned To ▾] [Department ▾] [Priority ▾] [Date Range]

Table:
  | Priority | Requester | Description | Status | Deadline | Assigned | Actions |
  | 🔴 Urgent | Jane Smith | Water quality... | In Review | 2 days left | M. Johnson | View |
  | — Normal | Bob Reporter | Police records... | Received | Apr 24 | Unassigned | View · Assign |

  Pagination: [< Previous] Page 1 of 3 [Next >]
```

### 7.5 Request Detail [REDESIGN]

**Current problems:**
- Document IDs shown as truncated UUIDs instead of filenames
- No timeline/event history
- No messaging
- No fee tracking
- No response letter generation

**Redesigned content:**

```
Header:
  [← Back to Requests]
  Request from Jane Smith                [searching] badge
  Received: April 12, 2026 · Deadline: April 19, 2026 (7 days)

Two-column layout:

Left column (65%):
  ┌─ Request Details ─────────────────────────────────┐
  │ Requester: Jane Smith · jane@example.com          │
  │ Type: Resident · Priority: Normal                 │
  │ Description: Water quality test results 2025      │
  │ Scope: Narrow (estimated)                         │
  │ Fee estimate: $0.00 (under threshold)             │
  └───────────────────────────────────────────────────┘

  ┌─ Timeline ────────────────────────────────────────┐
  │ Apr 12, 2:43 PM · Request received                │
  │   Logged by System Administrator                  │
  │ Apr 12, 2:45 PM · Documents attached (3)          │
  │   water-quality-report-2025.txt + 2 others        │
  │ Apr 12, 3:01 PM · Status changed to "Searching"   │
  │   By System Administrator                         │
  └───────────────────────────────────────────────────┘

  ┌─ Attached Documents (3) ──────────────────────────┐
  │ | Document | Type | Exemptions | Status | Action | │
  │ | water-quality-report-2025.txt | txt | 2 flags | pending | Review |
  │ | police-incident-jan2025.txt | txt | 4 flags | pending | Review |
  │ | council-minutes-feb2025.txt | txt | 3 flags | pending | Review |
  └───────────────────────────────────────────────────┘

  ┌─ Messages ────────────────────────────────────────┐
  │ [Internal note / Requester message toggle]        │
  │ [Message input]                    [Send]         │
  └───────────────────────────────────────────────────┘

Right column (35%):
  ┌─ Workflow ────────────────────────────────────────┐
  │ Current: Searching                                │
  │ [Submit for Review]  (primary button)             │
  │ [Request Clarification] (secondary)               │
  │ [Generate Response Letter] (secondary)            │
  └───────────────────────────────────────────────────┘

  ┌─ Fees ────────────────────────────────────────────┐
  │ Estimated: $0.00                                  │
  │ Status: Under threshold (no fee required)         │
  │ [Update Fee Estimate]                             │
  └───────────────────────────────────────────────────┘

  ┌─ Search & Attach ─────────────────────────────────┐
  │ [Search for documents to attach]                  │
  │ Quick search within this request context          │
  └───────────────────────────────────────────────────┘
```

### 7.6 Exemptions [REDESIGN]

**Current problems:**
- "Acceptance Rate: 0.0%" misleading when no flags reviewed
- Rule table shows raw definition strings
- No flag review workflow on this page

**Redesigned content:**

```
Header:
  [Exemption Detection]                    [+ Add Rule]

Stat cards:
  [Pending Review: 18 🟡] [Accepted: 0] [Rejected: 0] [Active Rules: 1]
  (When no flags reviewed: show "No flags reviewed yet" instead of 0.0%)

Tab bar:
  [Flags for Review] [Rules] [Audit History]

Flags tab (default):
  Table of unreviewed flags with:
  | Document | Category | Confidence | Matched Text | Rule | Actions |
  | water-quality-report.txt | SSN | 95% | "***-**-1234" | PII Regex | [Accept] [Reject] [View Context] |

Rules tab:
  | State | Category | Type | Pattern | Status | Actions |
  | CO | CORA - Trade Secrets | keyword | trade secret, proprietary... | Active | [Edit] [Disable] |
  [+ Add Rule] button opens modal with: state, category, type (regex/keyword/llm_prompt), definition, test input
```

### 7.7 Sources [REDESIGN]

**Current problems (includes known bugs #1 and #2):**
- Directory path is a raw text input (clerks don't know filesystem paths)
- No integration options beyond directory and upload
- No connection testing

**Redesigned content:**

```
Header:
  [Data Sources]                           [+ Add Source]

Upload section:
  ┌─ Upload Documents ────────────────────────────────┐
  │  [Drag & drop zone — preserved from current]      │
  │  PDF, DOCX, XLSX, CSV, TXT, HTML, EML             │
  │  Max 50MB per file                                 │
  └───────────────────────────────────────────────────┘

Connected sources:
  Card grid (not table):
  ┌─ File Uploads ─────┐  ┌─ Shared Drive ─────────┐  ┌─ SharePoint ──────────┐
  │ 📁 _uploads        │  │ 📂 \\server\records    │  │ 🔗 Coming in v1.1    │
  │ Active · 3 docs    │  │ [Configure Path]       │  │                       │
  │ [Ingest Now]       │  │ [Test Connection]      │  │ Integration planned   │
  └────────────────────┘  └────────────────────────┘  └───────────────────────┘

  ┌─ Email Archive ─────┐  ┌─ Database ─────────────┐  ┌─ API Endpoint ────────┐
  │ 📧 Microsoft 365    │  │ 🗄️ Coming in v1.1     │  │ 🌐 Coming in v2.0    │
  │ [Configure Email]   │  │                        │  │                       │
  │ [Test Connection]   │  │ Integration planned    │  │ Integration planned   │
  └─────────────────────┘  └────────────────────────┘  └───────────────────────┘

Add Source modal (for "Shared Drive"):
  Step 1: "Where are your records stored?"
          [Browse / paste path: _______________]
          [Test Connection]
          Example: C:\Records\Public or /mnt/records
  Step 2: "How often should we check for new files?"
          [Manual only / Daily / Weekly]
  Step 3: "Which department owns these records?"
          [Department dropdown]
```

### 7.8 Ingestion [REDESIGN]

**Current problems:**
- Filenames show UUID prefixes
- No progress indicators for active ingestion
- No retry for failed documents

**Redesigned content:**

```
Stat cards:
  [Sources: 1/1] [Documents: 3] [Chunks: 4] [Processing: 0] [Failed: 0]

Active processing (if any):
  Progress bar with filename and step indicator
  "Processing council-minutes-feb2025.txt — Chunking (step 2/4)"

Recent documents table:
  | Document | Type | Size | Status | Chunks | Ingested | Actions |
  | city-council-minutes-feb2025.txt | txt | 3.5 KB | ✅ Completed | 2 | 3 hours ago | [Re-ingest] |
  (Original filenames, not UUIDs. Relative timestamps alongside absolute.)
```

### 7.9 Users [REDESIGN]

**Current problems:**
- No department assignment
- No user detail/edit view
- "Never" for last login is unhelpful

**Redesigned content:**

```
  | Name | Email | Role | Department | Status | Last Active | Actions |
  | System Administrator | admin@example.gov | admin | — | Active | Today | [Edit] |
  | Test Clerk | testclerk@example.gov | staff | Records | Active | Never logged in | [Edit] [Deactivate] |
```

### 7.10 Onboarding Interview [MVP-NOW]

New page — not a redesign. LLM-guided adaptive interview for first-time city deployment (Section 12.2).

```
Three-phase wizard:
  Phase 1: City Profile — state, population, email platform, IT staffing, request volume
  Phase 2: System Identification — walk through functional domains, targeted questions
  Phase 3: Gap Map — show domains with no identified source, prompt for resolution

UI pattern: conversational chat-style interface with structured input fields
  (dropdowns for known options, free text for details, skip buttons for unknowns)
Progress indicator showing current phase and completion percentage
Save-and-resume capability (onboarding_status tracks progress)
```

### 7.11 City Profile & Settings [MVP-NOW]

New page — not a redesign. Persistent view of the City Profile produced by onboarding (Section 12.2.2).

```
Header:
  [City Profile]                              [Re-run Onboarding Interview]

City details card:
  City: [name] · State: [state] · Population: [band] · Email: [platform]
  IT staffing: [dedicated/shared] · Monthly requests: [volume]

Connected Systems table:
  | Domain | System | Vendor | Protocol | Status | Last Sync | Actions |
  | Finance | Caselle | Caselle Inc | ODBC | ● Healthy | 2 hours ago | [Configure] [Test] |
  | Email | Microsoft 365 | Microsoft | Graph API | ● Healthy | 15 min ago | [Configure] [Test] |

Gap Map:
  ⚠ Permitting — no source identified. [Connect a source]
  ⚠ Public Safety — no source identified. [Connect a source] (CJIS compliance required)
  ✓ Finance — connected (Caselle)
  ✓ Email — connected (Microsoft 365)
```

### 7.12 Discovery Dashboard [v1.1]

New page — network scan results and source confirmation (Section 12.3.3).

```
Header:
  [Discovery Dashboard]                       [Run Discovery Scan]

Last scan: April 10, 2026 · 14 sources found

Stat cards:
  [High Confidence: 8] [Needs Review: 4] [Unknown: 2] [New Since Last Scan: 3]

Results table:
  | Service | Confidence | Identified As | Domain | Actions |
  | SQL Server @ 10.0.1.50 | 94% | Tyler Munis | Finance | [Confirm & Connect] |
  | PostgreSQL @ 10.0.3.22 | 42% | Unknown | — | [Investigate] [Classify] [Ignore] |

Coverage gap alerts:
  ⚠ 32% of requests reference "police" but no Public Safety source connected
```

---

## 8. Workflow Patterns

### 8.1 Request Lifecycle

```
[Received]
    │
    ├── Needs more info? ──→ [Clarification Needed] ──→ Response received ──→ [Received]
    │
    ▼
[Assigned] (routed to department liaison or staff member)
    │
    ▼
[Searching] (staff searching for responsive documents)
    │
    ▼
[In Review] (documents collected, exemption/legal review)
    │
    ├── Exemptions found? ──→ Flag review workflow
    │
    ▼
[Ready for Release] (review complete)
    │
    ▼
[Drafted] (response letter generated)
    │
    ▼
[Approved] (supervisor signs off)
    │
    ▼
[Fulfilled] (records delivered to requester)
    │
    ▼
[Closed] (archived with full audit trail)
```

Every status transition:
- Writes to `request_timeline`
- Writes to `audit_log`
- Triggers notification (if template exists for that transition)
- Updates `records_requests.status`

### 8.2 Exemption Review Workflow

```
Document ingested
    │
    ▼
Exemption engine scans chunks (regex + keyword + LLM)
    │
    ▼
Flags created (status: flagged)
    │
    ▼
Staff reviews flag:
    ├── [Accept] → flag confirmed, document marked for redaction
    ├── [Reject] → false positive, flag dismissed
    └── [Escalate] → routed to legal/reviewer role
    │
    ▼
All flags resolved → document ready for inclusion/exclusion decision
```

### 8.3 Response Letter Generation [MVP-NOW]

```
Clerk clicks [Generate Response Letter] on Request Detail
    │
    ▼
System assembles context (within token budget):
  - Request description and requester info
  - List of responsive documents (included/excluded)
  - Exemption flags and their dispositions
  - Applicable disclosure template for jurisdiction
  - Fee summary
    │
    ▼
LLM generates draft letter (labeled "AI-generated draft")
    │
    ▼
Clerk edits in rich text editor
    │
    ▼
[Submit for Approval] → Supervisor reviews
    │
    ▼
[Approve] → Letter finalized, status → approved
    │
    ▼
[Send] → Letter delivered (email or download), status → fulfilled
```

### 8.4 Notification Templates [MVP-NOW]

| Event | Recipient | Channel | Subject Pattern |
|---|---|---|---|
| Request received | Requester | Email | "Your records request has been received (#{id})" |
| Clarification needed | Requester | Email | "We need more information about your request (#{id})" |
| Request assigned | Liaison | In-app | "New records request assigned to your department" |
| Deadline approaching (3 days) | Assigned staff | In-app + Email | "Records request #{id} due in 3 days" |
| Deadline overdue | Assigned staff + Admin | In-app + Email | "OVERDUE: Records request #{id} past deadline" |
| Records ready | Requester | Email | "Your requested records are ready (#{id})" |
| Request closed | Requester | Email | "Your records request has been closed (#{id})" |

Tone: reassuring, plain language, explain process. Never defensive or legalistic.

---

## 9. Accessibility Standards

Target: **WCAG 2.2 AA** from day one.

| Requirement | Current State | Target |
|---|---|---|
| Color contrast | Passes (text ~15:1, muted ~5.7:1) | Maintain |
| Touch targets | FAIL (nav links 20px, no padding) | 44x44px minimum on all interactive elements |
| Focus visibility | No visible focus styles | `focus:ring-2 focus:ring-primary` on all focusables |
| Skip navigation | Missing | Add skip-to-content link |
| ARIA landmarks | Good (nav role, table aria-labels) | Maintain + add to new components |
| Color-only indicators | Status badges use color only | Add icons to every badge |
| Keyboard navigation | Untested | Full keyboard completion for all workflows |
| Form error handling | Not tested | Preserve data on validation error, focus first error |
| Screen reader | Untested | Test with NVDA/VoiceOver before v1.0 |

### Content Design Rules

- Lead with action: "Tell us what records you need" not "Records Request Submission Form"
- Explain why data is requested when the reason is not obvious
- Never hide important policy terms only in tooltips
- Every closed/denied request shows reason in human language plus formal basis
- Replace internal jargon: "responsive documents" becomes "records found for release"
- Every error state explains: what happened, how to fix it, how to get help

---

## 10. Compliance Architecture [BUILT]

Based on the 50-state regulatory analysis. These are hard requirements enforced at the API layer.

### 10.1 Human-in-the-Loop [BUILT]

- No auto-redaction. Every exemption flag requires affirmative human action.
- No auto-denial. No denial or partial-denial response generated without human decision.
- No auto-release. No document transmitted to requester without explicit human authorization.
- All AI content labeled as "AI-generated draft requiring human review" at the API layer.

### 10.2 Audit Logging [BUILT]

- Hash-chained, append-only audit log.
- Every API call logged with user, action, resource, timestamp, IP.
- Exportable as CSV/JSON for compliance audits.
- Retention policy configurable (cleanup job [MVP-NOW]).

### 10.3 Data Sovereignty [BUILT]

- No outbound network connections (verification scripts provided).
- No telemetry, analytics beacons, or external API calls.
- All processing local. LLM runs on-premises via Ollama.
- All dependencies permissive or weak-copyleft (MIT, Apache 2.0, BSD, LGPL, MPL).
- Redis pinned to <8.0.0 (BSD licensed).

### 10.4 AI Governance [BUILT]

- Model registry tracks all LLM models in use.
- CAIA impact assessment template provided.
- AI governance policy template provided.
- Colorado CAIA is the strictest standard designed for.

---

## 11. Technical Implementation Plan

### Build Order

```
Phase 0: Design Foundation                    [MVP-NOW — do first] ✅ COMPLETE
  ├── Install shadcn/ui
  ├── Map design tokens to CSS variables
  ├── Build sidebar layout shell
  ├── Create component variants (buttons, badges, cards, tables)
  └── Typography scale implementation

Phase 1: Staff Workbench Redesign             [MVP-NOW — 11 pages]
  ├── Dashboard with operational metrics and coverage gap indicators
  ├── Search with normalized scores and empty states
  ├── Requests with filtering, priority, SLA indicators
  ├── Request Detail with timeline, messages, fees
  ├── Exemptions with flag review workflow
  ├── Sources with guided setup, integration cards, and connector management
  ├── Ingestion with clean filenames and progress
  ├── Users with department assignment
  ├── Onboarding Interview wizard (Section 12.2)
  ├── City Profile & Settings page (Section 12.2.2)
  └── Discovery Dashboard placeholder (v1.1 — UI shell only)

Phase 2: New Backend Features                 [MVP-NOW]
  ├── Database migrations (departments, fees, timeline, messages, notifications, prompts,
  │   city_profile, system_catalog, connector_templates)
  ├── Notification service (Celery + SMTP)
  ├── Response letter generation (LLM + templates)
  ├── Context manager (token budgeting for Ollama)
  ├── Connector framework — authenticate/discover/fetch/health_check (Section 12.4)
  ├── Onboarding service — LLM-guided interview with catalog lookup (Section 12.2)
  ├── Municipal Systems Catalog — versioned JSON, loaded into DB (Section 12.1)
  ├── File system / SMB connector (Section 12.4.2)
  ├── Email connector — SMTP/IMAP/O365 Graph API (Section 12.4.2)
  ├── Tier 1 regex expansion — credit cards, bank accounts, driver's licenses (Section 12.7.1)
  ├── Fee tracking API
  ├── Request scope assessment API
  ├── Operational analytics API
  ├── Liaison role + department scoping
  └── Audit retention cleanup task

Phase 3: Public Portal + Discovery            [v1.1]
  ├── Public API with rate limiting
  ├── Public homepage and search
  ├── Guided request wizard
  ├── Public request tracker
  ├── Help and policy pages
  ├── Published records index and saved searches
  ├── Redaction ledger with originals vs. derivatives
  ├── Network discovery engine with IT opt-in (Section 12.3)
  ├── Confidence scoring and auto-identification (Section 12.3.2)
  ├── Connection health monitoring and self-healing (Section 12.5)
  ├── REST API connectors — Tyler, Accela (Section 12.4.2)
  ├── ODBC/JDBC bridge connector (Section 12.4.2)
  ├── Coverage gap analysis (Section 12.5.3)
  ├── Discovery Dashboard — full implementation (Section 12.3.3)
  └── Tier 2 NER redaction — names, medical, juvenile, privilege (Section 12.7.2)

Phase 4: Transparency + Advanced Discovery    [v2.0]
  ├── Open records library with curated collections
  ├── Reporting dashboards and trend analytics
  ├── Public request archive (closed requests, opt-in)
  ├── Federation between CivicRecords AI instances
  ├── API endpoint probing for vendor auto-detection (Section 12.3.1)
  ├── Schema drift detection and alerting (Section 12.5.2)
  ├── LLM-assisted unknown database characterization (Section 12.6.1)
  ├── RPA bridge for legacy systems — last resort (Section 12.6.3)
  ├── Community catalog contributions (Section 12.1)
  ├── GIS connector, vendor SDK connectors (Section 12.4.2)
  ├── Tier 3 visual AI — face/plate blurring, OCR, speech-to-text (Section 12.7.3)
  └── Webhook/event stream connectors (Section 12.4.2)
```

### Engineering Acceptance Criteria

- Every component must support loading, empty, error, and disabled states.
- Every workflow must support keyboard-only completion.
- Role-based permissions change available actions, not layout or naming.
- All status transitions write to audit log automatically.
- Public status pages understandable without staff login.
- No `any` types in TypeScript (except catch blocks).
- Python: async/await consistently, type hints on all public functions.
- Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`).

---

## 12. Universal Discovery & Connection Architecture

### 12.0 Why This Section Matters

Open records requests can touch any system a city operates — email, financial records, police body camera footage, building permits, personnel files, utility billing. Today, clerks often spend more time finding records than reviewing them. This section defines how CivicRecords AI finds, connects to, and monitors a city's data sources automatically — so the clerk's job becomes reviewing and releasing records, not hunting for them.

> **In plain language:** Instead of you tracking down every system that might have responsive records, CivicRecords AI learns what systems your city uses and goes looking for you. You still decide what gets released — the system just makes sure nothing gets overlooked.

### 12.1 Municipal Knowledge Graph

Municipal IT environments are not random. A city of 30,000 in Colorado has a predictable set of software systems. The specific vendor names change, but the functional categories are nearly universal. CivicRecords AI uses this predictability as its starting point.

#### 12.1.1 The Systems Catalog

The system ships with a curated **Municipal Systems Catalog** — a structured graph mapping functional domains to the systems that typically serve them, the data they contain, how they are accessed, and what kinds of open records requests they are relevant to.

Each domain entry contains:
- Domain name and description
- Typical systems and vendors
- Data shape (structured records, documents, media, spatial data)
- Access protocols (REST API, ODBC/JDBC, SMTP journal, file share, vendor SDK, manual export)
- Common record types frequently subject to open records requests
- Redaction sensitivity (PII, HIPAA, CJIS, juvenile records)
- Discovery hints (technical fingerprints for automatic identification)

**Functional Domains:**

| Domain | Typical Systems | Common Record Requests | Sensitivity |
|---|---|---|---|
| Finance & Budgeting | Tyler Munis, Caselle, OpenGov, SAP | Purchase orders, vendor payments, budget reports, payroll | Tax IDs, bank accounts, SSNs |
| Public Safety | Mark43, Spillman, Axon, Genetec, Tyler New World | Incident reports, arrest records, body cam footage, 911 calls | CJIS-protected, juvenile records, victim identity |
| Land Use & Permitting | Accela, CityWorks, EnerGov | Building permits, inspections, code violations, site plans | Homeowner PII, contractor license data |
| Geographic Information | Esri ArcGIS, QGIS, MapGeo | Property boundaries, zoning maps, infrastructure layers | Property owner names/addresses |
| Human Resources | NEOGOV, Workday, ADP, Paylocity | Job postings, hiring records, salary data, complaints | HIPAA, background checks, SSNs |
| Document Management | Laserfiche, OnBase, SharePoint, network file shares | Meeting minutes, ordinances, contracts, correspondence | Varies |
| Email & Communication | Microsoft 365, Google Workspace, on-prem Exchange | Staff email, calendar entries, Teams/Slack messages | Personal emails, sensitive deliberations |
| Utilities & Public Works | CIS Infinity, Tyler iasWorld, Cartegraph, Lucity | Utility billing, work orders, maintenance logs, meter data | Account numbers, addresses, payment info |
| Courts & Legal | Tyler Odyssey, Journal Technologies, custom systems | Court dockets, case filings, ordinance violations | Sealed records, juvenile cases |
| Parks & Recreation | RecTrac, CivicRec, ActiveNet, custom databases | Facility reservations, program registrations, rental agreements | Minor personal info, payment data |
| Asset & Fleet Management | Samsara, Asset Panda, FleetWave, Cartegraph | Vehicle GPS logs, maintenance records, fuel purchases | Driver IDs, GPS patrol patterns |
| Legacy & Custom Systems | AS/400, custom Access databases, FoxPro, flat files | Historical records predating modern systems | Often unknown — requires manual review |

**Community-Maintained Catalog:** The catalog ships as a versioned JSON file. Open-source cities can contribute updates. Catalog updates never overwrite a city's local configuration.

### 12.2 Guided Onboarding Interview

When a city first deploys CivicRecords AI, the system runs an LLM-guided onboarding conversation. Not a static form with 200 fields — an adaptive interview that starts broad and gets specific based on answers.

> **In plain language:** Think of it like a new employee's first day: they ask about your office, your tools, and your workflow, and they already know enough about city government to ask smart follow-up questions.

#### 12.2.1 Interview Flow

**Phase 1: City Profile (5-10 minutes)**
- What state are you in? (determines applicable open records law and deadlines)
- Approximate population? (narrows likely systems)
- Email platform? (Microsoft 365, Google Workspace, on-prem Exchange)
- Dedicated IT department or shared role?
- Monthly open records request volume?

**Phase 2: System Identification (10-20 minutes)**
Walks through each functional domain, asking targeted questions based on city profile. Small towns skip enterprise ERP questions.

**Phase 3: Gap Map (5 minutes)**
Produces a list of functional domains where the city should have data but hasn't identified a source. Example: "You haven't identified a permitting system, but your city issues building permits. Where do those records live?"

#### 12.2.2 Onboarding Output

The interview produces a **City Profile** containing:
- Confirmed systems with vendor names, versions, and access details
- Gap map entries for domains without an identified system
- IT environment notes (network topology, Active Directory, cloud vs. on-premise)
- Priority ranking based on request volume

The City Profile can be revisited and updated at any time from the Sources page.

### 12.3 Active Discovery Engine [v1.1]

The onboarding interview captures what staff already know. The Active Discovery Engine finds what they missed, forgot, or didn't know about. With explicit permission from city IT, it scans the local network and cross-references findings against the Municipal Systems Catalog.

> **In plain language:** After setup, the system looks around your city's network (with IT's permission) and says: "I found a database that looks like it might be your parks reservation system. Want me to connect to it?" It never connects to anything without your approval.

#### 12.3.1 Discovery Methods

**Method 1: Network Service Scanning** — Scans for common service fingerprints (SQL Server 1433, PostgreSQL 5432, SMB/CIFS, HTTP/HTTPS). Cross-references against knowledge graph. Requires explicit IT authorization logged in audit trail.

**Method 2: Directory Enumeration** — Enumerates Active Directory service accounts, shared mailboxes, and security group names. A service account named "svc_laserfiche" reveals a Laserfiche installation.

**Method 3: API Endpoint Probing** [v2.0] — Tries standard API endpoints for known vendors at discovered addresses. Probes only — does not authenticate or pull data.

#### 12.3.2 Confidence Scoring

| Score | Meaning | Admin Action |
|---|---|---|
| 90-100% | High confidence — vendor API confirmed | One-click confirm and connect |
| 60-89% | Probable match — database name/service account pattern | Review details, confirm vendor, authorize |
| 30-59% | Possible match — service found but type unclear | Investigate with IT, classify manually |
| Below 30% | Unknown — service exists but unidentifiable | Flag for IT review or ignore |

#### 12.3.3 The Discovery Dashboard

After a discovery run, the admin sees:
- Total sources found, broken down by confidence level
- Sources matching known municipal systems (one-click confirm)
- Sources needing human identification
- Unknown services flagged for IT review
- Gap map updates

### 12.4 Universal Connector Protocol

Every connector — whether it talks to a modern cloud API or a legacy database — implements the same interface and feeds records into the same ingestion pipeline.

#### 12.4.1 Connector Interface Contract

Four standard operations:
- **authenticate()** — Establish secure connection (OAuth2, database credentials, API key, service account). Handles credential refresh automatically.
- **discover()** — Enumerate available records (tables/rows for databases, mailboxes/dates for email, directories/files for file shares).
- **fetch()** — Pull specific records and convert to CivicRecords AI standard document format.
- **health_check()** — Verify connection alive, credentials valid, schema unchanged. Returns health status with diagnostics.

#### 12.4.2 Connector Types by Access Protocol

| Protocol | Authentication | Best For | Phase |
|---|---|---|---|
| File System / SMB | Service account or mount | Shared drives, document repos, scanned archives | [MVP-NOW] |
| SMTP / IMAP Journal | Service account (O365 Graph / IMAP) | Email archives (#1 source for records requests) | [MVP-NOW] |
| REST API (Modern SaaS) | OAuth2 | Tyler, Accela, NEOGOV, cloud platforms | [v1.1] |
| ODBC / JDBC Bridge | Database credentials (encrypted) | On-prem databases, legacy SQL, AS/400 via ODBC | [v1.1] |
| GIS REST API | API key or service token | Esri ArcGIS, spatial data, property records | [v2.0] |
| Vendor SDK | Vendor-specific | Evidence management (Axon), CAD systems | [v2.0] |
| Webhook / Event Stream | Shared secret or mTLS | Real-time IoT, fleet telematics, sensors | [v2.0] |
| Manual / Export Drop | None (file upload) | Systems with no API — clerk exports and uploads | [MVP-NOW] |

### 12.5 Continuous Discovery & Self-Healing

> **In plain language:** Once set up, the system keeps watching. If a connection breaks, it tries to fix it automatically. If a new system appears on the network, it lets you know. If people keep requesting records from a source you haven't connected yet, it tells you that too.

#### 12.5.1 Scheduled Discovery Runs

Weekly by default (configurable). Each run reports:
- **New sources** — services not in the previous scan
- **Changed sources** — known sources with changed fingerprints
- **Lost sources** — previously-detected services no longer responding

#### 12.5.2 Connection Health Monitoring

Heartbeat every 15 minutes (critical sources) or hourly (lower-priority). Automatic handling:
- **Expired OAuth2 tokens:** Auto-refreshed. Alerts admin only if refresh token also expired.
- **Temporary outages:** Exponential backoff (1m → 5m → 15m → 60m). Alerts only if persistent.
- **Password rotation:** Detects auth failures, prompts admin with clear explanation.
- **Schema drift:** Detects mismatch, pauses ingestion, alerts admin with description of changes.
- **API rate limiting:** Auto-throttles, adjusts sync to off-peak hours.

#### 12.5.3 Coverage Gap Analysis

Cross-references connected sources against request patterns. Example:

> "32% of your records requests in the past 90 days reference 'police' or 'incident report,' but you don't have a public safety data source connected. Would you like help setting that up?"

Runs monthly, surfaces on Dashboard as a coverage health indicator.

### 12.6 Handling Unknown and Legacy Systems

> **In plain language:** Not everything runs on well-known software. Some departments have homegrown tools, ancient systems, or tiny niche vendors. The system handles those too.

#### 12.6.1 Automated Characterization

For unknown database services, the system can (with authorization) enumerate table and column names without reading data. Metadata is fed to the local LLM for analysis.

**Schema Metadata Sensitivity:** Schema metadata itself can be sensitive (table names like "internal_affairs_complaints" reveal what a city tracks). The system:
- **Encrypted storage:** Schema enumeration results stored encrypted at rest, never in plaintext.
- **Context manager integration:** Schema metadata processed by LLM subject to same token budget and context management rules as document content (Section 4).
- **Audit log redaction:** Audit trail records that enumeration occurred but does not log individual table/column names in plaintext.
- **LLM prompt discipline:** Characterization prompt describes system function in general terms without echoing sensitive table names into UI or logs.

#### 12.6.2 Manual Fallback Paths (priority order)

1. **Watched folder:** Department exports data to a designated folder. System monitors and ingests automatically.
2. **Scheduled export:** IT sets up a cron job dumping data to a drop location.
3. **Manual upload:** Staff upload files through Sources page. Universal fallback.
4. **RPA bridge** [v2.0] — last resort. See suitability criteria below.

#### 12.6.3 RPA Suitability Criteria [v2.0]

RPA (automated screen-scraping) is powerful but inherently fragile. Deploy only when ALL four conditions are met:
1. **No API:** No REST, SOAP, or other programmatic interface.
2. **No export function:** No built-in report export, CSV dump, or print-to-file.
3. **No database access:** ODBC/JDBC unavailable or prohibited by vendor license.
4. **High request frequency:** Data requested monthly or more (for rare requests, manual upload is more practical).

> **In plain language:** RPA is like hiring a robot to click buttons in an old application. It works, but every time that old application changes its screens, the robot gets confused. For most legacy systems, a simpler approach (a nightly data export) is more reliable.

RPA connectors must include self-diagnostics (detect UI changes, auto-suspend, alert IT). Review quarterly for continued necessity.

### 12.7 Tiered Redaction Engine

Extends the existing Exemption Engine with automated detection organized into three tiers.

> **In plain language:** The system helps you find things that need to be blacked out before release — Social Security numbers, personal phone numbers, names of minors, faces in video. It flags what it finds, but you always make the final call.

**Critical design constraint:** Consistent with human-in-the-loop (Section 10), the redaction engine *proposes* redactions. Humans approve them. No redaction is applied automatically.

#### 12.7.1 Tier 1: Pattern Matching (RegEx) [MVP-NOW]

Deterministic, rule-based detection of structured PII:
- Social Security Numbers (XXX-XX-XXXX and variants)
- Credit card numbers (Luhn-validated, major card patterns)
- Phone numbers (US formats including area codes)
- Email addresses
- Bank account and routing numbers
- Driver's license numbers (state-specific patterns)

Runs at ingestion time. High confidence. Pre-flagged before a specific request is filed.

#### 12.7.2 Tier 2: AI Text Analysis (NLP/NER) [v1.1]

AI-powered detection using local Ollama LLM or dedicated NER models (spaCy):
- Person names in inappropriate disclosure contexts
- Medical information (HIPAA-relevant)
- Juvenile identifiers (names, school info, age in police reports)
- Attorney-client privileged content (contextual, not just keyword)

Medium-confidence flags with explanations: "This paragraph mentions a minor by name in a police report. Colorado law requires redaction of juvenile identity."

#### 12.7.3 Tier 3: Visual AI [v2.0]

Detection in images, video, and audio:
- **Video:** Face detection/blurring, license plate blurring, badge/ID detection (body camera, surveillance)
- **Images:** OCR to extract text from scanned documents, handwritten notes → Tier 1/2 processing
- **Audio:** Speech-to-text for 911 recordings/voicemails → NER → automated muting of PII segments

Requires GPU hardware. Architecture accommodates it; not required for initial deployment.

### 12.8 Security & Compliance for Discovery and Connection

Hard requirements beyond Section 10.

#### 12.8.1 Permission Model

- **Explicit opt-in for scanning:** Network discovery disabled by default. IT must explicitly enable and define scope. Authorization logged.
- **Admin approval for every connection:** Discovered sources are proposals. No data accessed until admin reviews, confirms, provides credentials, and authorizes.
- **Credential encryption:** AES-256 at rest. Never logged, never in exports, never displayed after initial entry.
- **Least-privilege access:** Read-only accounts. Read-only API scopes. System never writes to, modifies, or deletes data in source systems.

#### 12.8.2 Audit Trail

Every discovery and connection action logged to hash-chained audit log:
- Discovery scan initiated (who, what scope, when)
- Source discovered (what, confidence, hypothesis)
- Source confirmed or rejected
- Connection authorized, credentials stored
- Health check results (especially failures and schema drift)
- Redaction proposed, reviewed, approved, applied
- Credential rotation events

#### 12.8.3 Originals vs. Redacted Derivatives

Redaction produces a separate **Derivative** copy. Original preserved read-only. Derivative is the version transmitted to the requester. The `redaction_ledger` records every redaction applied, including legal basis and approving staff member. Non-destructive — if a decision is challenged, the original is available for re-review.

#### 12.8.4 CJIS Compliance for Public Safety Connectors

Connecting to police records systems (Mark43, Spillman, Axon, Tyler New World, Genetec, or any system containing Criminal Justice Information) triggers the FBI's CJIS Security Policy. This is a federal requirement.

> **In plain language:** If you connect CivicRecords AI to your police department's records system, federal rules (CJIS) apply. These rules require background checks for anyone who can access the data, encrypted connections, and detailed access logs. Our system already does most of this — but your city needs to formally verify compliance before turning on a police data connection. The system walks you through the checklist.

**Already satisfied by architecture:**
- Encryption in transit (TLS) and at rest (AES-256) — CJIS Policy 5.10.1
- Hash-chained audit logging — CJIS Policy 5.4
- Role-based access control with least-privilege — CJIS Policy 5.5
- No cloud egress, all data on-premises — CJIS Policy 5.10.3.2

**City must satisfy before activating public safety connector:**
- **Personnel security:** Fingerprint-based background checks for all individuals with CJI access — CJIS Policy 5.12
- **CJIS Security Addendum:** Signed with state's CJIS Systems Agency (CSA)
- **Security awareness training:** Within 6 months of access and biennially — CJIS Policy 5.2

**Enforcement:** When an admin attempts to connect a "Public Safety" source, the system presents a CJIS compliance checklist. Connection cannot activate until admin confirms each requirement. Confirmation recorded in audit log. Gate applies regardless of how the source was discovered.

### 12.9 Data Model Additions

#### 12.9.1 New Tables

```
city_profile [MVP-NOW]
  id, city_name, state, county, population_band,
  email_platform, has_dedicated_it, monthly_request_volume,
  onboarding_status (not_started/in_progress/complete),
  profile_data (JSON), gap_map (JSON),
  created_at, updated_at, updated_by

system_catalog [MVP-NOW] (shipped, read-only, versioned)
  id, domain, function, vendor_name,
  vendor_version, access_protocol, data_shape,
  common_record_types (JSON), redaction_tier,
  discovery_hints (JSON), connector_template_id,
  catalog_version, created_at

discovered_sources [v1.1]
  id, discovery_run_id, discovery_method,
  system_catalog_id (nullable FK), connection_uri,
  protocol, hostname, port, service_fingerprint,
  confidence_score (0-100), identification_hypothesis,
  status (pending/confirmed/rejected/connected),
  verified_by, verified_at,
  data_source_id (nullable FK to data_sources),
  last_seen, last_health_check, health_status,
  created_at

discovery_runs [v1.1]
  id, run_type (scheduled/manual/triggered),
  authorized_by, scan_scope (JSON),
  started_at, completed_at,
  sources_found, sources_new, sources_changed, sources_lost,
  run_log (JSON)

source_health_log [v1.1]
  id, discovered_source_id,
  check_type (heartbeat/full/schema_check),
  status (healthy/degraded/failed/unreachable),
  latency_ms, error_message, schema_hash,
  records_available, checked_at

connector_templates [MVP-NOW]
  id, vendor_name, protocol,
  auth_method (oauth2/odbc/api_key/service_account/none),
  config_schema (JSON), default_sync_schedule,
  default_rate_limit, redaction_tier,
  setup_instructions (markdown),
  created_at, catalog_version

coverage_gaps [v1.1]
  id, domain, gap_description,
  request_count_90d, request_percentage_90d,
  suggested_system_catalog_id,
  status (open/acknowledged/resolved),
  resolved_by, resolved_at,
  created_at, updated_at
```

#### 12.9.2 Extended Columns on Existing Tables

```
data_sources: add discovered_source_id (FK), connector_template_id (FK),
              sync_schedule, last_sync_at, last_sync_status,
              health_status, schema_hash

documents: add redaction_status (none/pending/partial/complete),
           derivative_path, original_locked (boolean)

exemption_flags: add detection_tier (1/2/3), detection_method,
                 auto_detected (boolean)

model_registry: add supports_ner (boolean), supports_vision (boolean)
```

### 12.10 Implementation Phasing

| Phase | What Ships | Clerk Experience | IT Dependency |
|---|---|---|---|
| **MVP-NOW** | Systems Catalog JSON. Guided onboarding interview. City profile + gap map. File/email/manual connectors. Tier 1 redaction (RegEx PII). Discovery dashboard (manual trigger). | Clerk answers setup questions, confirms systems, sees gap map. Can search email and file shares. SSNs and phone numbers auto-flagged. | IT provides network details, sets up service accounts for email/file share. |
| **v1.1** | Network discovery (IT opt-in). Confidence scoring. Health monitoring + self-healing. REST API connectors (Tyler, Accela). ODBC/JDBC bridge. Coverage gap analysis. Tier 2 NER redaction. | System finds sources clerk didn't know about. Broken connections self-heal. Coverage gaps on dashboard. AI flags names and medical info. | IT authorizes scan scope, provides DB credentials, reviews unknown services. |
| **v2.0** | API probing for vendor detection. Schema drift detection. LLM database characterization. RPA bridge. Community catalog. GIS/vendor SDK connectors. Tier 3 visual AI. Webhook connectors. | Auto-detects vendor software. Body cam face/plate blurring proposals. Legacy systems via RPA. Full coverage. | IT manages GPU hardware, reviews schema drift and RPA configs. |

### 12.11 Engineering Acceptance Criteria

1. Onboarding interview completable by a clerk without IT staff present.
2. Network discovery explicitly opt-in, off by default, logged before any scan.
3. No connector may access source data without explicit admin authorization in audit log.
4. Every connector must implement `health_check()` and surface unhealthy connections on Dashboard within one heartbeat cycle.
5. Credential storage AES-256 encrypted. Never in logs, exports, or UI after entry.
6. Gap map updates automatically as sources connect and request patterns change.
7. Tier 1 redaction must flag SSNs, credit cards, and phone numbers with zero false negatives on test corpus.
8. All redaction proposal-only. No automated redaction without human approval.
9. Discovery dashboard follows design system tokens (Section 6), including loading, empty, error, and disabled states.
10. Every discovery, connection, and redaction event generates tamper-proof audit log entry.
11. Public safety connectors must not activate until CJIS compliance checklist confirmed. Confirmation recorded in audit log.
12. Schema metadata from automated characterization stored encrypted, never in plaintext in logs, UI, or exports.
13. RPA connectors must include self-diagnostic failure detection and auto-suspend when target UI changes break extraction.

### 12.12 Glossary for Non-Technical Readers

| Term | What It Means |
|---|---|
| **API** | A standard way for two software systems to talk to each other. Like a phone number for a computer program. |
| **CJIS** | FBI division setting security rules for any system accessing police records or criminal justice data. |
| **CJI** | Criminal Justice Information — arrest records, incident reports, booking photos, criminal history. |
| **Connector** | A software module that knows how to talk to one specific type of system and bring records back in a standard format. |
| **Confidence Score** | A percentage indicating how certain the system is about what it found during a network scan. |
| **Coverage Gap** | A category of records people frequently request but the system doesn't have a source connected for. |
| **Discovery Run** | A scheduled or manual scan of the city's network to find data sources. |
| **Gap Map** | A list of functional areas where the city should have data but hasn't identified a source. |
| **Health Check** | A periodic test to make sure a data source connection is still working. |
| **NER** | Named Entity Recognition — AI that identifies people's names, organizations, and locations in text. |
| **OAuth2** | A secure way to grant read access to a cloud service without sharing your password. |
| **ODBC / JDBC** | Standardized adapters for connecting to databases. |
| **OCR** | Technology that reads text from images — scanned documents, handwritten notes. |
| **PII** | Personally Identifiable Information — SSNs, phone numbers, addresses, email addresses. |
| **Redaction** | Blacking out sensitive information before public release. Always proposed by system, approved by human. |
| **RegEx** | A text pattern describing a format (e.g., SSN pattern). Used for reliable structured data detection. |
| **RPA** | Robotic Process Automation — software mimicking human actions to extract data from old systems. Last resort. |
| **Schema Drift** | When a vendor updates their system and database structure changes. Connector needs to adapt. |
| **Self-Healing** | The system's ability to automatically fix common connection problems without human intervention. |

---

## 13. Phased Rollout Roadmap

| Phase | What | Why | Exit Criteria |
|---|---|---|---|
| **0. Foundations** | Token set, component library, sidebar shell, content model | Prevents design drift and rework | Team agrees on tokens, components, and page patterns. **COMPLETE.** |
| **1. Staff redesign** | Redesign 11 pages: 8 existing + Onboarding Interview, City Profile, Discovery Dashboard shell | Delivers a polished, accessible staff workbench with onboarding flow | All pages match spec, WCAG 2.2 AA passes, onboarding interview produces a valid City Profile, 80+ tests green |
| **2. New features** | Fees, notifications, response letters, context manager, analytics, connector framework, systems catalog, file/email connectors, onboarding service, Tier 1 regex expansion | Fills operational gaps and enables data source connectivity from day one | Clerk can complete onboarding, connect at least one data source (file share or email), process a request end-to-end with Tier 1 PII auto-flagging |
| **3. Public portal + Discovery** | Public homepage, search, request wizard, tracker, help. Network discovery engine, confidence scoring, health monitoring, self-healing, REST API/ODBC connectors, coverage gap analysis, Tier 2 NER redaction | Biggest resident-facing value plus automated source discovery | Requester can submit, track, and receive records. Discovery engine finds and identifies sources on city network. At least one self-healing connection recovery verified. |
| **4. Transparency + Advanced** | Open records library, analytics, public archive, federation. API probing, schema drift detection, LLM database characterization, RPA bridge, community catalog, GIS/vendor SDK connectors, Tier 3 visual AI, webhooks | Turns compliance into proactive transparency with full data landscape coverage | City can publish record sets, measure self-service adoption, and connect to any municipal system type including legacy |

---

## Appendix A: Migration from v0.1.0

### Status Value Migration

```sql
-- Rename existing statuses to match new terminology
UPDATE records_requests SET status = 'fulfilled' WHERE status = 'sent';
-- 'received', 'searching', 'in_review', 'drafted', 'approved' remain valid
-- New statuses added: 'clarification_needed', 'assigned', 'ready_for_release', 'fulfilled', 'closed'
```

### New Database Tables (Alembic migration)

```
departments
fee_schedules
fee_line_items
request_timeline
request_messages
response_letters
notification_templates
notification_log
prompt_templates
city_profile
system_catalog
connector_templates
saved_searches (v1.1)
published_records (v1.1)
redaction_ledger (v1.1)
discovered_sources (v1.1)
discovery_runs (v1.1)
source_health_log (v1.1)
coverage_gaps (v1.1)
record_collections (v2.0)
```

### New Columns on Existing Tables

```
users: department_id
documents: display_name, department_id, redaction_status, derivative_path, original_locked
records_requests: requester_phone, requester_type, scope_assessment,
                  department_id, estimated_fee, fee_status,
                  fee_waiver_requested, priority, closed_at, closure_reason
search_results: normalized_score
exemption_flags: review_note, detection_tier, detection_method, auto_detected
model_registry: context_window_size, supports_ner, supports_vision
data_sources: discovered_source_id, connector_template_id, sync_schedule,
              last_sync_at, last_sync_status, health_status, schema_hash
```

---

## Appendix B: File Manifest

| File | Purpose | Phase |
|---|---|---|
| `docs/UNIFIED-SPEC.md` | This document — single source of truth | — |
| `docs/DESIGN-CRITIQUE.md` | Design audit of v0.1.0 UI | Reference |
| `docs/superpowers/specs/2026-04-11-civicrecords-ai-master-design.md` | Original build spec (superseded) | Archive |
| `QA-VERIFICATION-REPORT.docx` | v0.1.0 QA report | Reference |
| Municipal Open Records UX Style Guide | External design direction document (informed Sections 6, 7, 8) | Reference |
| `Section12-Universal-Discovery.docx` | Original source for Section 12 (now integrated into this spec) | Archive |

---

*This specification was assembled from the original master design spec (67 commits, 80 tests, 5 sub-projects), a live UI design critique of 8 running pages, the Municipal Open Records UX Style Guide, context-mode architectural patterns, and the Universal Discovery & Connection Architecture. It represents the complete product vision for CivicRecords AI from v1.0 through v2.0.*
