"use client";

import type { EChartsOption } from "echarts";

import { EChart } from "@/components/advanced-charts/EChart";

export function BubbleScatterChart({ rows, xKey, yKey, sizeKey = "count", labelKey = "term", height = 360, exportName = "bubble-scatter" }: { rows: Array<Record<string, string | number | null | undefined>>; xKey: string; yKey: string; sizeKey?: string; labelKey?: string; height?: number; exportName?: string }) {
  const items = rows
    .map((row) => [Number(row[xKey] ?? 0), Number(row[yKey] ?? 0), Number(row[sizeKey] ?? 1), String(row[labelKey] ?? row.keyword ?? row.entity ?? row.collocation ?? "")])
    .filter((item) => Number.isFinite(item[0]) && Number.isFinite(item[1]) && item[3])
    .slice(0, 80);
  const maxSize = Math.max(1, ...items.map((item) => Number(item[2])));
  const option = {
    grid: { left: 42, right: 20, top: 24, bottom: 42 },
    xAxis: { name: xKey, axisLabel: { color: "var(--color-muted)" }, splitLine: { lineStyle: { color: "var(--chart-grid)" } } },
    yAxis: { name: yKey, axisLabel: { color: "var(--color-muted)" }, splitLine: { lineStyle: { color: "var(--chart-grid)" } } },
    series: [{
      type: "scatter",
      data: items,
      symbolSize: (value: Array<number | string>) => Math.max(8, Math.min(42, 8 + (Number(value[2]) / maxSize) * 34)),
      label: { show: true, formatter: (params: { value: Array<number | string> }) => String(params.value[3]).slice(0, 14), color: "var(--color-text-secondary)", position: "top", fontSize: 10 },
      itemStyle: { opacity: 0.82 },
    }],
  } as EChartsOption;
  return <EChart option={option} height={height} empty={!items.length} emptyTitle="No scatter data" exportName={exportName} />;
}
