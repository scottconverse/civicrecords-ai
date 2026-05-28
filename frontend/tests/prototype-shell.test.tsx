import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { AppShell } from "../src/components/app-shell";
import { AuditDrawer } from "../src/components/audit-drawer";
import { CommandPalette } from "../src/components/command-palette";
import { VersionFooter } from "../src/components/version-footer";
import "../src/globals.css";

const globalsCss = readFileSync(
  join(process.cwd(), "src", "globals.css"),
  "utf-8"
);
const rootTokenBlock = globalsCss.match(/:root\s*\{[\s\S]*?\n\s{2}\}/)?.[0] ?? "";

describe("Records AI prototype shell contracts", () => {
  it("exports the audit drawer, command palette, and health-backed version footer", () => {
    expect(AuditDrawer).toBeTypeOf("function");
    expect(CommandPalette).toBeTypeOf("function");
    expect(VersionFooter).toBeTypeOf("function");
  });

  it("loads the prototype font and color tokens used by the city-core shell", () => {
    expect(globalsCss).toContain("--paper");
    expect(globalsCss).toContain("--navy");
    expect(globalsCss).toContain("--gold");
    expect(globalsCss).toContain("JetBrains Mono");
  });

  it("renders the shell with prototype tokens available at runtime", () => {
    const style = document.createElement("style");
    style.textContent = rootTokenBlock;
    document.head.appendChild(style);

    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AppShell userEmail="admin@example.gov" userRole="admin" onSignOut={() => undefined}>
          <h1>Prototype token runtime check</h1>
        </AppShell>
      </MemoryRouter>
    );

    const rootStyles = getComputedStyle(document.documentElement);
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(rootStyles.getPropertyValue("--paper").trim()).toBe("#f8f3e8");
    expect(rootStyles.getPropertyValue("--font-sans")).toContain("Inter");
    expect(rootStyles.getPropertyValue("--font-serif")).toContain("Source Serif 4");
    expect(rootStyles.getPropertyValue("--font-mono")).toContain("JetBrains Mono");
  });
});
