import { useState, useEffect, type FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export default function Settings({
  token,
  forcePasswordRotation = false,
  onPasswordRotated,
}: {
  token: string;
  forcePasswordRotation?: boolean;
  onPasswordRotated?: () => void;
}) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rotationError, setRotationError] = useState("");
  const [rotationMessage, setRotationMessage] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  useEffect(() => {
    if (forcePasswordRotation) {
      setLoading(false);
      return;
    }

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
  }, [forcePasswordRotation, token]);

  async function handlePasswordRotation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setRotationError("");
    setRotationMessage("");

    if (password.length < 12) {
      setRotationError("Enter a new administrator password with at least 12 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setRotationError("The two password fields do not match. Re-enter the same new password in both fields.");
      return;
    }

    setSavingPassword(true);
    try {
      await apiFetch("/users/me", {
        token,
        method: "PATCH",
        body: JSON.stringify({ password }),
      });
      setPassword("");
      setConfirmPassword("");
      setRotationMessage("Password changed. Staff tools are now unlocked for this administrator.");
      onPasswordRotated?.();
    } catch (e) {
      setRotationError(
        e instanceof Error
          ? e.message
          : "Password change failed. Try again or ask your IT contact to confirm the system is reachable."
      );
    } finally {
      setSavingPassword(false);
    }
  }

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

  if (forcePasswordRotation) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Change Initial Password"
          description="Staff tools stay locked until the initial administrator password is changed."
        />

        <Card className="shadow-none max-w-xl">
          <CardHeader>
            <CardTitle className="text-lg">First Login Required</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handlePasswordRotation}>
              <p className="text-sm text-muted-foreground">
                Choose a new administrator password. This protects the generated setup password from being reused.
              </p>

              <div className="space-y-2">
                <label htmlFor="new-password" className="text-sm font-medium">
                  New password
                </label>
                <Input
                  id="new-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                  minLength={12}
                  required
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="confirm-password" className="text-sm font-medium">
                  Confirm new password
                </label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  autoComplete="new-password"
                  minLength={12}
                  required
                />
              </div>

              {rotationError && (
                <p className="text-sm text-destructive" role="alert">
                  {rotationError}
                </p>
              )}
              {rotationMessage && (
                <p className="text-sm text-success" role="status">
                  {rotationMessage}
                </p>
              )}

              <Button type="submit" disabled={savingPassword}>
                {savingPassword ? "Changing password..." : "Change password"}
              </Button>
            </form>
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
