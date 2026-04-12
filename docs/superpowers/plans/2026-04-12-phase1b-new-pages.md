# Phase 1B: New Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 new pages (Onboarding Interview, City Profile, Discovery Dashboard) as functional UI shells with local state and mock data. Backend APIs will be wired up in Phase 2.

**Architecture:** Each page uses the Phase 0 design system components. Since backend APIs don't exist yet, pages store state in localStorage (onboarding) or show static mock data (city profile, discovery). The onboarding wizard uses a multi-step form pattern — not an actual LLM conversation yet. Routes and sidebar nav are updated to include the new pages.

**Tech Stack:** React 18, shadcn/ui, Tailwind CSS with civic tokens, Lucide React icons, TypeScript strict mode.

**Compatibility notes from Phase 1A:**
- Button does NOT support `asChild` — use `onClick` with `useNavigate()`
- `Select.onValueChange` receives `string | null` — wrap with `(v) => setX(v ?? default)`
- DialogTrigger: use `render` prop, not `asChild`

---

## Task 1: Onboarding Interview Page

**Files:**
- Create: `frontend/src/pages/Onboarding.tsx`

This is a multi-step wizard with 3 phases. Since the LLM onboarding service doesn't exist yet, it uses a structured form that collects the same data the LLM interview would. Data is saved to localStorage for now (Phase 2 will persist to `city_profile` table via API).

- [ ] **Step 1: Create Onboarding.tsx**

Create `frontend/src/pages/Onboarding.tsx`:

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Building2,
  Mail,
  Users,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  AlertTriangle,
  MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

const STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY",
];

const POPULATION_BANDS = [
  "Under 5,000",
  "5,000 - 25,000",
  "25,000 - 100,000",
  "100,000 - 500,000",
  "Over 500,000",
];

const DOMAINS = [
  { key: "finance", label: "Finance & Budgeting", hint: "Tyler Munis, Caselle, OpenGov, SAP" },
  { key: "public_safety", label: "Public Safety", hint: "Mark43, Spillman, Axon, Tyler New World" },
  { key: "permitting", label: "Land Use & Permitting", hint: "Accela, CityWorks, EnerGov" },
  { key: "hr", label: "Human Resources", hint: "NEOGOV, Workday, ADP, Paylocity" },
  { key: "document_mgmt", label: "Document Management", hint: "Laserfiche, OnBase, SharePoint" },
  { key: "utilities", label: "Utilities & Public Works", hint: "CIS Infinity, Cartegraph, Lucity" },
  { key: "courts", label: "Courts & Legal", hint: "Tyler Odyssey, Journal Technologies" },
  { key: "parks", label: "Parks & Recreation", hint: "RecTrac, CivicRec, ActiveNet" },
];

const STEPS = [
  { phase: 1, label: "City Profile", icon: Building2 },
  { phase: 2, label: "Systems", icon: MapPin },
  { phase: 3, label: "Gap Map", icon: AlertTriangle },
];

function loadSavedProfile(): CityProfile {
  try {
    const saved = localStorage.getItem("civicrecords_city_profile");
    if (saved) return JSON.parse(saved);
  } catch {}
  return {
    cityName: "", state: "CO", county: "", populationBand: "",
    emailPlatform: "", hasDedicatedIT: "", monthlyRequestVolume: "",
    systems: {},
  };
}

export default function Onboarding({ token }: { token: string }) {
  const [step, setStep] = useState(1);
  const [profile, setProfile] = useState<CityProfile>(loadSavedProfile);
  const navigate = useNavigate();

  const updateProfile = (updates: Partial<CityProfile>) => {
    setProfile((prev) => ({ ...prev, ...updates }));
  };

  const updateSystem = (domain: string, vendor: string, notes: string) => {
    setProfile((prev) => ({
      ...prev,
      systems: { ...prev.systems, [domain]: { vendor, notes } },
    }));
  };

  const saveAndContinue = () => {
    localStorage.setItem("civicrecords_city_profile", JSON.stringify(profile));
    if (step < 3) {
      setStep(step + 1);
    } else {
      localStorage.setItem("civicrecords_onboarding_complete", "true");
      navigate("/city-profile");
    }
  };

  const domainsWithoutSystems = DOMAINS.filter(
    (d) => !profile.systems[d.key]?.vendor
  );

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Welcome to CivicRecords AI"
        description="Let's set up your city profile. This takes about 15-20 minutes."
      />

      {/* Progress steps */}
      <div className="flex items-center gap-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = step === s.phase;
          const isDone = step > s.phase;
          return (
            <div key={s.phase} className="flex items-center gap-2">
              {i > 0 && <div className={cn("w-8 h-px", isDone ? "bg-primary" : "bg-border")} />}
              <div
                className={cn(
                  "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm",
                  isActive ? "bg-primary text-primary-foreground" :
                  isDone ? "bg-primary/10 text-primary" :
                  "bg-muted text-muted-foreground"
                )}
              >
                {isDone ? <CheckCircle className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                {s.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Phase 1: City Profile */}
      {step === 1 && (
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>Tell us about your city</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">City Name *</label>
                <Input
                  value={profile.cityName}
                  onChange={(e) => updateProfile({ cityName: e.target.value })}
                  placeholder="e.g. City of Lakewood"
                />
              </div>
              <div>
                <label className="text-sm font-medium">State *</label>
                <Select value={profile.state} onValueChange={(v) => updateProfile({ state: v ?? "CO" })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {STATES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">County</label>
                <Input
                  value={profile.county}
                  onChange={(e) => updateProfile({ county: e.target.value })}
                  placeholder="e.g. Jefferson County"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Population *</label>
                <Select value={profile.populationBand} onValueChange={(v) => updateProfile({ populationBand: v ?? "" })}>
                  <SelectTrigger><SelectValue placeholder="Select range" /></SelectTrigger>
                  <SelectContent>
                    {POPULATION_BANDS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Email Platform *</label>
                <Select value={profile.emailPlatform} onValueChange={(v) => updateProfile({ emailPlatform: v ?? "" })}>
                  <SelectTrigger><SelectValue placeholder="Select platform" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="microsoft365">Microsoft 365</SelectItem>
                    <SelectItem value="google">Google Workspace</SelectItem>
                    <SelectItem value="exchange">On-premise Exchange</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Dedicated IT Department?</label>
                <Select value={profile.hasDedicatedIT} onValueChange={(v) => updateProfile({ hasDedicatedIT: v ?? "" })}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="yes">Yes — dedicated IT staff</SelectItem>
                    <SelectItem value="no">No — IT is a shared role</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Monthly Records Requests</label>
                <Select value={profile.monthlyRequestVolume} onValueChange={(v) => updateProfile({ monthlyRequestVolume: v ?? "" })}>
                  <SelectTrigger><SelectValue placeholder="Approximate volume" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1-5">1-5 per month</SelectItem>
                    <SelectItem value="5-20">5-20 per month</SelectItem>
                    <SelectItem value="20-50">20-50 per month</SelectItem>
                    <SelectItem value="50+">50+ per month</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Phase 2: System Identification */}
      {step === 2 && (
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>What systems does your city use?</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              For each department, tell us the software system name. Skip any you don't know — you can add them later.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {DOMAINS.map((domain) => {
              const existing = profile.systems[domain.key];
              return (
                <div key={domain.key} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-start">
                  <div>
                    <p className="text-sm font-medium">{domain.label}</p>
                    <p className="text-xs text-muted-foreground">{domain.hint}</p>
                  </div>
                  <Input
                    value={existing?.vendor || ""}
                    onChange={(e) => updateSystem(domain.key, e.target.value, existing?.notes || "")}
                    placeholder="System name or vendor"
                  />
                  <Input
                    value={existing?.notes || ""}
                    onChange={(e) => updateSystem(domain.key, existing?.vendor || "", e.target.value)}
                    placeholder="Notes (cloud/on-prem, version, etc.)"
                  />
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Phase 3: Gap Map */}
      {step === 3 && (
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>Gap Map</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              These are functional areas where your city should have data but you haven't identified a system yet.
              This is normal — you can connect sources later from the Sources page.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {domainsWithoutSystems.length === 0 ? (
              <div className="flex items-center gap-2 text-success py-4">
                <CheckCircle className="h-5 w-5" />
                <p className="font-medium">All domains have an identified system. Great coverage!</p>
              </div>
            ) : (
              domainsWithoutSystems.map((domain) => (
                <div key={domain.key} className="flex items-center justify-between py-3 border-b last:border-0">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-4 w-4 text-warning" />
                    <div>
                      <p className="text-sm font-medium">{domain.label}</p>
                      <p className="text-xs text-muted-foreground">No system identified</p>
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => { setStep(2); }}
                  >
                    Identify System
                  </Button>
                </div>
              ))
            )}

            {/* Show identified systems */}
            {Object.entries(profile.systems).filter(([, v]) => v.vendor).length > 0 && (
              <>
                <Separator className="my-4" />
                <p className="text-label uppercase text-muted-foreground">Identified Systems</p>
                {Object.entries(profile.systems)
                  .filter(([, v]) => v.vendor)
                  .map(([key, val]) => {
                    const domain = DOMAINS.find((d) => d.key === key);
                    return (
                      <div key={key} className="flex items-center gap-3 py-2">
                        <CheckCircle className="h-4 w-4 text-success" />
                        <span className="text-sm font-medium">{domain?.label}</span>
                        <Badge variant="outline" className="text-xs">{val.vendor}</Badge>
                      </div>
                    );
                  })}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <Button onClick={saveAndContinue}>
          {step === 3 ? "Complete Setup" : "Continue"}
          {step < 3 && <ChevronRight className="h-4 w-4 ml-1" />}
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Onboarding.tsx
git commit -m "feat: add Onboarding Interview wizard (3-phase, localStorage)

- Phase 1: City Profile (state, population, email, IT staffing, volume)
- Phase 2: System Identification (8 municipal domains with vendor hints)
- Phase 3: Gap Map (shows unidentified domains with navigation back)
- Progress indicator with phase icons
- Saves to localStorage (Phase 2 backend will persist to city_profile table)"
```

---

## Task 2: City Profile & Settings Page

**Files:**
- Create: `frontend/src/pages/CityProfile.tsx`

Reads the profile from localStorage (saved by onboarding). Shows city details, connected systems, and gap map. Links back to re-run onboarding.

- [ ] **Step 1: Create CityProfile.tsx**

Create `frontend/src/pages/CityProfile.tsx`:

```tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const saved = localStorage.getItem("civicrecords_city_profile");
      if (saved) setProfile(JSON.parse(saved));
    } catch {}
  }, []);

  if (!profile || !localStorage.getItem("civicrecords_onboarding_complete")) {
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
```

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/CityProfile.tsx
git commit -m "feat: add City Profile page (reads from localStorage)

- City details card with profile data from onboarding
- Connected Systems list with vendor badges
- Gap Map showing unidentified domains with warning indicators
- CJIS compliance badge on Public Safety domain
- Empty state linking to onboarding if not configured
- Re-run Onboarding button"
```

---

## Task 3: Discovery Dashboard Shell

**Files:**
- Create: `frontend/src/pages/Discovery.tsx`

This is a v1.1 feature — the page exists as a shell with mock data showing what it will look like when the network discovery engine is built.

- [ ] **Step 1: Create Discovery.tsx**

Create `frontend/src/pages/Discovery.tsx`:

```tsx
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Radar,
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Sparkles,
  Lock,
} from "lucide-react";

export default function Discovery({ token }: { token: string }) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Discovery Dashboard"
        description="Network discovery and automatic source identification"
        actions={
          <Button disabled>
            <Radar className="h-4 w-4 mr-2" />
            Run Discovery Scan
          </Button>
        }
      />

      {/* Coming soon notice */}
      <Card className="shadow-none border-primary/20 bg-primary/5">
        <CardContent className="p-4 flex items-start gap-3">
          <Lock className="h-5 w-5 text-primary mt-0.5" />
          <div>
            <p className="text-sm font-medium text-foreground">
              Network Discovery — Coming in v1.1
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              The discovery engine will scan your city's network (with IT authorization) to automatically
              find and identify data sources. It cross-references findings against the Municipal Systems
              Catalog and presents them for your review — nothing connects without your approval.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Preview of what the dashboard will look like */}
      <div className="opacity-60 pointer-events-none">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard label="High Confidence" value={0} icon={CheckCircle} />
          <StatCard label="Needs Review" value={0} icon={HelpCircle} />
          <StatCard label="Unknown" value={0} icon={AlertTriangle} />
          <StatCard label="New Since Last Scan" value={0} icon={Sparkles} />
        </div>
      </div>

      <EmptyState
        icon={Radar}
        title="No discovery scans yet"
        description="When network discovery is enabled in v1.1, this page will show discovered data sources with confidence scores, one-click confirmation, and coverage gap alerts."
      />

      {/* What it will do */}
      <Card className="shadow-none">
        <CardContent className="p-6">
          <h3 className="text-lg font-semibold mb-3">What Discovery Will Do</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <Radar className="h-4 w-4 text-primary" />
                Network Scanning
              </div>
              <p className="text-muted-foreground">
                Scan for database servers, file shares, email servers, and web applications on your city network.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <CheckCircle className="h-4 w-4 text-primary" />
                Auto-Identification
              </div>
              <p className="text-muted-foreground">
                Cross-reference discovered services against the Municipal Systems Catalog to identify vendors and data types.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle className="h-4 w-4 text-primary" />
                Coverage Gaps
              </div>
              <p className="text-muted-foreground">
                Compare connected sources against request patterns to find data that people ask for but isn't indexed.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Discovery.tsx
git commit -m "feat: add Discovery Dashboard shell (v1.1 preview)

- Coming soon notice with feature description
- Preview stat cards (dimmed, non-interactive)
- Empty state explaining what discovery will do
- Feature preview cards (scanning, identification, coverage gaps)
- Run Discovery Scan button (disabled until v1.1)"
```

---

## Task 4: Wire Routing + Sidebar Nav + Verification

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/sidebar-nav.tsx`

- [ ] **Step 1: Update sidebar-nav.tsx**

Add the 3 new pages to the sidebar navigation. Onboarding and City Profile go under a new "Setup" section. Discovery goes under Administration.

Edit `frontend/src/components/sidebar-nav.tsx` — add new imports and nav groups:

Add to imports:
```tsx
import {
  Search,
  FileText,
  Shield,
  FolderOpen,
  HardDrive,
  LayoutDashboard,
  Users,
  Building2,
  ClipboardList,
  Radar,
  type LucideIcon,
} from "lucide-react";
```

Add a new SETUP_ITEMS array after WORKFLOW_ITEMS:
```tsx
const SETUP_ITEMS: NavItem[] = [
  { path: "/onboarding", label: "Onboarding", icon: ClipboardList },
  { path: "/city-profile", label: "City Profile", icon: Building2 },
];
```

Add Discovery to ADMIN_ITEMS:
```tsx
const ADMIN_ITEMS: NavItem[] = [
  { path: "/sources", label: "Sources", icon: FolderOpen },
  { path: "/ingestion", label: "Ingestion", icon: HardDrive },
  { path: "/discovery", label: "Discovery", icon: Radar },
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/users", label: "Users", icon: Users },
];
```

Add a Setup section to the nav JSX (after Workflow, before Administration):
```tsx
<Separator className="my-3" />

<p className="px-3 mb-1 text-label uppercase text-muted-foreground">
  Setup
</p>
{SETUP_ITEMS.map((item) => (
  <NavLink key={item.path} item={item} />
))}
```

- [ ] **Step 2: Update App.tsx with new routes**

Add imports for the 3 new pages and add Route entries.

Add imports:
```tsx
import Onboarding from "@/pages/Onboarding";
import CityProfile from "@/pages/CityProfile";
import Discovery from "@/pages/Discovery";
```

Add routes (before the catch-all):
```tsx
<Route path="/onboarding" element={<Onboarding token={token} />} />
<Route path="/city-profile" element={<CityProfile token={token} />} />
<Route path="/discovery" element={<Discovery token={token} />} />
```

- [ ] **Step 3: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Rebuild Docker and verify in browser**

```bash
docker compose build frontend && docker compose up -d frontend
```

Navigate to each new page and verify:
- `/onboarding` — wizard loads, 3-step progress indicator, form fields work
- `/city-profile` — shows empty state if onboarding not completed, or profile data if it has
- `/discovery` — shows "Coming in v1.1" notice with preview cards

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: wire Onboarding, City Profile, and Discovery into routing and sidebar

- Sidebar: new Setup section (Onboarding, City Profile) + Discovery under Admin
- App.tsx: 3 new routes added
- All 11 pages accessible from sidebar navigation"
```

---

## Summary

After Phase 1B, the staff workbench has 11 pages:
- **8 redesigned** (Phase 1A): Dashboard, Search, Requests, Request Detail, Exemptions, Sources, Ingestion, Users
- **3 new** (Phase 1B): Onboarding Interview, City Profile & Settings, Discovery Dashboard shell
- Sidebar organized into 3 groups: Workflow (3), Setup (2), Administration (5 + Discovery)
- Onboarding data persists in localStorage until Phase 2 backend wires it to the `city_profile` API
