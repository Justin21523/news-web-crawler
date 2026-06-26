"use client";

import { EmptyState } from "@/components/ui";

export function HeatmapChart({
  xLabels,
  yLabels,
  values,
  height = 360,
  exportName = "heatmap",
  onSelect,
}: {
  xLabels: string[];
  yLabels: string[];
  values: Array<[number, number, number]>;
  height?: number;
  exportName?: string;
  onSelect?: (selection: { xLabel: string; yLabel: string; value: number }) => void;
}) {
  void exportName;
  if (!xLabels.length || !yLabels.length || !values.length) return <EmptyState title="No heatmap data" detail="Adjust filters, run the related job, or expand the date range." />;
  const max = Math.max(1, ...values.map((item) => Number(item[2] || 0)));
  const lookup = new Map(values.map(([x, y, value]) => [`${x}-${y}`, value]));
  return (
    <div className="overflow-x-auto" style={{ minHeight: height }}>
      <div className="grid min-w-[640px] gap-1" style={{ gridTemplateColumns: `120px repeat(${xLabels.length}, minmax(48px, 1fr))` }}>
        <div />
        {xLabels.map((label) => <div key={label} className="truncate px-1 text-center text-[0.68rem] font-semibold text-muted" title={label}>{label}</div>)}
        {yLabels.map((rowLabel, y) => (
          <div key={rowLabel} className="contents">
            <div className="truncate py-2 pr-2 text-xs font-semibold text-ink" title={rowLabel}>{rowLabel}</div>
            {xLabels.map((colLabel, x) => {
              const value = Number(lookup.get(`${x}-${y}`) ?? 0);
              const intensity = value / max;
              return (
                <div
                  key={`${rowLabel}-${colLabel}`}
                  role={onSelect ? "button" : undefined}
                  tabIndex={onSelect ? 0 : undefined}
                  data-testid={`heatmap-cell-${exportName}-${rowLabel}-${colLabel}`.replace(/\s+/g, "-")}
                  className="numeric rounded px-2 py-3 text-center text-xs font-semibold"
                  title={`${rowLabel} → ${colLabel}: ${value}`}
                  onClick={() => onSelect?.({ xLabel: colLabel, yLabel: rowLabel, value })}
                  onKeyDown={(event) => {
                    if ((event.key === "Enter" || event.key === " ") && onSelect) onSelect({ xLabel: colLabel, yLabel: rowLabel, value });
                  }}
                  style={{
                    backgroundColor: `rgba(37, 99, 235, ${0.08 + intensity * 0.62})`,
                    color: intensity > 0.45 ? "#ffffff" : "var(--text-secondary)",
                  }}
                >
                  {value}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
