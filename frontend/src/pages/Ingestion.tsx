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

interface Document extends Record<string, unknown> {
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

  const columns: Column<Document & Record<string, unknown>>[] = [
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
            data={docs}
            rowKey={(d) => d.id}
            ariaLabel="Ingested documents"
          />
        </div>
      )}
    </div>
  );
}
