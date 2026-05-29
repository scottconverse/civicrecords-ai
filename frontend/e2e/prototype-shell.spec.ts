import { expect, test } from "@playwright/test";

test.describe("Records AI operator shell accessibility contract", () => {
  test("staff shell exposes launcher return, audit drawer, and command palette affordances", async ({ page }) => {
    await page.addInitScript(() => {
      const payload = btoa(JSON.stringify({
        exp: 2000000000,
        email: "operator@example.gov",
      })).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      localStorage.setItem("token", `header.${payload}.signature`);
    });

    await page.route("**/config/portal-mode", async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ mode: "private" }),
      });
    });
    await page.route("**/users/me", async (route) => {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          email: "operator@example.gov",
          full_name: "Records Operator",
          role: "admin",
          must_change_password: false,
        }),
      });
    });

    await page.goto("/");

    await expect(page.getByRole("link", { name: /skip to main content/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /help/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /suite launcher/i })).toBeVisible();

    await page.getByRole("button", { name: /audit/i }).click();
    await expect(page.getByRole("dialog", { name: /audit/i })).toBeVisible();

    await page.keyboard.press("Control+K");
    await expect(page.getByRole("dialog", { name: /command palette/i })).toBeVisible();
  });
});
