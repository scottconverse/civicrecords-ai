import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { components } from "@/generated/api";
import {
  Database,
  Cpu,
  Zap,
  CheckCircle,
  XCircle,
  Server,
  type LucideIcon,
} from "lucide-react";

interface HealthResponse {
  status: string;
  version: string;
}

// Backend /admin/status returns exactly the fields declared by
// components["schemas"]["SystemStatus"]: version, database, ollama, redis,
// user_count, audit_log_count. No SMTP, audit-retention, LLM-model, or
// data-sovereignty fields exist on that endpoint today — this page MUST
// not invent them. If those surfaces are wanted on Settings, extend the
// backend contract first; rendering guessed values on an admin truth
// surface is misleading to operators.
type SystemStatus = components["schemas"]["SystemStatus"];

function isServiceHealthy(status: string | undefined): boolean {
  return status === "connected" || status === "ok" || status === "healthy";
}

function StatusRow({
  label,
  icon: Icon,
  status,
  detail,
}: {
  label: string;
  icon: LucideIcon;
  status: "ok" | "error" | "info";
  detail: string;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2 text-sm">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-foreground font-medium">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">{detail}</span>
        {status === "ok" && <CheckCircle className="h-4 w-4 text-success" />}
        {status === "error" && <XCircle className="h-4 w-4 text-destructive" />}
      </div>
    </div>
  );
}

export default function Settings({ token }: { token: string }) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiFetch<HealthResponse>("/health", { token }),
      apiFetch<SystemStatus>("/admin/status", { token }),
    ])
      .then(([h, s]) => {
        setHealth(h);
        setStatus(s);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40" />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Settings" />
        <Card className="border-destructive">
          <CardContent className="p-6">
            <p className="text-destructive">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!health || !status) return null;

  const dbOk = isServiceHealthy(status.database);
  const ollamaOk = isServiceHealthy(status.ollama);
  const redisOk = isServiceHealthy(status.redis);

  return (
    <div className="space-y-8">
      <PageHeader
        title="Settings"
        description="System configuration and status overview"
      />

      {/* System Info — the ONLY card on this page. Every row is backed by a
          real field on /health or /admin/status. Do not add rows whose values
          are derived from fields the backend does not return. */}
      <Card className="shadow-none max-w-2xl">
        <CardHeader className="pb-3">
          <CardTitle className="text-label uppercase text-muted-foreground">
            System Info
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          <StatusRow
            label="Version"
            icon={Server}
            status="info"
            detail={`v${health.version}`}
          />
          <StatusRow
            label="Database (PostgreSQL)"
            icon={Database}
            status={dbOk ? "ok" : "error"}
            detail={status.database ?? "unknown"}
          />
          <StatusRow
            label="Ollama (LLM Engine)"
            icon={Cpu}
            status={ollamaOk ? "ok" : "error"}
            detail={status.ollama ?? "unknown"}
          />
          <StatusRow
            label="Redis (Task Queue)"
            icon={Zap}
            status={redisOk ? "ok" : "error"}
            detail={status.redis ?? "unknown"}
          />
        </CardContent>
      </Card>
    </div>
  );
}
