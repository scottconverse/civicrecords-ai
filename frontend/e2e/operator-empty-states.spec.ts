import { expect, test, type Page } from "@playwright/test";

function fakeJwt(role: string) {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "user-1",
      email: `${role}@example.gov`,
      role,
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
  );
  return `${header}.${payload}.signature`;
}

async function mockOperatorApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api/, "");

    if (path === "/config/portal-mode") {
      await route.fulfill({ json: { mode: "admin" } });
      return;
    }
    if (path === "/users/me") {
      await route.fulfill({ json: { email: "admin@example.gov", full_name: "Admin User", role: "admin" } });
      return;
    }
    if (path === "/admin/status") {
      await route.fulfill({
        json: {
          version: "1.7.3-empty-state-qa",
          database: "connected",
          redis: "connected",
          ollama: "connected",
          user_count: 0,
          audit_log_count: 0,
        },
      });
      return;
    }
    if (path === "/analytics/operational") {
      await route.fulfill({
        json: {
          average_response_time_days: null,
          median_response_time_days: null,
          requests_by_status: {},
          requests_by_department: {},
          deadline_compliance_rate: 100,
          total_open: 0,
          total_closed: 0,
          total_overdue: 0,
          clarification_frequency: 0,
          top_request_topics: [],
        },
      });
      return;
    }
    if (path === "/audit/logs") {
      await route.fulfill({ json: [] });
      return;
    }
    if (path === "/admin/coverage-gaps") {
      await route.fulfill({ json: null });
      return;
    }
    if (path === "/requests/stats") {
      await route.fulfill({
        json: { total_requests: 0, by_status: {}, approaching_deadline: 0, overdue: 0 },
      });
      return;
    }
    if (path === "/requests/") {
      await route.fulfill({ json: [] });
      return;
    }
    if (path === "/departments/" || path === "/admin/users" || path === "/datasources/" || path === "/documents/" || path === "/exemptions/rules/") {
      await route.fulfill({ json: [] });
      return;
    }
    if (path === "/datasources/stats") {
      await route.fulfill({
        json: {
          total_sources: 0,
          active_sources: 0,
          total_documents: 0,
          documents_by_status: {},
          total_chunks: 0,
        },
      });
      return;
    }
    if (path === "/exemptions/dashboard") {
      await route.fulfill({
        json: {
          total_flags: 0,
          by_status: {},
          by_category: {},
          acceptance_rate: 100,
          total_rules: 0,
          active_rules: 0,
        },
      });
      return;
    }
    if (path === "/search/filters") {
      await route.fulfill({ json: { file_types: [], source_names: [], departments: [], date_range: null } });
      return;
    }
    if (path === "/search/query") {
      await route.fulfill({
        json: {
          query_id: "query-1",
          session_id: "session-1",
          query_text: "water quality",
          results: [],
          results_count: 0,
          synthesized_answer: null,
          ai_generated: false,
        },
      });
      return;
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled mock route: ${path}` } });
  });
}

async function screenshotEvidence(page: Page, name: string, testInfo: { outputPath: (path: string) => string }) {
  await page.screenshot({ path: testInfo.outputPath(`${name}.png`), fullPage: true });
}

test.describe("operator empty states and zero-request dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await mockOperatorApi(page);
    await page.addInitScript((token) => localStorage.setItem("token", token), fakeJwt("admin"));
  });

  test("dashboard avoids fake deadline compliance and shows actionable empty panels", async ({ page }, testInfo) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.getByText("100.0%")).toHaveCount(0);
    await expect(page.getByText("No requests yet. Compliance will calculate once request work is tracked.")).toBeVisible();
    await expect(page.getByText("No deadlines in the next 3 days")).toBeVisible();
    await expect(page.getByRole("button", { name: "View Requests" })).toBeVisible();
    await expect(page.getByText("No recent activity yet")).toBeVisible();
    await expect(page.getByRole("button", { name: "Open Audit Log" })).toBeVisible();

    await screenshotEvidence(page, "dashboard-zero-compliance", testInfo);
  });

  test("operator pages show actionable empty states", async ({ page }, testInfo) => {
    const pages = [
      { path: "/requests", title: "No requests are being tracked yet", cta: "Create First Request", shot: "requests-empty" },
      { path: "/sources", title: "No connected sources yet", cta: "Connect First Source", shot: "sources-empty" },
      { path: "/ingestion", title: "No documents have been ingested yet", cta: "Go to Sources", shot: "ingestion-empty" },
      { path: "/users", title: "No staff accounts yet", cta: "Create First User", shot: "users-empty" },
      { path: "/audit-log", title: "No audit activity has been recorded yet", cta: "Open Requests", shot: "audit-log-empty" },
    ];

    for (const pageCase of pages) {
      await page.goto(pageCase.path);
      await expect(page.getByText(pageCase.title)).toBeVisible();
      await expect(page.getByRole("button", { name: pageCase.cta })).toBeVisible();
      await screenshotEvidence(page, pageCase.shot, testInfo);
    }

    await page.goto("/exemptions");
    await expect(page.getByText("No exemption rules set up yet")).toBeVisible();
    await expect(page.getByRole("button", { name: "Add First Rule" })).toBeVisible();
    await page.getByRole("tab", { name: "Flags for Review" }).click();
    await expect(page.getByText("No flags ready for review")).toBeVisible();
    await expect(page.getByRole("button", { name: "View Ingestion" })).toBeVisible();
    await screenshotEvidence(page, "exemptions-empty", testInfo);

    await page.goto("/search");
    await expect(page.getByText("Search ingested city records")).toBeVisible();
    await page.getByPlaceholder("Search documents... e.g. 'water quality reports 2025'").fill("water quality");
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page.getByText("No records matched this search")).toBeVisible();
    await expect(page.getByRole("button", { name: "Start New Search" })).toBeVisible();
    await screenshotEvidence(page, "search-empty-results", testInfo);
  });
});
