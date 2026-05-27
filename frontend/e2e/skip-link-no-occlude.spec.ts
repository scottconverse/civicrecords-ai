import { expect, test, type Page } from "@playwright/test";

function fakeJwt(role: string) {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "user-1",
      email: `${role}@example.gov`,
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
  );
  return `${header}.${payload}.signature`;
}

async function mockRotationScreen(page: Page) {
  await page.route("**/api/config/portal-mode", route =>
    route.fulfill({ json: { mode: "private" } }),
  );
  await page.route("**/api/users/me", route =>
    route.fulfill({
      json: {
        email: "admin@example.gov",
        full_name: "System Administrator",
        role: "admin",
        must_change_password: true,
      },
    }),
  );
  await page.addInitScript(token => localStorage.setItem("token", token), fakeJwt("admin"));
}

function boxesOverlap(
  a: { x: number; y: number; width: number; height: number },
  b: { x: number; y: number; width: number; height: number },
) {
  return !(
    a.x + a.width <= b.x ||
    b.x + b.width <= a.x ||
    a.y + a.height <= b.y ||
    b.y + b.height <= a.y
  );
}

test("skip link does not occlude the password-rotation heading", async ({ page }) => {
  const viewports = [
    { name: "mobile", width: 390, height: 844 },
    { name: "desktop", width: 1366, height: 900 },
  ];

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await mockRotationScreen(page);
    await page.goto("/settings");

    const skipLink = page.getByRole("link", { name: "Skip to main content" });
    const heading = page.getByRole("heading", { name: "Change Initial Password" });
    const mobileNavTrigger = page.getByRole("button", { name: "Open navigation" });

    await expect(heading).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(skipLink).toBeFocused();

    const [skipBox, headingBox, navBox] = await Promise.all([
      skipLink.boundingBox(),
      heading.boundingBox(),
      viewport.name === "mobile" ? mobileNavTrigger.boundingBox() : Promise.resolve(null),
    ]);

    expect(skipBox, `${viewport.name} skip link bounding box`).not.toBeNull();
    expect(headingBox, `${viewport.name} rotation heading bounding box`).not.toBeNull();
    expect(boxesOverlap(skipBox!, headingBox!), `${viewport.name} boxes overlap`).toBe(false);
    if (navBox) {
      expect(boxesOverlap(skipBox!, navBox), "mobile skip link overlaps nav trigger").toBe(false);
    }

    const screenshotPath = process.env.CRIT1_SCREENSHOT_PATH;
    if (viewport.name === "mobile" && screenshotPath) {
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }
  }
});
