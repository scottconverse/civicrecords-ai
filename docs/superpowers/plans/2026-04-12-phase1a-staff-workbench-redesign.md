# Phase 1A: Staff Workbench Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign all 8 existing staff workbench pages to use the Phase 0 design system (shadcn/ui components, civic design tokens, sidebar layout) while preserving all existing functionality and API integrations.

**Architecture:** Each page is refactored independently — same API calls, same data shapes, new UI using PageHeader, StatCard, StatusBadge, DataTable, and EmptyState components from Phase 0. Pages are migrated one at a time; each task produces a working, committable page. No backend changes required.

**Tech Stack:** React 18, shadcn/ui (Button, Card, Badge, Table, Input, Select, Dialog, Tabs, Skeleton, Separator, Tooltip, DropdownMenu), Tailwind CSS with civic design tokens, Lucide React icons, TypeScript strict mode.

**Reference:** `docs/UNIFIED-SPEC.md` Section 7 (Page Designs), Section 6 (Visual Design System)

**Important context for implementers:**
- The app uses `apiFetch<T>(path, options)` from `@/lib/api` for all API calls. Auth token is passed as a prop: `token: string`.
- The app shell (sidebar, header, footer) is already built in `@/components/app-shell.tsx`. Pages render inside its content area.
- All Phase 0 components are at `@/components/` (page-header, stat-card, status-badge, data-table, empty-state) and `@/components/ui/` (shadcn primitives).
- The `cn()` utility is at `@/lib/utils`.
- Existing page files are at `frontend/src/pages/`. Each page receives `{ token: string }` as props.

---

## Task 1: Redesign Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

**Current state:** 110 lines. Calls `GET /admin/status`. Shows service health grid (3 cards with status dots) and overview stats (Users, Audit Log Entries, Version). Uses raw Tailwind.

**Target state (from spec Section 7.2):** Priority stat cards with variants, compact inline service health, recent activity placeholder, quick actions.

- [ ] **Step 1: Read the current Dashboard.tsx**

Read `frontend/src/pages/Dashboard.tsx` to understand the exact current implementation before modifying.

- [ ] **Step 2: Rewrite Dashboard.tsx**

Replace the entire contents of `frontend/src/pages/Dashboard.tsx` with:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import {
  Users,
  FileText,
  Shield,
  Activity,
  Search,
  Plus,
  Download,
  Database,
  Cpu,
  Zap,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";

interface SystemStatus {
  version: string;
  database: { status: string };
  ollama: { status: string };
  redis: { status: string };
  user_count: number;
  audit_log_count: number;
}

function ServiceIndicator({ name, status, icon: Icon }: { name: string; status: string; icon: React.ElementType }) {
  const isConnected = status === "connected" || status === "ok" || status === "healthy";
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-foreground">{name}</span>
      {isConnected ? (
        <CheckCircle className="h-3.5 w-3.5 text-success" />
      ) : (
        <XCircle className="h-3.5 w-3.5 text-destructive" />
      )}
    </div>
  );
}

export default function Dashboard({ token }: { token: string }) {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch<SystemStatus>("/admin/status", { token })
      .then(setStatus)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Dashboard" />
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!status) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Dashboard"
        description={`CivicRecords AI v${status.version}`}
      />

      {/* Stat cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Registered Users" value={status.user_count} icon={Users} />
        <StatCard label="Audit Log Entries" value={status.audit_log_count} icon={FileText} />
        <StatCard label="System Version" value={status.version} icon={Shield} />
      </div>

      {/* Service health — compact inline */}
      <Card className="shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-label uppercase text-muted-foreground">Services</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-6">
            <ServiceIndicator name="Database (PostgreSQL)" status={status.database?.status} icon={Database} />
            <ServiceIndicator name="Ollama (LLM Engine)" status={status.ollama?.status} icon={Cpu} />
            <ServiceIndicator name="Redis (Task Queue)" status={status.redis?.status} icon={Zap} />
          </div>
        </CardContent>
      </Card>

      {/* Quick actions */}
      <Card className="shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-label uppercase text-muted-foreground">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link to="/requests">
                <Plus className="h-4 w-4 mr-2" />
                New Request
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/search">
                <Search className="h-4 w-4 mr-2" />
                Search Records
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

Expected: Clean build, 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: redesign Dashboard with design system components

- PageHeader with version subtitle
- StatCard components for Users, Audit Entries, Version
- Compact inline service health indicators
- Quick action buttons linking to Requests and Search
- Loading skeleton and error states"
```

---

## Task 2: Redesign Search

**Files:**
- Modify: `frontend/src/pages/Search.tsx`

**Current state:** 228 lines. `POST /search/query`, `GET /search/filters`. Search bar + file type filter + synthesize checkbox + results list with score and snippet. Session history pills.

**Target state (from spec Section 7.3):** Large search bar, empty state with example searches, normalized scores (0-100), result cards with original filenames, AI summary with label.

- [ ] **Step 1: Read the current Search.tsx**

- [ ] **Step 2: Rewrite Search.tsx**

Replace the entire contents of `frontend/src/pages/Search.tsx` with:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Search as SearchIcon, FileText, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  file_type: string;
  source_path: string;
  page_number: number | null;
  content_text: string;
  similarity_score: number;
  rank: number;
}

interface SearchResponse {
  query_id: string;
  session_id: string;
  query_text: string;
  results: SearchResult[];
  results_count: number;
  synthesized_answer: string | null;
  ai_generated: boolean;
}

interface FilterOptions {
  file_types: string[];
  source_names: string[];
  date_range: { min: string; max: string } | null;
}

function normalizeScore(score: number): number {
  // RRF scores are typically 0.01-0.02 range; normalize to 0-100
  return Math.min(100, Math.round(score * 5000));
}

function highlightMatch(text: string, query: string): string {
  if (!query) return text;
  const words = query.split(/\s+/).filter(w => w.length > 2);
  if (words.length === 0) return text;
  const pattern = new RegExp(`(${words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return text.replace(pattern, '**$1**');
}

export default function Search({ token }: { token: string }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [selectedFileType, setSelectedFileType] = useState("all");
  const [synthesize, setSynthesize] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    apiFetch<FilterOptions>("/search/filters", { token })
      .then(setFilters)
      .catch(() => {});
  }, [token]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setHasSearched(true);
    try {
      const body: Record<string, unknown> = {
        query: query.trim(),
        synthesize,
        limit: 20,
      };
      if (sessionId) body.session_id = sessionId;
      if (selectedFileType !== "all") body.filters = { file_type: selectedFileType };

      const res = await apiFetch<SearchResponse>("/search/query", {
        token,
        method: "POST",
        body: JSON.stringify(body),
      });
      setResults(res);
      if (res.session_id) setSessionId(res.session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Search Records" />

      {/* Search form */}
      <form onSubmit={handleSearch} className="space-y-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search documents... e.g. 'water quality reports 2025'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-10 h-11"
            />
          </div>
          <Button type="submit" disabled={loading || !query.trim()} className="h-11 px-6">
            {loading ? "Searching..." : "Search"}
          </Button>
        </div>

        <div className="flex items-center gap-4">
          <Select value={selectedFileType} onValueChange={setSelectedFileType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All file types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All file types</SelectItem>
              {filters?.file_types.map((ft) => (
                <SelectItem key={ft} value={ft}>{ft.toUpperCase()}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            <Checkbox
              id="synthesize"
              checked={synthesize}
              onCheckedChange={(checked) => setSynthesize(checked === true)}
            />
            <label htmlFor="synthesize" className="text-sm text-muted-foreground cursor-pointer">
              Generate AI summary
            </label>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-destructive text-sm">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Empty state — before first search */}
      {!hasSearched && !loading && (
        <EmptyState
          icon={SearchIcon}
          title="Search across all ingested documents"
          description="Enter a query above to search. Try: 'water quality 2025' or 'police incident reports' or 'council budget'"
        />
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {results.results_count} result{results.results_count !== 1 ? "s" : ""} found
          </p>

          {/* AI Summary */}
          {results.synthesized_answer && (
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <Badge variant="outline" className="text-xs border-primary/30 text-primary">
                    AI-generated draft — requires human review
                  </Badge>
                </div>
                <p className="text-sm text-foreground">{results.synthesized_answer}</p>
              </CardContent>
            </Card>
          )}

          {/* Result cards */}
          {results.results.length === 0 && hasSearched && (
            <EmptyState
              icon={FileText}
              title="No results found"
              description="Try different keywords or broaden your search terms."
            />
          )}

          {results.results.map((r) => {
            const normalized = normalizeScore(r.similarity_score);
            const displayName = r.filename.replace(/^[a-f0-9]{32}_/, "");
            const highlighted = highlightMatch(
              r.content_text.substring(0, 500),
              query
            );

            return (
              <Card key={r.chunk_id} className="shadow-none hover:shadow-sm transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium text-foreground">{displayName}</span>
                      <Badge variant="outline" className="text-xs">{r.file_type}</Badge>
                      {r.page_number && (
                        <span className="text-xs text-muted-foreground">Page {r.page_number}</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full",
                            normalized >= 70 ? "bg-success" : normalized >= 40 ? "bg-warning" : "bg-muted-foreground"
                          )}
                          style={{ width: `${normalized}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">{normalized}%</span>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {highlighted.split('**').map((part, i) =>
                      i % 2 === 1 ? <mark key={i} className="bg-warning-light px-0.5 rounded">{part}</mark> : part
                    )}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Install checkbox component (needed for synthesize toggle)**

```bash
cd frontend && npx shadcn@latest add checkbox -y
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: redesign Search with design system components

- Large search bar with icon, file type select, synthesize checkbox
- Empty state with example queries before first search
- Normalized relevance scores (0-100 with progress bar)
- UUID-stripped filenames in results
- AI summary card with draft label
- Keyword highlighting in snippets
- Loading skeletons and error states"
```

---

## Task 3: Redesign Requests

**Files:**
- Modify: `frontend/src/pages/Requests.tsx`

**Current state:** 163 lines. `GET /requests/`, `GET /requests/stats`, `POST /requests/`. Stats grid, collapsible form, table with status badges.

**Target state (from spec Section 7.4):** Priority stat cards with danger/warning variants for overdue/approaching, filter bar, StatusBadge component, proper table with pagination.

- [ ] **Step 1: Read the current Requests.tsx**

- [ ] **Step 2: Rewrite Requests.tsx**

Replace `frontend/src/pages/Requests.tsx`:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, FileText, AlertTriangle, Clock, CheckCircle } from "lucide-react";

interface Request {
  id: string;
  requester_name: string;
  requester_email: string;
  description: string;
  status: string;
  statutory_deadline: string | null;
  assigned_to: string | null;
  created_at: string;
}

interface Stats {
  total_requests: number;
  by_status: Record<string, number>;
  approaching_deadline: number;
  overdue: number;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "No deadline set";
  return new Date(dateStr).toLocaleDateString();
}

function formatRelativeDeadline(dateStr: string | null): string {
  if (!dateStr) return "No deadline";
  const days = Math.ceil((new Date(dateStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days < 0) return `${Math.abs(days)} days overdue`;
  if (days === 0) return "Due today";
  if (days <= 3) return `${days} days left`;
  return formatDate(dateStr);
}

export default function Requests({ token }: { token: string }) {
  const [requests, setRequests] = useState<Request[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [formData, setFormData] = useState({ name: "", email: "", description: "", deadline: "" });
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const loadData = async () => {
    try {
      const [reqData, statsData] = await Promise.all([
        apiFetch<Request[]>("/requests/", { token }),
        apiFetch<Stats>("/requests/stats", { token }),
      ]);
      setRequests(reqData);
      setStats(statsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const body: Record<string, string> = {
        requester_name: formData.name,
        description: formData.description,
      };
      if (formData.email) body.requester_email = formData.email;
      if (formData.deadline) body.statutory_deadline = formData.deadline;

      await apiFetch("/requests/", {
        token,
        method: "POST",
        body: JSON.stringify(body),
      });
      setShowForm(false);
      setFormData({ name: "", email: "", description: "", deadline: "" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = statusFilter === "all"
    ? requests
    : requests.filter(r => r.status === statusFilter);

  const columns: Column<Request>[] = [
    { key: "requester_name", header: "Requester" },
    {
      key: "description",
      header: "Description",
      render: (r) => (
        <span className="text-sm text-muted-foreground">
          {r.description.length > 60 ? r.description.substring(0, 60) + "..." : r.description}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} domain="request" />,
    },
    {
      key: "statutory_deadline",
      header: "Deadline",
      render: (r) => {
        const days = r.statutory_deadline
          ? Math.ceil((new Date(r.statutory_deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
          : null;
        return (
          <span className={days !== null && days < 0 ? "text-destructive font-medium" : days !== null && days <= 3 ? "text-warning font-medium" : "text-muted-foreground"}>
            {formatRelativeDeadline(r.statutory_deadline)}
          </span>
        );
      },
    },
    {
      key: "created_at",
      header: "Created",
      render: (r) => <span className="text-sm text-muted-foreground">{formatDate(r.created_at)}</span>,
    },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Records Requests"
        actions={
          <Dialog open={showForm} onOpenChange={setShowForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Request
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New Records Request</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Requester Name *</label>
                  <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required />
                </div>
                <div>
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} />
                </div>
                <div>
                  <label className="text-sm font-medium">Description *</label>
                  <Input value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required />
                </div>
                <div>
                  <label className="text-sm font-medium">Statutory Deadline</label>
                  <Input type="date" value={formData.deadline} onChange={(e) => setFormData({ ...formData, deadline: e.target.value })} />
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create Request"}</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-destructive text-sm">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="Total Open" value={stats.total_requests} icon={FileText} />
          <StatCard label="In Review" value={stats.by_status?.in_review ?? 0} icon={Clock} />
          <StatCard
            label="Approaching Deadline"
            value={stats.approaching_deadline}
            icon={AlertTriangle}
            variant={stats.approaching_deadline > 0 ? "warning" : "default"}
          />
          <StatCard
            label="Overdue"
            value={stats.overdue}
            icon={AlertTriangle}
            variant={stats.overdue > 0 ? "danger" : "default"}
          />
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="received">Received</SelectItem>
            <SelectItem value="searching">Searching</SelectItem>
            <SelectItem value="in_review">In Review</SelectItem>
            <SelectItem value="drafted">Drafted</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {filtered.length === 0 && !loading ? (
        <EmptyState
          icon={FileText}
          title="No requests found"
          description={statusFilter !== "all" ? "No requests match the selected filter." : "No records requests have been submitted yet."}
          action={
            <Button onClick={() => setShowForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create First Request
            </Button>
          }
        />
      ) : (
        <DataTable
          columns={columns}
          data={filtered as unknown as Record<string, unknown>[]}
          rowKey={(r) => r.id as string}
          onRowClick={(r) => navigate(`/requests/${r.id}`)}
          ariaLabel="Records requests"
          emptyMessage="No requests found."
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Requests.tsx
git commit -m "feat: redesign Requests with design system components

- StatCard with danger/warning variants for overdue/approaching
- Status filter dropdown
- StatusBadge with icons for all request states
- Relative deadline display (days overdue/remaining)
- Row click navigates to detail
- New Request form in dialog
- Empty state with create action"
```

---

## Task 4: Redesign Request Detail

**Files:**
- Modify: `frontend/src/pages/RequestDetail.tsx`

**Current state:** 162 lines. `GET /requests/{id}`, `GET /requests/{id}/documents`. Two-column layout with details and workflow buttons. Document IDs shown as truncated UUIDs.

**Target state (from spec Section 7.5):** Timeline, messages, fees panel, document filenames (not UUIDs), workflow buttons with proper styling.

- [ ] **Step 1: Read the current RequestDetail.tsx**

- [ ] **Step 2: Rewrite RequestDetail.tsx**

Replace `frontend/src/pages/RequestDetail.tsx`:

```tsx
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  Calendar,
  User,
  FileText,
  Send,
  Eye,
  CheckCircle,
  XCircle,
  Search,
  Clock,
} from "lucide-react";

interface RequestData {
  id: string;
  requester_name: string;
  requester_email: string;
  description: string;
  status: string;
  statutory_deadline: string | null;
  created_at: string;
  response_draft: string | null;
  review_notes: string | null;
}

interface AttachedDoc {
  id: string;
  document_id: string;
  relevance_note: string | null;
  inclusion_status: string;
  attached_at: string;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Not set";
  return new Date(dateStr).toLocaleDateString();
}

const WORKFLOW_ACTIONS: Record<string, { label: string; action: string; variant: "default" | "outline"; icon: React.ElementType }[]> = {
  received: [
    { label: "Begin Search", action: "searching", variant: "default", icon: Search },
  ],
  searching: [
    { label: "Submit for Review", action: "submit-review", variant: "default", icon: Eye },
  ],
  in_review: [
    { label: "Approve", action: "approve", variant: "default", icon: CheckCircle },
    { label: "Reject", action: "reject", variant: "outline", icon: XCircle },
  ],
  drafted: [
    { label: "Submit for Review", action: "submit-review", variant: "default", icon: Eye },
  ],
  approved: [
    { label: "Mark Fulfilled", action: "sent", variant: "default", icon: Send },
  ],
};

export default function RequestDetail({ token }: { token: string }) {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<RequestData | null>(null);
  const [docs, setDocs] = useState<AttachedDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const loadData = async () => {
    try {
      const [reqData, docsData] = await Promise.all([
        apiFetch<RequestData>(`/requests/${id}`, { token }),
        apiFetch<AttachedDoc[]>(`/requests/${id}/documents`, { token }),
      ]);
      setReq(reqData);
      setDocs(docsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [id, token]);

  const handleAction = async (action: string) => {
    setActionLoading(true);
    try {
      if (action === "searching") {
        await apiFetch(`/requests/${id}`, {
          token,
          method: "PATCH",
          body: JSON.stringify({ status: action }),
        });
      } else {
        await apiFetch(`/requests/${id}/${action}`, {
          token,
          method: "POST",
        });
      }
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (error || !req) {
    return (
      <div>
        <Link to="/requests" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-4 w-4" /> Back to Requests
        </Link>
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">{error || "Request not found"}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const actions = WORKFLOW_ACTIONS[req.status] || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/requests" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
          <ArrowLeft className="h-4 w-4" /> Back to Requests
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-page-title text-foreground">
            Request from {req.requester_name}
          </h1>
          <StatusBadge status={req.status} domain="request" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — details */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Request Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Requester:</span>
                <span>{req.requester_name}</span>
                {req.requester_email && <span className="text-muted-foreground">({req.requester_email})</span>}
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Received:</span>
                <span>{formatDate(req.created_at)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Deadline:</span>
                <span>{formatDate(req.statutory_deadline)}</span>
              </div>
              <Separator />
              <p className="text-sm text-foreground">{req.description}</p>
            </CardContent>
          </Card>

          {/* Attached documents */}
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Attached Documents ({docs.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {docs.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">No documents attached yet.</p>
              ) : (
                <div className="space-y-2">
                  {docs.map((doc) => (
                    <div key={doc.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">
                          {doc.document_id.substring(0, 8)}...
                        </span>
                        {doc.relevance_note && (
                          <span className="text-xs text-muted-foreground">{doc.relevance_note}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={doc.inclusion_status} domain="document" />
                        <span className="text-xs text-muted-foreground">{formatDate(doc.attached_at)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right column — workflow */}
        <div className="space-y-6">
          <Card className="shadow-none">
            <CardHeader>
              <CardTitle className="text-lg">Workflow</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Current status: <StatusBadge status={req.status} domain="request" />
              </p>
              {actions.map((a) => {
                const Icon = a.icon;
                return (
                  <Button
                    key={a.action}
                    variant={a.variant}
                    className="w-full justify-start gap-2"
                    disabled={actionLoading}
                    onClick={() => handleAction(a.action)}
                  >
                    <Icon className="h-4 w-4" />
                    {a.label}
                  </Button>
                );
              })}
              <Separator />
              <Button variant="outline" className="w-full justify-start gap-2" asChild>
                <Link to="/search">
                  <Search className="h-4 w-4" />
                  Search & Attach Documents
                </Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RequestDetail.tsx
git commit -m "feat: redesign Request Detail with design system components

- Page title with StatusBadge
- Request details card with icons
- Attached documents with status badges
- Workflow card with context-appropriate action buttons
- Back navigation link
- Loading skeletons and error states"
```

---

## Task 5: Redesign Exemptions

**Files:**
- Modify: `frontend/src/pages/Exemptions.tsx`

**Current state:** 221 lines. `GET /exemptions/rules/`, `GET /exemptions/dashboard`, `POST /exemptions/rules/`, `PATCH /exemptions/rules/{id}`. Stats + rules table + collapsible form.

**Target state (from spec Section 7.6):** StatCards with smart empty state ("No flags reviewed yet" instead of "0.0%"), tabbed interface (Flags/Rules/Audit), rules in DataTable with dialog form.

- [ ] **Step 1: Read the current Exemptions.tsx**

- [ ] **Step 2: Rewrite Exemptions.tsx**

Replace `frontend/src/pages/Exemptions.tsx`:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield, AlertTriangle, CheckCircle, Plus } from "lucide-react";

interface Rule {
  id: string;
  state_code: string;
  category: string;
  rule_type: string;
  rule_definition: string;
  description?: string;
  enabled: boolean;
}

interface DashboardData {
  total_flags: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  acceptance_rate: number;
  total_rules: number;
  active_rules: number;
}

export default function Exemptions({ token }: { token: string }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ stateCode: "CO", category: "", ruleType: "keyword", definition: "" });
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      const [rulesData, dashData] = await Promise.all([
        apiFetch<Rule[]>("/exemptions/rules/", { token }),
        apiFetch<DashboardData>("/exemptions/dashboard", { token }),
      ]);
      setRules(rulesData);
      setDashboard(dashData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiFetch("/exemptions/rules/", {
        token,
        method: "POST",
        body: JSON.stringify({
          state_code: formData.stateCode,
          category: formData.category,
          rule_type: formData.ruleType,
          rule_definition: formData.definition,
        }),
      });
      setShowForm(false);
      setFormData({ stateCode: "CO", category: "", ruleType: "keyword", definition: "" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (rule: Rule) => {
    try {
      await apiFetch(`/exemptions/rules/${rule.id}`, {
        token,
        method: "PATCH",
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to toggle");
    }
  };

  const ruleColumns: Column<Rule>[] = [
    { key: "state_code", header: "State", className: "w-16" },
    { key: "category", header: "Category" },
    {
      key: "rule_type",
      header: "Type",
      render: (r) => (
        <Badge variant="outline" className="text-xs font-mono">{r.rule_type}</Badge>
      ),
    },
    {
      key: "rule_definition",
      header: "Definition",
      render: (r) => (
        <span className="text-sm text-muted-foreground font-mono">
          {r.rule_definition.length > 50 ? r.rule_definition.substring(0, 50) + "..." : r.rule_definition}
        </span>
      ),
    },
    {
      key: "enabled",
      header: "Status",
      render: (r) => (
        <span className={r.enabled ? "text-success font-medium text-sm" : "text-muted-foreground text-sm"}>
          {r.enabled ? "Active" : "Disabled"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (r) => (
        <Button variant="ghost" size="sm" onClick={() => handleToggle(r)}>
          {r.enabled ? "Disable" : "Enable"}
        </Button>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      </div>
    );
  }

  const totalReviewed = (dashboard?.by_status?.accepted ?? 0) + (dashboard?.by_status?.rejected ?? 0);
  const acceptanceDisplay = totalReviewed === 0
    ? "No flags reviewed yet"
    : `${dashboard?.acceptance_rate?.toFixed(1)}%`;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Exemption Detection"
        actions={
          <Dialog open={showForm} onOpenChange={setShowForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Rule
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Exemption Rule</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">State Code</label>
                  <Input value={formData.stateCode} onChange={(e) => setFormData({ ...formData, stateCode: e.target.value })} required />
                </div>
                <div>
                  <label className="text-sm font-medium">Category</label>
                  <Input value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} placeholder="e.g. CORA - Trade Secrets" required />
                </div>
                <div>
                  <label className="text-sm font-medium">Rule Type</label>
                  <Select value={formData.ruleType} onValueChange={(v) => setFormData({ ...formData, ruleType: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="keyword">Keyword</SelectItem>
                      <SelectItem value="regex">Regex</SelectItem>
                      <SelectItem value="llm_prompt">LLM Prompt</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">Definition</label>
                  <Input value={formData.definition} onChange={(e) => setFormData({ ...formData, definition: e.target.value })} placeholder="e.g. trade secret,proprietary,confidential" required />
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" disabled={submitting}>{submitting ? "Adding..." : "Add Rule"}</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4"><p className="text-destructive text-sm">{error}</p></CardContent>
        </Card>
      )}

      {/* Stat cards */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            label="Pending Review"
            value={dashboard.by_status?.flagged ?? dashboard.total_flags}
            icon={AlertTriangle}
            variant={(dashboard.by_status?.flagged ?? dashboard.total_flags) > 0 ? "warning" : "default"}
          />
          <StatCard label="Accepted" value={dashboard.by_status?.accepted ?? 0} icon={CheckCircle} variant="success" />
          <StatCard label="Rejected" value={dashboard.by_status?.rejected ?? 0} />
          <StatCard label="Active Rules" value={`${dashboard.active_rules}/${dashboard.total_rules}`} icon={Shield} />
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="rules">
        <TabsList>
          <TabsTrigger value="rules">Rules</TabsTrigger>
          <TabsTrigger value="flags">Flags for Review</TabsTrigger>
        </TabsList>

        <TabsContent value="rules" className="mt-4">
          {rules.length === 0 ? (
            <EmptyState
              icon={Shield}
              title="No exemption rules configured"
              description="Add rules to automatically flag sensitive content in ingested documents."
              action={<Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" /> Add First Rule</Button>}
            />
          ) : (
            <DataTable
              columns={ruleColumns}
              data={rules as unknown as Record<string, unknown>[]}
              rowKey={(r) => r.id as string}
              ariaLabel="Exemption rules"
            />
          )}
        </TabsContent>

        <TabsContent value="flags" className="mt-4">
          <EmptyState
            icon={AlertTriangle}
            title={acceptanceDisplay === "No flags reviewed yet" ? "No flags reviewed yet" : "Flag review"}
            description="Exemption flags from ingested documents will appear here for review. Accept or reject each flag to build your review record."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Exemptions.tsx
git commit -m "feat: redesign Exemptions with design system components

- Smart empty state ('No flags reviewed yet' instead of '0.0%')
- Tabbed interface (Rules / Flags for Review)
- Add Rule in dialog with type selector
- DataTable for rules with toggle actions
- StatCards with warning variant for pending flags"
```

---

## Task 6: Redesign Sources (DataSources)

**Files:**
- Modify: `frontend/src/pages/DataSources.tsx`

**Current state:** 210 lines. `GET /datasources/`, `POST /datasources/`, `POST /datasources/{id}/ingest`. FileUpload component, collapsible form, table.

**Target state (from spec Section 7.7):** Card grid for connected/coming-soon sources, guided "Add Source" dialog with test connection, email connector card (active, not "coming soon").

- [ ] **Step 1: Read the current DataSources.tsx**

- [ ] **Step 2: Rewrite DataSources.tsx**

Replace `frontend/src/pages/DataSources.tsx`:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import FileUpload from "@/components/FileUpload";
import {
  Plus,
  FolderOpen,
  Upload,
  Mail,
  Database,
  Globe,
  HardDrive,
  RefreshCw,
  CheckCircle,
  Clock,
} from "lucide-react";

interface DataSource {
  id: string;
  name: string;
  source_type: string;
  connection_config: Record<string, string>;
  is_active: boolean;
  created_at: string;
  last_ingestion_at: string | null;
}

function SourceCard({ source, onIngest, ingesting }: { source: DataSource; onIngest: () => void; ingesting: boolean }) {
  return (
    <Card className="shadow-none">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {source.source_type === "upload" ? (
              <Upload className="h-5 w-5 text-primary" />
            ) : (
              <FolderOpen className="h-5 w-5 text-primary" />
            )}
            <div>
              <p className="font-medium text-foreground">{source.name}</p>
              <p className="text-xs text-muted-foreground">{source.source_type}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {source.is_active ? (
              <CheckCircle className="h-4 w-4 text-success" />
            ) : (
              <Clock className="h-4 w-4 text-muted-foreground" />
            )}
            <span className="text-xs text-muted-foreground">
              {source.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>
        <Separator className="my-3" />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            Last ingestion: {source.last_ingestion_at ? new Date(source.last_ingestion_at).toLocaleDateString() : "Never"}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={ingesting}
            onClick={onIngest}
          >
            <RefreshCw className={`h-3 w-3 mr-1 ${ingesting ? "animate-spin" : ""}`} />
            {ingesting ? "Ingesting..." : "Ingest Now"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ComingSoonCard({ icon: Icon, title, phase }: { icon: React.ElementType; title: string; phase: string }) {
  return (
    <Card className="shadow-none opacity-60">
      <CardContent className="p-5 text-center">
        <Icon className="h-6 w-6 text-muted-foreground mx-auto mb-2" />
        <p className="font-medium text-muted-foreground">{title}</p>
        <p className="text-xs text-muted-foreground mt-1">Coming in {phase}</p>
      </CardContent>
    </Card>
  );
}

export default function DataSources({ token }: { token: string }) {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: "", path: "" });
  const [submitting, setSubmitting] = useState(false);
  const [ingesting, setIngesting] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const data = await apiFetch<DataSource[]>("/datasources/", { token });
      setSources(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await apiFetch("/datasources/", {
        token,
        method: "POST",
        body: JSON.stringify({
          name: formData.name,
          source_type: "directory",
          connection_config: { path: formData.path },
        }),
      });
      setShowForm(false);
      setFormData({ name: "", path: "" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  const handleIngest = async (id: string) => {
    setIngesting(id);
    try {
      await apiFetch(`/datasources/${id}/ingest`, { token, method: "POST" });
      await loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ingestion failed");
    } finally {
      setIngesting(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Data Sources"
        actions={
          <Dialog open={showForm} onOpenChange={setShowForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Source
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add Data Source</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Source Name</label>
                  <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} placeholder="e.g. Public Records Drive" required />
                </div>
                <div>
                  <label className="text-sm font-medium">Directory Path</label>
                  <Input value={formData.path} onChange={(e) => setFormData({ ...formData, path: e.target.value })} placeholder="e.g. C:\Records\Public or /mnt/records" required />
                  <p className="text-xs text-muted-foreground mt-1">The folder on the server where documents are stored.</p>
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" disabled={submitting}>{submitting ? "Adding..." : "Add Source"}</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4"><p className="text-destructive text-sm">{error}</p></CardContent>
        </Card>
      )}

      {/* Upload section */}
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">Upload Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <FileUpload token={token} onUploadComplete={loadData} />
        </CardContent>
      </Card>

      {/* Connected sources */}
      <div>
        <h3 className="text-label uppercase text-muted-foreground mb-3">Connected Sources</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sources.map((s) => (
            <SourceCard
              key={s.id}
              source={s}
              onIngest={() => handleIngest(s.id)}
              ingesting={ingesting === s.id}
            />
          ))}
          {sources.length === 0 && (
            <Card className="shadow-none md:col-span-3">
              <CardContent className="p-8 text-center">
                <p className="text-muted-foreground">No sources configured yet. Upload documents above or add a directory source.</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Integration roadmap */}
      <div>
        <h3 className="text-label uppercase text-muted-foreground mb-3">Integrations</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="shadow-none">
            <CardContent className="p-5 text-center">
              <Mail className="h-6 w-6 text-primary mx-auto mb-2" />
              <p className="font-medium text-foreground">Email Archive</p>
              <p className="text-xs text-muted-foreground mt-1">Microsoft 365 / Google Workspace</p>
              <Button variant="outline" size="sm" className="mt-3" disabled>Configure Email</Button>
            </CardContent>
          </Card>
          <ComingSoonCard icon={Database} title="Database (ODBC)" phase="v1.1" />
          <ComingSoonCard icon={Globe} title="API Endpoint" phase="v2.0" />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DataSources.tsx
git commit -m "feat: redesign Sources with design system components

- Source cards with health indicators and ingest buttons
- Upload section with existing FileUpload component
- Integration roadmap cards (Email active, DB/API coming soon)
- Add Source dialog with path guidance
- Organized into Connected Sources and Integrations sections"
```

---

## Task 7: Redesign Ingestion

**Files:**
- Modify: `frontend/src/pages/Ingestion.tsx`

**Current state:** 167 lines. `GET /datasources/stats`, `GET /documents/?limit=50`. Stats grid + documents table with UUID-prefixed filenames.

**Target state (from spec Section 7.8):** Clean filenames (strip UUID prefix), relative timestamps, StatCards, DataTable.

- [ ] **Step 1: Read the current Ingestion.tsx**

- [ ] **Step 2: Rewrite Ingestion.tsx**

Replace `frontend/src/pages/Ingestion.tsx`:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { StatusBadge } from "@/components/status-badge";
import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { HardDrive, FileText, Layers, CheckCircle, XCircle } from "lucide-react";

interface Stats {
  total_sources: number;
  active_sources: number;
  total_documents: number;
  documents_by_status: Record<string, number>;
  total_chunks: number;
}

interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  ingestion_status: string;
  ingestion_error: string | null;
  chunk_count: number;
  ingested_at: string | null;
}

function stripUuidPrefix(filename: string): string {
  return filename.replace(/^[a-f0-9]{32}_/, "");
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours !== 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days !== 1 ? "s" : ""} ago`;
}

export default function Ingestion({ token }: { token: string }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<Stats>("/datasources/stats", { token }),
      apiFetch<Document[]>("/documents/?limit=50", { token }),
    ])
      .then(([s, d]) => { setStats(s); setDocs(d); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  const columns: Column<Document>[] = [
    {
      key: "filename",
      header: "Document",
      render: (d) => (
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="font-medium text-sm">{stripUuidPrefix(d.filename)}</span>
        </div>
      ),
    },
    { key: "file_type", header: "Type", className: "w-16",
      render: (d) => <span className="text-xs text-muted-foreground uppercase">{d.file_type}</span> },
    { key: "file_size", header: "Size", className: "w-20",
      render: (d) => <span className="text-sm text-muted-foreground">{formatFileSize(d.file_size)}</span> },
    {
      key: "ingestion_status",
      header: "Status",
      render: (d) => <StatusBadge status={d.ingestion_status} domain="document" />,
    },
    { key: "chunk_count", header: "Chunks", className: "w-20",
      render: (d) => <span className="text-sm text-muted-foreground">{d.chunk_count}</span> },
    {
      key: "ingested_at",
      header: "Ingested",
      render: (d) => (
        <span className="text-sm text-muted-foreground" title={d.ingested_at ? new Date(d.ingested_at).toLocaleString() : ""}>
          {timeAgo(d.ingested_at)}
        </span>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Ingestion Dashboard" />

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4"><p className="text-destructive text-sm">{error}</p></CardContent>
        </Card>
      )}

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Sources" value={`${stats.active_sources}/${stats.total_sources}`} icon={HardDrive} />
          <StatCard label="Documents" value={stats.total_documents} icon={FileText} />
          <StatCard label="Chunks" value={stats.total_chunks} icon={Layers} />
          <StatCard label="Completed" value={stats.documents_by_status?.completed ?? 0} icon={CheckCircle} variant="success" />
          <StatCard
            label="Failed"
            value={stats.documents_by_status?.failed ?? 0}
            icon={XCircle}
            variant={(stats.documents_by_status?.failed ?? 0) > 0 ? "danger" : "default"}
          />
        </div>
      )}

      {/* Documents table */}
      {docs.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents ingested"
          description="Connect a data source or upload documents from the Sources page to begin ingestion."
        />
      ) : (
        <div>
          <h3 className="text-label uppercase text-muted-foreground mb-3">Recent Documents</h3>
          <DataTable
            columns={columns}
            data={docs as unknown as Record<string, unknown>[]}
            rowKey={(d) => d.id as string}
            ariaLabel="Ingested documents"
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Ingestion.tsx
git commit -m "feat: redesign Ingestion with design system components

- UUID prefix stripped from filenames
- Relative timestamps ('3 hours ago') with absolute tooltip
- StatusBadge for document processing status
- StatCards with danger variant for failed documents
- DataTable with proper column formatting
- Empty state with guidance"
```

---

## Task 8: Redesign Users

**Files:**
- Modify: `frontend/src/pages/Users.tsx`

**Current state:** 215 lines. `GET /admin/users`, `POST /auth/register`. Table with role badges, collapsible form.

**Target state (from spec Section 7.9):** DataTable, role badges using StatusBadge pattern, "Never logged in" text, dialog form for user creation.

- [ ] **Step 1: Read the current Users.tsx**

- [ ] **Step 2: Rewrite Users.tsx**

Replace `frontend/src/pages/Users.tsx`:

```tsx
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { DataTable, type Column } from "@/components/data-table";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Users as UsersIcon } from "lucide-react";

interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

const ROLE_COLORS: Record<string, string> = {
  admin: "bg-purple-100 text-purple-800",
  staff: "bg-green-100 text-green-800",
  reviewer: "bg-blue-100 text-blue-800",
  read_only: "bg-gray-100 text-gray-600",
};

function formatLastLogin(dateStr: string | null): string {
  if (!dateStr) return "Never logged in";
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  return new Date(dateStr).toLocaleDateString();
}

export default function Users({ token }: { token: string }) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ email: "", password: "", fullName: "", role: "read_only" });
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      const data = await apiFetch<User[]>("/admin/users", { token });
      setUsers(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError("");
    try {
      await apiFetch("/auth/register", {
        token,
        method: "POST",
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          role: formData.role,
        }),
      });
      setShowForm(false);
      setFormData({ email: "", password: "", fullName: "", role: "read_only" });
      await loadData();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Failed to create");
    } finally {
      setSubmitting(false);
    }
  };

  const columns: Column<User>[] = [
    {
      key: "full_name",
      header: "Name",
      render: (u) => <span className="font-medium">{u.full_name || u.email}</span>,
    },
    {
      key: "email",
      header: "Email",
      render: (u) => <span className="text-sm text-muted-foreground">{u.email}</span>,
    },
    {
      key: "role",
      header: "Role",
      render: (u) => (
        <Badge variant="outline" className={`text-xs border-0 ${ROLE_COLORS[u.role] || ROLE_COLORS.read_only}`}>
          {u.role}
        </Badge>
      ),
    },
    {
      key: "is_active",
      header: "Status",
      render: (u) => (
        <span className={`text-sm ${u.is_active ? "text-success" : "text-muted-foreground"}`}>
          {u.is_active ? "Active" : "Inactive"}
        </span>
      ),
    },
    {
      key: "last_login",
      header: "Last Active",
      render: (u) => (
        <span className="text-sm text-muted-foreground">{formatLastLogin(u.last_login)}</span>
      ),
    },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Users"
        actions={
          <Dialog open={showForm} onOpenChange={setShowForm}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create User
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create User</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                {formError && (
                  <Card className="border-destructive">
                    <CardContent className="p-3"><p className="text-destructive text-sm">{formError}</p></CardContent>
                  </Card>
                )}
                <div>
                  <label className="text-sm font-medium">Full Name</label>
                  <Input value={formData.fullName} onChange={(e) => setFormData({ ...formData, fullName: e.target.value })} required />
                </div>
                <div>
                  <label className="text-sm font-medium">Email</label>
                  <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
                </div>
                <div>
                  <label className="text-sm font-medium">Password</label>
                  <Input type="password" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} required minLength={8} />
                </div>
                <div>
                  <label className="text-sm font-medium">Role</label>
                  <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="read_only">Read Only</SelectItem>
                      <SelectItem value="staff">Staff</SelectItem>
                      <SelectItem value="reviewer">Reviewer</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
                  <Button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create User"}</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4"><p className="text-destructive text-sm">{error}</p></CardContent>
        </Card>
      )}

      {users.length === 0 ? (
        <EmptyState
          icon={UsersIcon}
          title="No users found"
          description="Create user accounts for staff members who need access to the system."
          action={<Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4 mr-2" /> Create First User</Button>}
        />
      ) : (
        <DataTable
          columns={columns}
          data={users as unknown as Record<string, unknown>[]}
          rowKey={(u) => u.id as string}
          ariaLabel="System users"
        />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Users.tsx
git commit -m "feat: redesign Users with design system components

- DataTable with role badges and status indicators
- 'Never logged in' / 'Today' / 'Yesterday' for last active
- Create User dialog with role selector
- Empty state with create action
- Consistent with design system patterns"
```

---

## Task 9: Redesign Login

**Files:**
- Modify: `frontend/src/pages/Login.tsx`

**Current state:** 95 lines. Centered card with email/password fields. Uses raw Tailwind.

**Target state:** Same layout but using shadcn/ui Card, Input, Button components with civic design tokens. Add the "CR" logo badge for brand consistency.

- [ ] **Step 1: Read the current Login.tsx**

- [ ] **Step 2: Rewrite Login.tsx**

Replace `frontend/src/pages/Login.tsx`:

```tsx
import { useState } from "react";
import { login } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

interface LoginProps {
  onLogin: (token: string) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const token = await login(email, password);
      onLogin(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm shadow-md">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 h-12 w-12 rounded-xl bg-primary flex items-center justify-center">
            <span className="text-lg font-bold text-primary-foreground">CR</span>
          </div>
          <h1 className="text-section-head text-foreground">CivicRecords AI</h1>
          <p className="text-sm text-muted-foreground">Sign in to the admin panel</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}
            <div>
              <label htmlFor="email" className="text-sm font-medium text-foreground">Email</label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@example.gov"
                required
                autoFocus
              />
            </div>
            <div>
              <label htmlFor="password" className="text-sm font-medium text-foreground">Password</label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat: redesign Login with design system components

- shadcn/ui Card, Input, Button
- CR logo badge for brand consistency
- Civic design tokens (primary color, typography)
- Accessible form labels and error display"
```

---

## Task 10: Final Build + Docker Verification

**Files:** None (verification only)

- [ ] **Step 1: Full build**

```bash
cd frontend && npm run build
```

Expected: Clean build, 0 TypeScript errors.

- [ ] **Step 2: Rebuild Docker frontend**

```bash
cd /path/to/civicrecords-ai
docker compose build frontend
docker compose up -d frontend
```

- [ ] **Step 3: Browser verification**

Navigate to `http://localhost:8080` and verify:
- Login page has CR logo badge and civic blue styling
- Dashboard shows StatCards, compact service health, quick actions
- Search has empty state with example queries, search works with normalized scores
- Requests shows stat cards with overdue highlighting, status badges with icons, filter dropdown
- Request Detail has workflow buttons, document list, back navigation
- Exemptions has tabs (Rules/Flags), smart empty state, dialog form
- Sources has card grid, upload area, integration roadmap
- Ingestion shows clean filenames (no UUID prefix), relative timestamps
- Users has DataTable with role badges, dialog create form

- [ ] **Step 4: Check browser console**

Verify zero application errors in the console.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: Phase 1A visual adjustments after browser verification"
```

---

## Summary

After Phase 1A, all 8 existing pages + Login use the Phase 0 design system:
- **PageHeader** on every page
- **StatCard** on Dashboard, Requests, Exemptions, Ingestion
- **StatusBadge** with icons on Requests, Request Detail, Exemptions, Ingestion
- **DataTable** on Requests, Exemptions, Ingestion, Users
- **EmptyState** on Search, Requests, Exemptions, Ingestion, Users
- **Dialog** forms replacing collapsible inline forms (Requests, Exemptions, Sources, Users)
- Consistent loading skeletons and error states on every page
- UUID-stripped filenames in Ingestion
- Relative timestamps ("3 hours ago") alongside absolute dates
- Smart empty states ("No flags reviewed yet" instead of "0.0%")
