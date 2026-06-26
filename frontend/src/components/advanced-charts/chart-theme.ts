"use client";

export type ChartDatum = Record<string, string | number | boolean | null | undefined>;

export const chartPalette = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
  "var(--chart-9)",
  "var(--chart-10)",
];

export function cssVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function resolvedPalette() {
  return [
    cssVar("--chart-1", "#2563eb"),
    cssVar("--chart-2", "#0f766e"),
    cssVar("--chart-3", "#f59e0b"),
    cssVar("--chart-4", "#7c3aed"),
    cssVar("--chart-5", "#dc2626"),
    cssVar("--chart-6", "#0891b2"),
    cssVar("--chart-7", "#db2777"),
    cssVar("--chart-8", "#64748b"),
    cssVar("--chart-9", "#fb7185"),
    cssVar("--chart-10", "#facc15"),
  ];
}

export function commonTextStyle() {
  return {
    color: cssVar("--text-secondary", "#475569"),
    fontFamily: "var(--font-sans)",
  };
}

export function darkChartBase() {
  return {
    color: resolvedPalette(),
    backgroundColor: "transparent",
    textStyle: commonTextStyle(),
    tooltip: {
      trigger: "item",
      backgroundColor: cssVar("--color-surface-elevated", "#101c2e"),
      borderColor: cssVar("--color-border", "#22324a"),
      textStyle: { color: cssVar("--color-text", "#e5edf7") },
    },
    legend: {
      textStyle: commonTextStyle(),
    },
  };
}

export function downloadText(filename: string, content: string, mime = "text/plain") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function rowsToCsv(rows: ChartDatum[]) {
  if (!rows.length) return "";
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const escape = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  return [headers.map(escape).join(","), ...rows.map((row) => headers.map((key) => escape(row[key])).join(","))].join("\n");
}
