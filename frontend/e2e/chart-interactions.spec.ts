import { expect, test } from "@playwright/test";
import { stat } from "node:fs/promises";

test("analysis chart click updates URL state", async ({ page }) => {
  await page.goto("/analysis?tab=sources");
  await expect(page.getByTestId("advanced-chart-source-volume-treemap")).toBeVisible();
  const sourceItem = page.getByTestId(/^treemap-item-source-volume-treemap-/).first();
  if (await sourceItem.count()) {
    await expect(sourceItem).toBeVisible();
    await sourceItem.click();
    await expect(page).toHaveURL(/source=/);
  } else {
    await expect(page.getByText("No treemap data")).toBeVisible();
  }

  await expect(page.getByTestId("advanced-chart-source-category-heatmap")).toBeVisible();
  const heatmapCell = page.getByTestId(/^heatmap-cell-source-category-heatmap-/).first();
  if (await heatmapCell.count()) {
    await expect(heatmapCell).toBeVisible();
    await heatmapCell.click();
    await expect(page).toHaveURL(/category=/);
  } else {
    await expect(page.getByText("No heatmap data").first()).toBeVisible();
  }
});

test("text mining topic, cluster, and entity modals restore from URL", async ({ page }) => {
  await page.goto("/text-mining?tab=topics&topic_id=0");
  await expect(page.getByTestId("drilldown-modal")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Topic 0/ })).toBeVisible();

  await page.goto("/text-mining?tab=clusters&cluster_id=0");
  await expect(page.getByTestId("drilldown-modal")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Cluster 0/ })).toBeVisible();

  await page.goto("/text-mining?tab=entities");
  await expect(page.getByTestId("advanced-chart-text-mining-entity-intelligence-network")).toBeVisible();
  const entityNode = page.getByTestId(/^network-node-text-mining-entity-intelligence-network-/).first();
  if (await entityNode.count()) {
    await expect(entityNode).toBeVisible();
    await entityNode.click();
    await expect(page).toHaveURL(/tab=entities/);
    await expect(page).toHaveURL(/entity=/);
    await expect(page.getByTestId("drilldown-modal")).toBeVisible();
  } else {
    await expect(page.getByText("No network data")).toBeVisible();
  }
});

test("chart PNG and SVG exports are non-empty", async ({ page }, testInfo) => {
  await page.goto("/text-mining?tab=entities");
  await expect(page.getByTestId("advanced-chart-text-mining-entity-frequency")).toBeVisible();

  const pngDownload = page.waitForEvent("download");
  await page.getByTestId("chart-export-png-text-mining-entity-frequency").click();
  const png = await pngDownload;
  const pngPath = testInfo.outputPath(png.suggestedFilename());
  await png.saveAs(pngPath);
  expect((await stat(pngPath)).size).toBeGreaterThan(100);

  const svgDownload = page.waitForEvent("download");
  await page.getByTestId("chart-export-svg-text-mining-entity-frequency").click();
  const svg = await svgDownload;
  const svgPath = testInfo.outputPath(svg.suggestedFilename());
  await svg.saveAs(svgPath);
  expect((await stat(svgPath)).size).toBeGreaterThan(100);
});

test("mobile tabs and tables remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/text-mining?tab=entities");
  await expect(page.getByRole("tab", { name: "Entities" })).toBeVisible();
  await expect(page.getByText("Representative Articles")).toBeVisible();
  await expect(page.locator(".overflow-x-auto").first()).toBeVisible();
});
