# Phase 0: Design Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install shadcn/ui, map the civic design tokens, replace the top nav with a sidebar layout shell, and create reusable domain components (StatusBadge, StatCard, DataTable, PageHeader) so that Phase 1 page redesigns can be done one page at a time without touching infrastructure.

**Architecture:** shadcn/ui components installed via CLI, design tokens mapped to CSS variables in `globals.css`, a new `AppShell` layout component wrapping all authenticated pages with a 240px sidebar + header + content area. Domain components built on top of shadcn primitives. All existing pages continue to work during the transition — no big-bang rewrite.

**Tech Stack:** React 18, shadcn/ui (Radix primitives), Tailwind CSS 3.4, Lucide React icons, class-variance-authority (already installed), TypeScript strict mode.

**Reference:** `docs/UNIFIED-SPEC.md` sections 6 (Visual Design System) and 7 (Page Designs — layout shell).

---

## File Structure

### New files to create:

```
frontend/
├── components.json                          ← shadcn/ui config
├── src/
│   ├── globals.css                          ← MODIFY: replace with design tokens
│   ├── components/
│   │   ├── ui/                              ← shadcn/ui primitives (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── card.tsx
│   │   │   ├── table.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── tooltip.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── dropdown-menu.tsx
│   │   ├── app-shell.tsx                    ← Sidebar + header layout
│   │   ├── sidebar-nav.tsx                  ← Navigation items with icons
│   │   ├── stat-card.tsx                    ← Metric card (label + value + trend)
│   │   ├── status-badge.tsx                 ← Status badge with icon + color mapping
│   │   ├── data-table.tsx                   ← Reusable table with pagination
│   │   ├── page-header.tsx                  ← Page title + description + action buttons
│   │   └── empty-state.tsx                  ← Empty state with icon + message + action
│   ├── App.tsx                              ← MODIFY: wrap routes in AppShell
│   └── lib/
│       └── utils.ts                         ← MODIFY: ensure cn() helper exists
```

### Files modified:

- `frontend/src/globals.css` — Replace Tailwind defaults + custom classes with shadcn/ui CSS variables mapped to civic design tokens
- `frontend/src/App.tsx` — Replace top nav with `<AppShell>` wrapper, keep all existing routes
- `frontend/src/lib/utils.ts` — Ensure `cn()` utility exists (may already be there)
- `frontend/tailwind.config.js` — Extend with shadcn/ui theme config
- `frontend/tsconfig.json` — Ensure `baseUrl` is set (required by shadcn)

---

## Task 1: Install shadcn/ui and Configure

**Files:**
- Create: `frontend/components.json`
- Modify: `frontend/tsconfig.json`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/globals.css`
- Modify: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Add baseUrl to tsconfig.json**

shadcn/ui CLI requires `baseUrl` in tsconfig. Open `frontend/tsconfig.json` and add `"baseUrl": "."` to `compilerOptions`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "target": "ES2020",
    ...
  }
}
```

- [ ] **Step 2: Initialize shadcn/ui**

```bash
cd frontend
npx shadcn@latest init -d
```

This creates `components.json` and updates `globals.css` with CSS variable scaffold. Select these options if prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

If it runs non-interactively (`-d` flag), it picks defaults. We'll override the CSS variables in the next step anyway.

- [ ] **Step 3: Verify components.json was created**

Check that `frontend/components.json` exists and has the correct aliases:

```bash
cat frontend/components.json
```

Expected: JSON with `"aliases"` pointing to `"@/components"`, `"@/lib/utils"`, etc. If paths don't match our structure, edit to:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

- [ ] **Step 4: Replace globals.css with civic design tokens**

Replace the entire contents of `frontend/src/globals.css` with our design token system. This maps the UX Style Guide tokens (#1F5A84 primary, #1F2933 text, etc.) into shadcn/ui CSS variables:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Brand */
    --background: 0 0% 100%;
    --foreground: 210 18% 16%;

    /* Card & Popover */
    --card: 207 33% 97%;
    --card-foreground: 210 18% 16%;
    --popover: 0 0% 100%;
    --popover-foreground: 210 18% 16%;

    /* Primary — Civic Blue #1F5A84 */
    --primary: 207 62% 32%;
    --primary-foreground: 0 0% 100%;

    /* Secondary */
    --secondary: 207 33% 97%;
    --secondary-foreground: 207 62% 32%;

    /* Muted */
    --muted: 207 33% 97%;
    --muted-foreground: 207 12% 40%;

    /* Accent */
    --accent: 207 33% 97%;
    --accent-foreground: 207 62% 32%;

    /* Destructive — #8B2E2E */
    --destructive: 0 50% 36%;
    --destructive-foreground: 0 0% 100%;

    /* Status colors (custom, not shadcn defaults) */
    --success: 153 43% 30%;
    --success-foreground: 0 0% 100%;
    --success-light: 153 43% 93%;
    --warning: 37 85% 29%;
    --warning-foreground: 0 0% 100%;
    --warning-light: 37 85% 94%;
    --danger: 0 50% 36%;
    --danger-light: 0 50% 95%;
    --info: 207 62% 32%;
    --info-light: 207 62% 95%;

    /* Borders & Inputs */
    --border: 207 20% 82%;
    --input: 207 20% 82%;
    --ring: 207 62% 32%;

    /* Radius */
    --radius: 0.5rem;

    /* Sidebar — matches spec layout section */
    --sidebar-width: 240px;
    --header-height: 56px;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      "Helvetica Neue", Arial, sans-serif;
  }

  h1, h2, h3, h4, h5, h6 {
    @apply tracking-tight;
  }
}

@layer components {
  /* Status badge utilities — used by StatusBadge component */
  .badge-success {
    background-color: hsl(var(--success-light));
    color: hsl(var(--success));
  }
  .badge-warning {
    background-color: hsl(var(--warning-light));
    color: hsl(var(--warning));
  }
  .badge-danger {
    background-color: hsl(var(--danger-light));
    color: hsl(var(--danger));
  }
  .badge-info {
    background-color: hsl(var(--info-light));
    color: hsl(var(--info));
  }
  .badge-neutral {
    @apply bg-gray-100 text-gray-600;
  }

  /* Spinner animation */
  .spinner {
    @apply animate-spin rounded-full border-2 border-current border-t-transparent;
  }
}
```

- [ ] **Step 5: Update tailwind.config.js for shadcn/ui**

Replace `frontend/tailwind.config.js` with:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
          light: "hsl(var(--success-light))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
          light: "hsl(var(--warning-light))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
      fontSize: {
        "page-title": ["2.25rem", { lineHeight: "1.2", fontWeight: "700" }],
        "section-head": ["1.75rem", { lineHeight: "1.3", fontWeight: "600" }],
        "subsection": ["1.375rem", { lineHeight: "1.35", fontWeight: "600" }],
        "label": ["0.8125rem", { lineHeight: "1.4", fontWeight: "500", letterSpacing: "0.05em" }],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
```

- [ ] **Step 6: Install tailwindcss-animate**

```bash
cd frontend && npm install tailwindcss-animate
```

- [ ] **Step 7: Ensure cn() utility exists in utils.ts**

Check `frontend/src/lib/utils.ts`. It should export:

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

The project already has `clsx` and `tailwind-merge` installed. If `utils.ts` already has this, no change needed.

- [ ] **Step 8: Build to verify no breakage**

```bash
cd frontend && npm run build
```

Expected: Build succeeds. Existing pages may have visual differences (CSS variable changes) but should render without errors.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: install shadcn/ui and map civic design tokens

- Initialize shadcn/ui with components.json
- Replace globals.css with UX Style Guide design tokens (#1F5A84 civic blue)
- Update tailwind.config.js with shadcn/ui theme extensions
- Add status color variables (success/warning/danger/info)
- Add tailwindcss-animate dependency"
```

---

## Task 2: Install shadcn/ui Primitive Components

**Files:**
- Create: `frontend/src/components/ui/button.tsx` (auto-generated)
- Create: `frontend/src/components/ui/badge.tsx` (auto-generated)
- Create: `frontend/src/components/ui/card.tsx` (auto-generated)
- Create: `frontend/src/components/ui/table.tsx` (auto-generated)
- Create: `frontend/src/components/ui/input.tsx` (auto-generated)
- Create: `frontend/src/components/ui/select.tsx` (auto-generated)
- Create: `frontend/src/components/ui/separator.tsx` (auto-generated)
- Create: `frontend/src/components/ui/tooltip.tsx` (auto-generated)
- Create: `frontend/src/components/ui/dialog.tsx` (auto-generated)
- Create: `frontend/src/components/ui/tabs.tsx` (auto-generated)
- Create: `frontend/src/components/ui/skeleton.tsx` (auto-generated)
- Create: `frontend/src/components/ui/dropdown-menu.tsx` (auto-generated)

- [ ] **Step 1: Install shadcn/ui components via CLI**

```bash
cd frontend
npx shadcn@latest add button badge card table input select separator tooltip dialog tabs skeleton dropdown-menu -y
```

The `-y` flag auto-accepts prompts. This creates files in `src/components/ui/` and installs any missing Radix dependencies.

- [ ] **Step 2: Verify components were created**

```bash
ls frontend/src/components/ui/
```

Expected: All 12 component files listed above.

- [ ] **Step 3: Build to verify no breakage**

```bash
cd frontend && npm run build
```

Expected: Clean build. Components are installed but not yet imported anywhere.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add shadcn/ui primitive components

- button, badge, card, table, input, select, separator
- tooltip, dialog, tabs, skeleton, dropdown-menu
- All Radix dependencies auto-installed"
```

---

## Task 3: Create StatusBadge Component

**Files:**
- Create: `frontend/src/components/status-badge.tsx`

This component maps request/document/exemption statuses to the color+icon system defined in the unified spec (Section 6, Status Badge Color Mapping).

- [ ] **Step 1: Create the StatusBadge component**

Create `frontend/src/components/status-badge.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import {
  Inbox,
  MessageCircle,
  UserCheck,
  Search,
  Eye,
  CheckCircle,
  FileText,
  ShieldCheck,
  Send,
  Archive,
  AlertTriangle,
  XCircle,
  Clock,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type StatusVariant = "info" | "warning" | "success" | "danger" | "neutral";

interface StatusConfig {
  label: string;
  variant: StatusVariant;
  icon: LucideIcon;
}

const REQUEST_STATUS_MAP: Record<string, StatusConfig> = {
  received: { label: "Received", variant: "info", icon: Inbox },
  clarification_needed: { label: "Clarification Needed", variant: "warning", icon: MessageCircle },
  assigned: { label: "Assigned", variant: "info", icon: UserCheck },
  searching: { label: "Searching", variant: "info", icon: Search },
  in_review: { label: "In Review", variant: "warning", icon: Eye },
  ready_for_release: { label: "Ready for Release", variant: "success", icon: CheckCircle },
  drafted: { label: "Drafted", variant: "info", icon: FileText },
  approved: { label: "Approved", variant: "success", icon: ShieldCheck },
  fulfilled: { label: "Fulfilled", variant: "success", icon: Send },
  sent: { label: "Fulfilled", variant: "success", icon: Send },
  closed: { label: "Closed", variant: "neutral", icon: Archive },
};

const DOCUMENT_STATUS_MAP: Record<string, StatusConfig> = {
  pending: { label: "Pending", variant: "warning", icon: Clock },
  completed: { label: "Completed", variant: "success", icon: CheckCircle },
  failed: { label: "Failed", variant: "danger", icon: XCircle },
  processing: { label: "Processing", variant: "info", icon: Clock },
};

const EXEMPTION_STATUS_MAP: Record<string, StatusConfig> = {
  flagged: { label: "Flagged", variant: "warning", icon: AlertTriangle },
  reviewed: { label: "Reviewed", variant: "info", icon: Eye },
  accepted: { label: "Accepted", variant: "success", icon: CheckCircle },
  rejected: { label: "Rejected", variant: "neutral", icon: XCircle },
};

const VARIANT_CLASSES: Record<StatusVariant, string> = {
  info: "badge-info",
  warning: "badge-warning",
  success: "badge-success",
  danger: "badge-danger",
  neutral: "badge-neutral",
};

type StatusDomain = "request" | "document" | "exemption";

interface StatusBadgeProps {
  status: string;
  domain?: StatusDomain;
  className?: string;
}

function getStatusConfig(status: string, domain: StatusDomain): StatusConfig {
  const maps: Record<StatusDomain, Record<string, StatusConfig>> = {
    request: REQUEST_STATUS_MAP,
    document: DOCUMENT_STATUS_MAP,
    exemption: EXEMPTION_STATUS_MAP,
  };
  return maps[domain][status] ?? {
    label: status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    variant: "neutral" as StatusVariant,
    icon: Clock,
  };
}

export function StatusBadge({ status, domain = "request", className }: StatusBadgeProps) {
  const config = getStatusConfig(status, domain);
  const Icon = config.icon;

  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 border-0 font-medium",
        VARIANT_CLASSES[config.variant],
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

Expected: Clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/status-badge.tsx
git commit -m "feat: add StatusBadge component with icon+color status mapping

- Maps request statuses (received through closed) to info/warning/success/danger/neutral
- Maps document statuses (pending/completed/failed/processing)
- Maps exemption statuses (flagged/reviewed/accepted/rejected)
- Every badge includes icon for colorblind accessibility (WCAG)"
```

---

## Task 4: Create StatCard Component

**Files:**
- Create: `frontend/src/components/stat-card.tsx`

Stat cards are used on Dashboard, Requests, Exemptions, Ingestion. Label + large number + optional trend indicator.

- [ ] **Step 1: Create the StatCard component**

Create `frontend/src/components/stat-card.tsx`:

```tsx
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  variant?: "default" | "success" | "warning" | "danger";
  className?: string;
}

const VARIANT_STYLES = {
  default: "text-foreground",
  success: "text-success",
  warning: "text-warning",
  danger: "text-destructive",
};

export function StatCard({ label, value, icon: Icon, variant = "default", className }: StatCardProps) {
  return (
    <Card className={cn("shadow-none", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-label uppercase text-muted-foreground">{label}</p>
            <p className={cn("text-page-title mt-1", VARIANT_STYLES[variant])}>
              {value}
            </p>
          </div>
          {Icon && (
            <div className="rounded-lg bg-muted p-3">
              <Icon className="h-5 w-5 text-muted-foreground" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/stat-card.tsx
git commit -m "feat: add StatCard component for metric display

- Label (uppercase, muted) + large value with variant coloring
- Optional icon with muted background
- Variants: default, success, warning, danger"
```

---

## Task 5: Create PageHeader Component

**Files:**
- Create: `frontend/src/components/page-header.tsx`

- [ ] **Step 1: Create the PageHeader component**

Create `frontend/src/components/page-header.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between mb-8", className)}>
      <div>
        <h1 className="text-page-title text-foreground">{title}</h1>
        {description && (
          <p className="mt-1 text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/page-header.tsx
git commit -m "feat: add PageHeader component with title, description, and action slot"
```

---

## Task 6: Create EmptyState Component

**Files:**
- Create: `frontend/src/components/empty-state.tsx`

- [ ] **Step 1: Create the EmptyState component**

Create `frontend/src/components/empty-state.tsx`:

```tsx
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 text-center", className)}>
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-subsection text-foreground mb-2">{title}</h3>
      <p className="text-muted-foreground max-w-md mb-6">{description}</p>
      {action}
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/empty-state.tsx
git commit -m "feat: add EmptyState component with icon, title, description, and action slot"
```

---

## Task 7: Create DataTable Component

**Files:**
- Create: `frontend/src/components/data-table.tsx`

Reusable table with header, rows, and optional pagination. Built on shadcn Table primitive.

- [ ] **Step 1: Create the DataTable component**

Create `frontend/src/components/data-table.tsx`:

```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
  ariaLabel?: string;
  className?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  loading,
  emptyMessage = "No data to display.",
  rowKey,
  onRowClick,
  pagination,
  ariaLabel,
  className,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  const totalPages = pagination
    ? Math.ceil(pagination.total / pagination.pageSize)
    : 1;

  return (
    <div className={className}>
      <Table aria-label={ariaLabel}>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col.key} className={col.className}>
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="text-center py-8 text-muted-foreground"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            data.map((row) => (
              <TableRow
                key={rowKey(row)}
                className={cn(onRowClick && "cursor-pointer hover:bg-muted/50")}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <TableCell key={col.key} className={col.className}>
                    {col.render
                      ? col.render(row)
                      : String(row[col.key] ?? "")}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {pagination && totalPages > 1 && (
        <div className="flex items-center justify-between border-t pt-4 mt-4">
          <p className="text-sm text-muted-foreground">
            Page {pagination.page} of {totalPages} ({pagination.total} total)
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page <= 1}
              onClick={() => pagination.onPageChange(pagination.page - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page >= totalPages}
              onClick={() => pagination.onPageChange(pagination.page + 1)}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/data-table.tsx
git commit -m "feat: add DataTable component with pagination and loading states

- Generic typed columns with custom render functions
- Loading skeleton, empty state, pagination controls
- Optional row click handler
- Accessible with aria-label support"
```

---

## Task 8: Create Sidebar Navigation

**Files:**
- Create: `frontend/src/components/sidebar-nav.tsx`

- [ ] **Step 1: Create the SidebarNav component**

Create `frontend/src/components/sidebar-nav.tsx`:

```tsx
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import {
  Search,
  FileText,
  Shield,
  FolderOpen,
  HardDrive,
  LayoutDashboard,
  Users,
  type LucideIcon,
} from "lucide-react";

interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

const WORKFLOW_ITEMS: NavItem[] = [
  { path: "/search", label: "Search", icon: Search },
  { path: "/requests", label: "Requests", icon: FileText },
  { path: "/exemptions", label: "Exemptions", icon: Shield },
];

const ADMIN_ITEMS: NavItem[] = [
  { path: "/sources", label: "Sources", icon: FolderOpen },
  { path: "/ingestion", label: "Ingestion", icon: HardDrive },
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/users", label: "Users", icon: Users },
];

function NavLink({ item }: { item: NavItem }) {
  const location = useLocation();
  const isActive =
    item.path === "/"
      ? location.pathname === "/"
      : location.pathname.startsWith(item.path);

  return (
    <Link
      to={item.path}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
        "min-h-[44px]",
        isActive
          ? "bg-primary/10 text-primary border-l-2 border-primary -ml-px"
          : "text-muted-foreground hover:text-foreground hover:bg-muted"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <item.icon className="h-4 w-4 shrink-0" />
      {item.label}
    </Link>
  );
}

export function SidebarNav() {
  return (
    <nav
      className="flex flex-col gap-1 px-3 py-4"
      role="navigation"
      aria-label="Main navigation"
    >
      <p className="px-3 mb-1 text-label uppercase text-muted-foreground">
        Workflow
      </p>
      {WORKFLOW_ITEMS.map((item) => (
        <NavLink key={item.path} item={item} />
      ))}

      <Separator className="my-3" />

      <p className="px-3 mb-1 text-label uppercase text-muted-foreground">
        Administration
      </p>
      {ADMIN_ITEMS.map((item) => (
        <NavLink key={item.path} item={item} />
      ))}
    </nav>
  );
}
```

- [ ] **Step 2: Build to verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/sidebar-nav.tsx
git commit -m "feat: add SidebarNav with grouped navigation and 44px touch targets

- Workflow group: Search, Requests, Exemptions
- Administration group: Sources, Ingestion, Dashboard, Users
- Active page highlighted with left border accent
- All links meet 44px minimum touch target (WCAG 2.5.5)"
```

---

## Task 9: Create AppShell Layout

**Files:**
- Create: `frontend/src/components/app-shell.tsx`
- Modify: `frontend/src/App.tsx`

The AppShell wraps all authenticated pages with sidebar + header + scrollable content area. This replaces the current top nav bar.

- [ ] **Step 1: Create the AppShell component**

Create `frontend/src/components/app-shell.tsx`:

```tsx
import { SidebarNav } from "@/components/sidebar-nav";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { LogOut, HelpCircle } from "lucide-react";

interface AppShellProps {
  children: React.ReactNode;
  onSignOut: () => void;
  userEmail?: string;
}

export function AppShell({ children, onSignOut, userEmail }: AppShellProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className="flex flex-col border-r bg-card"
        style={{ width: "var(--sidebar-width)" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-6" style={{ height: "var(--header-height)" }}>
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-sm font-bold text-primary-foreground">CR</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground leading-tight">CivicRecords</p>
            <p className="text-xs text-muted-foreground leading-tight">AI</p>
          </div>
        </div>

        <Separator />

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto">
          <SidebarNav />
        </div>

        {/* Footer */}
        <div className="border-t p-4">
          <p className="text-xs text-muted-foreground truncate mb-2">{userEmail}</p>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground"
            onClick={onSignOut}
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header
          className="flex items-center justify-end gap-3 border-b px-6 bg-background"
          style={{ height: "var(--header-height)" }}
        >
          <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground">
            <HelpCircle className="h-4 w-4" />
            Help
          </Button>
        </header>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto p-6" role="main">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t px-6 py-2 text-xs text-muted-foreground flex items-center justify-between">
          <span>CivicRecords AI v0.1.0 &middot; Apache 2.0</span>
          <span>Help &middot; Audit Log</span>
        </footer>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update App.tsx to use AppShell**

Replace the current `App.tsx` content. The key change: remove the top `<nav>` and wrap the `<Routes>` in `<AppShell>`:

```tsx
import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { isTokenValid } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Search from "@/pages/Search";
import Requests from "@/pages/Requests";
import RequestDetail from "@/pages/RequestDetail";
import Exemptions from "@/pages/Exemptions";
import DataSources from "@/pages/DataSources";
import Ingestion from "@/pages/Ingestion";
import Users from "@/pages/Users";

export default function App() {
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem("token");
    return stored && isTokenValid(stored) ? stored : null;
  });

  const handleLogin = useCallback((newToken: string) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
  }, []);

  const handleSignOut = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  // Periodic token validation
  useEffect(() => {
    const interval = setInterval(() => {
      const stored = localStorage.getItem("token");
      if (stored && !isTokenValid(stored)) {
        handleSignOut();
      }
    }, 60000);
    return () => clearInterval(interval);
  }, [handleSignOut]);

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  // Decode email from JWT for display
  let userEmail = "";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    userEmail = payload.email || payload.sub || "";
  } catch {
    userEmail = "";
  }

  return (
    <AppShell onSignOut={handleSignOut} userEmail={userEmail}>
      <Routes>
        <Route path="/" element={<Dashboard token={token} />} />
        <Route path="/search" element={<Search token={token} />} />
        <Route path="/requests" element={<Requests token={token} />} />
        <Route path="/requests/:id" element={<RequestDetail token={token} />} />
        <Route path="/exemptions" element={<Exemptions token={token} />} />
        <Route path="/sources" element={<DataSources token={token} />} />
        <Route path="/ingestion" element={<Ingestion token={token} />} />
        <Route path="/users" element={<Users token={token} />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AppShell>
  );
}
```

- [ ] **Step 3: Build to verify**

```bash
cd frontend && npm run build
```

Expected: Clean build. The app now has a sidebar layout. Existing page components render inside the content area. They'll still use old Tailwind classes but the shell is new.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: replace top nav with sidebar AppShell layout

- New AppShell component: 240px sidebar + 56px header + scrollable content
- SidebarNav with grouped Workflow/Administration sections
- Logo wordmark, user email display, sign out button in sidebar footer
- All existing pages and routes preserved
- Matches layout spec from UNIFIED-SPEC.md section 7.1"
```

---

## Task 10: Visual Verification

**Files:** None (verification only)

- [ ] **Step 1: Rebuild the frontend Docker container**

```bash
cd /path/to/civicrecords-ai
docker compose build frontend
docker compose up -d frontend
```

- [ ] **Step 2: Open the app in browser**

Navigate to `http://localhost:8080`. Verify:
- Sidebar appears on the left (240px wide)
- Logo shows "CR" badge + "CivicRecords AI" text
- Navigation is grouped: Workflow (Search, Requests, Exemptions) and Administration (Sources, Ingestion, Dashboard, Users)
- Active page is highlighted with left blue border
- Content area scrolls independently
- Sign out button is in sidebar footer
- All 8 pages still render and display data

- [ ] **Step 3: Spot-check accessibility**

- Tab through nav links — verify visible focus ring
- Check that all nav links have 44px+ height
- Verify sidebar has `role="navigation"` and `aria-label`

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: visual adjustments after Phase 0 verification"
```

---

## Summary

After Phase 0 is complete, the frontend has:

1. **shadcn/ui installed** with 12 primitive components
2. **Design tokens mapped** to CSS variables (civic blue #1F5A84, status colors, typography scale)
3. **Sidebar layout shell** replacing the top nav bar
4. **5 domain components** ready for page redesigns:
   - `StatusBadge` — status display with icon + color
   - `StatCard` — metric cards with label + value
   - `PageHeader` — page title + description + action buttons
   - `EmptyState` — empty state with icon + message + action
   - `DataTable` — table with pagination and loading states

Phase 1 (Staff Workbench Redesign) can now proceed page-by-page, replacing raw Tailwind with these components. Each page can be redesigned independently without touching infrastructure.
