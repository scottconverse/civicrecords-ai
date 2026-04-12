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
