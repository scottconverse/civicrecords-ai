
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
