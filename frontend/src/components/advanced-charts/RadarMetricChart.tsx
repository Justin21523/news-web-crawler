"use client";

import type { EChartsOption } from "echarts";

import { EChart } from "@/components/advanced-charts/EChart";

export function RadarMetricChart({ rows, labelKey = "label", valueKey = "value", height = 320, exportName = "radar-metrics" }: { rows: Array<Record<string, string | number | null | undefined>>; labelKey?: string; valueKey?: string; height?: number; exportName?: string }) {
  const items = rows.map((row) => ({ name: String(row[labelKey] ?? row.metric ?? row.term ?? ""), value: Number(row[valueKey] ?? row.score ?? row.count ?? 0) })).filter((item) => item.name && item.value > 0).slice(0, 8);
  const max = Math.max(1, ...items.map((item) => item.value));
  const option = {
    radar: {
      radius: "68%",
      indicator: items.map((item) => ({ name: item.name, max })),
      axisName: { color: "var(--color-text-secondary)", fontSize: 11 },
      splitLine: { lineStyle: { color: "var(--color-border)" } },
      splitArea: { areaStyle: { color: ["rgba(34,211,238,.04)", "rgba(167,139,250,.05)"] } },
      axisLine: { lineStyle: { color: "var(--color-border)" } },
    },
    series: [{ type: "radar", data: [{ value: items.map((item) => item.value), name: "Score" }], areaStyle: { opacity: 0.22 } }],
  } as EChartsOption;
  return <EChart option={option} height={height} empty={!items.length} emptyTitle="No radar data" exportName={exportName} />;
}
