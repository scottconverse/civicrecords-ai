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
import { Plus, FileText, AlertTriangle, Clock } from "lucide-react";

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

  const columns: Column<Request & Record<string, unknown>>[] = [
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
            <DialogTrigger render={<Button />}>
              <Plus className="h-4 w-4 mr-2" />
              New Request
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
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? "all")}>
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
        <DataTable<Request & Record<string, unknown>>
          columns={columns}
          data={filtered as (Request & Record<string, unknown>)[]}
          rowKey={(r) => r.id}
          onRowClick={(r) => navigate(`/requests/${r.id}`)}
          ariaLabel="Records requests"
          emptyMessage="No requests found."
        />
      )}
    </div>
  );
}
