import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";
import { useEffect, useState } from "react";

interface AuditDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface AuditEntry {
  id: number;
  action: string;
  resource_type: string;
  timestamp: string;
  resource_id?: string | null;
}

export function AuditDrawer({ open, onOpenChange }: AuditDrawerProps) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "loaded" | "empty" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setStatus("loading");
    setMessage("");
    const token = localStorage.getItem("token") || undefined;
    apiFetch<AuditEntry[]>("/audit/logs?limit=20", { token })
      .then((data) => {
        if (cancelled) return;
        setEntries(data);
        setStatus(data.length ? "loaded" : "empty");
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setEntries([]);
        setMessage(error.message);
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-label="Audit drawer"
        className="right-0 left-auto top-0 h-screen max-w-md translate-x-0 translate-y-0 rounded-none border-l sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle>Audit drawer</DialogTitle>
          <DialogDescription>
            Recent operator actions and compliance events from Records AI are listed here.
          </DialogDescription>
        </DialogHeader>
        {status === "loading" && (
          <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
            Loading recent audit events.
          </div>
        )}
        {status === "empty" && (
          <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
            No audit events yet. Use Records AI normally; sign-ins, searches, and record actions will appear here.
          </div>
        )}
        {status === "error" && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
            Audit events could not be loaded. {message || "Return to the suite launcher, sign in again, then reopen the drawer."}
          </div>
        )}
        {status === "loaded" && (
          <ul className="grid max-h-[70vh] gap-2 overflow-y-auto pr-1">
            {entries.map((entry) => (
              <li key={entry.id} className="rounded-md border bg-card p-3 text-sm">
                <p className="font-medium text-foreground">{entry.action}</p>
                <p className="text-muted-foreground">
                  {entry.resource_type}
                  {entry.resource_id ? ` · ${entry.resource_id}` : ""}
                </p>
                <p className="font-mono text-xs text-muted-foreground">
                  {new Date(entry.timestamp).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        )}
        <a className="text-sm font-medium text-primary underline-offset-4 hover:underline" href="/audit-log">
          View full audit log
        </a>
      </DialogContent>
    </Dialog>
  );
}
