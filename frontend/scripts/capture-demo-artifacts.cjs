#!/usr/bin/env node
const { chromium } = require("@playwright/test");
const fs = require("node:fs/promises");
const path = require("node:path");

const baseURL = process.env.E2E_BASE_URL || process.env.BASE_URL || "http://127.0.0.1:3009";
const outRoot = path.resolve(process.env.OUT_DIR || "../docs/demo-artifacts/latest");
const screenshotDir = path.join(outRoot, "screenshots");
const videoDir = path.join(outRoot, "videos");

const routes = [
  { name: "dashboard", path: "/" },
  { name: "journey", path: "/journey" },
  { name: "data-quality", path: "/data-quality" },
  { name: "analysis", path: "/analysis?tab=trends" },
  { name: "text-mining", path: "/text-mining?tab=entities" },
  { name: "articles", path: "/articles" },
  { name: "ml", path: "/ml" },
  { name: "jobs", path: "/jobs" },
  { name: "reports", path: "/ml/diagnostics/reports" },
];

const viewports = [
  { name: "desktop", width: 1440, height: 1000, isMobile: false },
  { name: "mobile", width: 390, height: 844, isMobile: true },
];

async function main() {
  await fs.rm(outRoot, { recursive: true, force: true });
  await fs.mkdir(screenshotDir, { recursive: true });
  await fs.mkdir(videoDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const manifest = {
    baseURL,
    captured_at: new Date().toISOString(),
    screenshots: [],
    videos: [],
  };

  for (const route of routes) {
    for (const viewport of viewports) {
      const page = await browser.newPage({ viewport, isMobile: viewport.isMobile });
      page.setDefaultTimeout(60_000);
      await page.goto(`${baseURL}${route.path}`, { waitUntil: "networkidle" });
      await reduceMotion(page);
      await page.locator(".guided-assistant-panel").waitFor({ timeout: 15000 });
      await captureScrolled(page, route.name, viewport.name, manifest);
      await page.close();
    }
  }

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    recordVideo: { dir: videoDir, size: { width: 1440, height: 1000 } },
  });
  const page = await context.newPage();
  page.setDefaultTimeout(60_000);
  await page.goto(`${baseURL}/journey`, { waitUntil: "networkidle" });
  const panel = page.locator(".guided-assistant-panel");
  await panel.waitFor({ timeout: 15000 });
  for (let i = 0; i < 11; i += 1) {
    await panel.getByRole("button", { name: /下一步|Next/ }).click();
    await page.waitForTimeout(900);
  }
  const video = page.video();
  await page.close();
  await context.close();
  if (video) {
    const original = await video.path();
    const target = path.join(videoDir, "guided-tour.webm");
    await fs.rename(original, target);
    manifest.videos.push(relative(target));
  }

  await browser.close();
  await fs.writeFile(path.join(outRoot, "qa-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf-8");
  console.log(`Demo artifacts written to ${outRoot}`);
}

async function captureScrolled(page, routeName, viewportName, manifest) {
  const viewport = page.viewportSize();
  const totalHeight = await page.evaluate(() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight));
  const step = Math.max(320, Math.floor(viewport.height * 0.82));
  const positions = [];
  for (let y = 0; y < totalHeight; y += step) positions.push(y);
  if (!positions.includes(Math.max(0, totalHeight - viewport.height))) {
    positions.push(Math.max(0, totalHeight - viewport.height));
  }
  const unique = [...new Set(positions)].slice(0, 8);
  for (let index = 0; index < unique.length; index += 1) {
    await page.evaluate((y) => window.scrollTo(0, y), unique[index]);
    await page.waitForTimeout(350);
    const filename = `${routeName}-${viewportName}-${String(index + 1).padStart(2, "0")}.png`;
    const filepath = path.join(screenshotDir, filename);
    await page.screenshot({ path: filepath, fullPage: false, animations: "disabled", timeout: 60_000 });
    manifest.screenshots.push({
      route: routeName,
      viewport: viewportName,
      scroll_y: unique[index],
      file: relative(filepath),
    });
  }
}

async function reduceMotion(page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0.001s !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001s !important;
        scroll-behavior: auto !important;
      }
    `,
  });
}

function relative(filepath) {
  return path.relative(path.resolve(".."), filepath).replaceAll(path.sep, "/");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
