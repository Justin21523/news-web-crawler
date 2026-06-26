"use client";

import { EmptyState } from "@/components/ui";
import { chartPalette } from "@/components/advanced-charts/chart-theme";

export function WordCloudChart({
  data,
  nameKey = "term",
  valueKey = "weight",
  height = 360,
  exportName = "word-cloud",
}: {
  data: Array<Record<string, string | number | null | undefined>>;
  nameKey?: string;
  valueKey?: string;
  height?: number;
  exportName?: string;
}) {
  const rows = data
    .map((item) => ({
      name: String(item[nameKey] ?? item.keyword ?? item.ngram ?? item.entity ?? ""),
      value: Number(item[valueKey] ?? item.score ?? item.count ?? 0),
    }))
    .filter((item) => item.name && item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 60);

  if (!rows.length) return <EmptyState title="No word cloud data" detail="Adjust filters or run text mining analysis." />;

  const max = Math.max(...rows.map((item) => item.value));
  const min = Math.min(...rows.map((item) => item.value));
  const span = Math.max(max - min, 0.0001);

  return (
    <div
      data-testid={`word-cloud-${exportName}`}
      className="relative overflow-hidden rounded-lg border border-line bg-[radial-gradient(circle_at_30%_20%,rgba(34,211,238,.16),transparent_32%),linear-gradient(135deg,rgba(16,28,46,.98),rgba(7,17,31,.98))] p-4"
      style={{ minHeight: height }}
    >
      <div className="flex min-h-[inherit] flex-wrap content-center items-center justify-center gap-x-4 gap-y-3">
        {rows.map((item, index) => {
          const normalized = (item.value - min) / span;
          const fontSize = 0.82 + normalized * 1.95;
          const opacity = 0.62 + normalized * 0.36;
          const color = chartPalette[index % chartPalette.length];
          return (
            <span
              key={`${item.name}-${index}`}
              className="inline-flex max-w-full items-center rounded-md border border-white/5 bg-white/[0.025] px-2 py-1 font-bold leading-none tracking-normal transition hover:scale-105 hover:border-primary/35 hover:bg-primary-soft-2"
              style={{ color, fontSize: `${fontSize}rem`, opacity }}
              title={`${item.name}: ${Number(item.value).toFixed(4)}`}
            >
              {item.name}
            </span>
          );
        })}
      </div>
    </div>
  );
}
