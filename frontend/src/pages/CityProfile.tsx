import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import {
  Building2,
  Mail,
  Users,
  Monitor,
  FileText,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Shield,
} from "lucide-react";

interface CityProfileRead {
  id: string;
  city_name: string;
  state: string;
  county: string | null;
  population_band: string | null;
  email_platform: string | null;
  has_dedicated_it: boolean | null;
  monthly_request_volume: string | null;
  onboarding_status: string;
  profile_data: Record<string, unknown> | null;
  gap_map: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// Local shape used for rendering
interface CityProfile {
  cityName: string;
  state: string;
  county: string;
  populationBand: string;
  emailPlatform: string;
  hasDedicatedIT: string;
  monthlyRequestVolume: string;
  systems: Record<string, { vendor: string; notes: string }>;
}

function mapApiProfile(api: CityProfileRead): CityProfile {
  const systems = (api.gap_map as Record<string, { vendor: string; notes: string }>) ?? {};
  return {
    cityName: api.city_name,
    state: api.state,
    county: api.county ?? "",
    populationBand: api.population_band ?? "",
    emailPlatform: api.email_platform ?? "",
    hasDedicatedIT: api.has_dedicated_it === true ? "yes" : api.has_dedicated_it === false ? "no" : "",
    monthlyRequestVolume: api.monthly_request_volume ?? "",
    systems,
  };
}

const DOMAIN_LABELS: Record<string, string> = {
  finance: "Finance & Budgeting",
  public_safety: "Public Safety",
  permitting: "Land Use & Permitting",
  hr: "Human Resources",
  document_mgmt: "Document Management",
  utilities: "Utilities & Public Works",
  courts: "Courts & Legal",
  parks: "Parks & Recreation",
};

const CJIS_DOMAINS = ["public_safety"];

const EMAIL_LABELS: Record<string, string> = {
  microsoft365: "Microsoft 365",
  google: "Google Workspace",
  exchange: "On-premise Exchange",
  other: "Other",
};

export default function CityProfile({ token }: { token: string }) {
  const [profile, setProfile] = useState<CityProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch<CityProfileRead | null>("/city-profile", { token })
      .then((data) => {
        if (!cancelled) {
          setProfile(data ? mapApiProfile(data) : null);
        }
      })
      .catch(() => {
        if (!cancelled) setProfile(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [token]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="City Profile" />
        <Card className="shadow-none">
          <CardContent className="pt-6 space-y-4">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-2/5" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="space-y-6">
        <PageHeader title="City Profile" />
        <EmptyState
          icon={Building2}
          title="No city profile configured"
          description="Run the onboarding interview to set up your city profile, identify your data systems, and see your coverage gap map."
          action={
            <Button onClick={() => navigate("/onboarding")}>
              Start Onboarding Interview
            </Button>
          }
        />
      </div>
    );
  }

  const identifiedSystems = Object.entries(profile.systems).filter(([, v]) => v.vendor);
  const allDomains = Object.keys(DOMAIN_LABELS);
  const gapDomains = allDomains.filter((d) => !profile.systems[d]?.vendor);

  return (
    <div className="space-y-6">
      <PageHeader
        title="City Profile"
        actions={
          <Button variant="outline" onClick={() => navigate("/onboarding")}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Re-run Onboarding
          </Button>
        }
      />

      {/* City details */}
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">City Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">City</p>
                <p className="font-medium">{profile.cityName || "Not set"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">State</p>
                <p className="font-medium">{profile.state}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Population</p>
                <p className="font-medium">{profile.populationBand || "Not set"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Email Platform</p>
                <p className="font-medium">{EMAIL_LABELS[profile.emailPlatform] || "Not set"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Monitor className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">IT Staffing</p>
                <p className="font-medium">{profile.hasDedicatedIT === "yes" ? "Dedicated IT" : profile.hasDedicatedIT === "no" ? "Shared role" : "Not set"}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-muted-foreground">Monthly Requests</p>
                <p className="font-medium">{profile.monthlyRequestVolume || "Not set"}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connected Systems */}
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">Connected Systems ({identifiedSystems.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {identifiedSystems.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No systems identified yet.</p>
          ) : (
            <div className="space-y-2">
              {identifiedSystems.map(([key, val]) => (
                <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <div>
                      <p className="text-sm font-medium">{DOMAIN_LABELS[key]}</p>
                      {val.notes && <p className="text-xs text-muted-foreground">{val.notes}</p>}
                    </div>
                  </div>
                  <Badge variant="outline">{val.vendor}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Gap Map */}
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle className="text-lg">
            Gap Map
            {gapDomains.length > 0 && (
              <Badge variant="outline" className="ml-2 badge-warning text-xs border-0">
                {gapDomains.length} gap{gapDomains.length !== 1 ? "s" : ""}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {gapDomains.length === 0 ? (
            <div className="flex items-center gap-2 text-success py-2">
              <CheckCircle className="h-5 w-5" />
              <p className="font-medium">All functional domains covered.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {gapDomains.map((key) => (
                <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-4 w-4 text-warning" />
                    <div>
                      <p className="text-sm font-medium">{DOMAIN_LABELS[key]}</p>
                      <p className="text-xs text-muted-foreground">No source identified</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {CJIS_DOMAINS.includes(key) && (
                      <Badge variant="outline" className="text-xs badge-danger border-0">
                        <Shield className="h-3 w-3 mr-1" />
                        CJIS required
                      </Badge>
                    )}
                    <Button variant="outline" size="sm" onClick={() => navigate("/sources")}>
                      Connect
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
