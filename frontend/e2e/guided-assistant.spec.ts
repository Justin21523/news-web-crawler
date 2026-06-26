import { expect, test } from "@playwright/test";

const routes = [
  { path: "/", heading: /Workflow 不是裝飾|Workflow Reflects Real State/ },
  { path: "/journey", heading: /歡迎來到 News Data Intelligence Platform|Welcome to News Data Intelligence Platform/ },
  { path: "/data-quality", heading: /資料品質分析|Data Quality Analysis/ },
  { path: "/analysis", heading: /EDA \/ Business Analysis/ },
  { path: "/text-mining", heading: /Text Mining 工作台|Text Mining Workbench/ },
  { path: "/articles", heading: /可探索文章資料庫|Explorable Article Database/ },
  { path: "/ml", heading: /ML Models 與 Diagnostics|ML Models and Diagnostics/ },
  { path: "/jobs", heading: /執行 Pipeline Jobs|Run Pipeline Jobs/ },
  { path: "/ml/diagnostics/reports", heading: /報表與作品集輸出|Reports and Portfolio Output/ },
];

test.describe("guided assistant default behavior", () => {
  for (const route of routes) {
    test(`opens by default on ${route.path}`, async ({ page }) => {
      await page.goto(route.path);
      const panel = page.locator(".guided-assistant-panel");
      await expect(panel).toBeVisible();
      await expect(panel.getByRole("heading", { name: route.heading })).toBeVisible();
    });
  }

  test("supports full tour navigation, language switching, close, and reopen-on-new-entry", async ({ page }) => {
    await page.goto("/journey");
    const panel = page.locator(".guided-assistant-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator(".guided-tour-spotlight")).toBeVisible();

    await panel.getByRole("button", { name: /下一步|Next/ }).click();
    await expect(panel.getByRole("heading", { name: /從資料開始|Start with Data/ })).toBeVisible();
    await expect(page).toHaveURL(/\/journey/);

    await panel.getByRole("button", { name: /下一步|Next/ }).click();
    await expect(page).toHaveURL(/\/jobs/);
    await expect(panel.getByRole("heading", { name: /執行 Pipeline Jobs|Run Pipeline Jobs/ })).toBeVisible();

    await page.getByRole("button", { name: /EN|中文/ }).first().click();
    await expect(panel.getByRole("heading", { name: /Run Pipeline Jobs|執行 Pipeline Jobs/ })).toBeVisible();

    await page.getByRole("button", { name: /Close|關閉/ }).click();
    await expect(page.locator(".guided-assistant-panel")).toHaveCount(0);

    await page.goto("/data-quality");
    const reopenedPanel = page.locator(".guided-assistant-panel");
    await expect(reopenedPanel).toBeVisible();
    await expect(reopenedPanel.getByRole("heading", { name: /Data Quality Analysis|資料品質分析/ })).toBeVisible();
  });
});
