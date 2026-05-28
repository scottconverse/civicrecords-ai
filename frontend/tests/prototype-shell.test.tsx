import { describe, expect, it } from "vitest";

import { AuditDrawer } from "../src/components/audit-drawer";
import { CommandPalette } from "../src/components/command-palette";
import { VersionFooter } from "../src/components/version-footer";
import "../src/globals.css";

describe("Records AI prototype shell contracts", () => {
  it("exports the audit drawer, command palette, and health-backed version footer", () => {
    expect(AuditDrawer).toBeTypeOf("function");
    expect(CommandPalette).toBeTypeOf("function");
    expect(VersionFooter).toBeTypeOf("function");
  });

  it("loads the prototype font and color tokens used by the city-core shell", () => {
    const styles = Array.from(document.styleSheets)
      .flatMap((sheet) => Array.from(sheet.cssRules ?? []))
      .map((rule) => rule.cssText)
      .join("\n");

    expect(styles).toContain("--paper");
    expect(styles).toContain("--navy");
    expect(styles).toContain("--gold");
    expect(styles).toContain("JetBrains Mono");
  });
});
