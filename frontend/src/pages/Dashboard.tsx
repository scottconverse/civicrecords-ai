import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  FileText,
  Shield,
  Search,
  Plus,
  Database,
  Cpu,
  Zap,
  CheckCircle,
  XCircle,
} from "lucide-react";

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
            <Button onClick={() => window.location.href = "/requests"}>
              <Plus className="h-4 w-4 mr-2" />
              New Request
            </Button>
            <Button variant="outline" onClick={() => window.location.href = "/search"}>
              <Search className="h-4 w-4 mr-2" />
              Search Records
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
