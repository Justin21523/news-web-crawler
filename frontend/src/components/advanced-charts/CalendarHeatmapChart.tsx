"use client";

import { EmptyState } from "@/components/ui";

export function CalendarHeatmapChart({ data, height = 260, exportName = "calendar-heatmap", onSelect }: { data: Array<{ date: string; count: number }>; height?: number; exportName?: string; onSelect?: (item: { date: string; count: number }) => void }) {
  void exportName;
  if (!data.length) return <EmptyState title="No calendar data" detail="Adjust filters or run the related analysis job." />;
  const max = Math.max(1, ...data.map((item) => Number(item.count || 0)));
  return (
    <div className="grid grid-cols-7 gap-1" style={{ minHeight: height }}>
      {data.slice(0, 84).map((item) => {
        const intensity = Number(item.count || 0) / max;
        return (
          <button key={item.date} type="button" onClick={() => onSelect?.(item)} className="rounded p-2 text-center transition hover:scale-[1.03] focus:outline-none focus:ring-2 focus:ring-primary" title={`${item.date}: ${item.count}`} style={{ backgroundColor: `rgba(15, 118, 110, ${0.08 + intensity * 0.64})`, color: intensity > 0.45 ? "#ffffff" : "var(--text-secondary)" }}>
            <div className="text-[0.62rem] font-semibold">{item.date.slice(5)}</div>
            <div className="numeric text-xs font-bold">{item.count}</div>
          </button>
        );
      })}
    </div>
  );
}
