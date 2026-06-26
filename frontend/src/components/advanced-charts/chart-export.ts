"use client";

import { toPng, toSvg } from "html-to-image";

import { downloadText } from "@/components/advanced-charts/chart-theme";

export async function downloadNodeImage(node: HTMLElement | null, filename: string, format: "png" | "svg") {
  if (!node) return;
  const backgroundColor = getComputedStyle(document.documentElement).getPropertyValue("--chart-bg").trim() || "#0b1626";
  const dataUrl = format === "png"
    ? await toPng(node, { backgroundColor, pixelRatio: 2 })
    : await toSvg(node, { backgroundColor });
  const anchor = document.createElement("a");
  anchor.href = dataUrl;
  anchor.download = `${filename}.${format}`;
  anchor.click();
}

export function downloadSvgText(filename: string, svg: string) {
  downloadText(`${filename}.svg`, svg, "image/svg+xml");
}
