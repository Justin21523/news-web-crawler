"use client";

import type { EChartsOption } from "echarts";

import { EChart } from "@/components/advanced-charts/EChart";

export function MatrixHeatmapChart({ rows, xKey, yKey, valueKey = "count", height = 380, exportName = "matrix-heatmap" }: { rows: Array<Record<string, string | number | null | undefined>>; xKey: string; yKey: string; valueKey?: string; height?: number; exportName?: string }) {
  const xLabels = Array.from(new Set(rows.map((row) => String(row[xKey] ?? "")).filter(Boolean))).slice(0, 24);
  const yLabels = Array.from(new Set(rows.map((row) => String(row[yKey] ?? "")).filter(Boolean))).slice(0, 18);
  const values = rows
    .map((row) => [xLabels.indexOf(String(row[xKey] ?? "")), yLabels.indexOf(String(row[yKey] ?? "")), Number(row[valueKey] ?? 0)])
    .filter(([x, y, value]) => Number(x) >= 0 && Number(y) >= 0 && Number(value) > 0);
  const max = Math.max(1, ...values.map((item) => Number(item[2])));
  const option = {
    grid: { left: 120, right: 30, top: 35, bottom: 90 },
    xAxis: { type: "category", data: xLabels, axisLabel: { color: "var(--color-muted)", rotate: 35 } },
    yAxis: { type: "category", data: yLabels, axisLabel: { color: "var(--color-muted)" } },
    visualMap: { min: 0, max, calculable: true, orient: "horizontal", left: "center", bottom: 4, textStyle: { color: "var(--color-text-secondary)" } },
    series: [{ type: "heatmap", data: values, label: { show: false }, emphasis: { itemStyle: { borderColor: "var(--color-primary)", borderWidth: 1 } } }],
  } as EChartsOption;
  return <EChart option={option} height={height} empty={!values.length} emptyTitle="No matrix data" exportName={exportName} />;
}
