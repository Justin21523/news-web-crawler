"use client";

import { EmptyState } from "@/components/ui";
import { chartPalette } from "@/components/advanced-charts/chart-theme";

export function TreemapChart({ data, height = 340, exportName = "treemap", onSelect }: { data: Array<{ name: string; value: number }>; height?: number; exportName?: string; onSelect?: (item: { name: string; value: number }) => void }) {
  void exportName;
  if (!data.length) return <EmptyState title="No treemap data" detail="Adjust filters or run the related analysis job." />;
  const total = data.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1;
  return (
    <div className="grid auto-rows-[96px] grid-cols-2 gap-2 md:grid-cols-3" style={{ minHeight: height }}>
      {data.slice(0, 12).map((item, index) => (
        <button key={item.name} type="button" data-testid={`treemap-item-${exportName}-${item.name}`.replace(/\s+/g, "-")} onClick={() => onSelect?.(item)} className="flex flex-col justify-between rounded-md p-3 text-left text-white shadow-sm transition hover:scale-[1.01] focus:outline-none focus:ring-2 focus:ring-primary" style={{ background: chartPalette[index % chartPalette.length], gridRow: Number(item.value) / total > 0.28 ? "span 2" : "span 1" }}>
          <div className="truncate text-sm font-semibold" title={item.name}>{item.name}</div>
          <div>
            <div className="numeric text-2xl font-semibold">{item.value}</div>
            <div className="text-xs text-white/80">{Math.round((Number(item.value) / total) * 100)}% share</div>
          </div>
        </button>
      ))}
    </div>
  );
}
