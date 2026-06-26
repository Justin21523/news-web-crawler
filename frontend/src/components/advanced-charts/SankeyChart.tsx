"use client";

import { EmptyState } from "@/components/ui";

export function SankeyChart({ rows, sourceKey, targetKey, valueKey = "count", height = 360, exportName = "sankey", onSelect }: { rows: Record<string, string | number | boolean | null | undefined>[]; sourceKey: string; targetKey: string; valueKey?: string; height?: number; exportName?: string; onSelect?: (row: Record<string, string | number | boolean | null | undefined>) => void }) {
  void exportName;
  if (!rows.length) return <EmptyState title="No flow data" detail="Adjust filters, run the related job, or expand the date range." />;
  const sorted = [...rows].sort((a, b) => Number(b[valueKey] ?? 0) - Number(a[valueKey] ?? 0)).slice(0, 12);
  const max = Math.max(1, ...sorted.map((row) => Number(row[valueKey] ?? 0)));
  return (
    <div className="space-y-3" style={{ minHeight: height }}>
      {sorted.map((row, index) => {
        const value = Number(row[valueKey] ?? 0);
        const width = `${Math.max(8, (value / max) * 100)}%`;
        return (
          <button key={`${String(row[sourceKey])}-${String(row[targetKey])}-${index}`} type="button" onClick={() => onSelect?.(row)} className="grid gap-2 rounded-md p-1 text-left transition hover:bg-primary-soft-2 md:grid-cols-[minmax(90px,1fr)_2fr_minmax(90px,1fr)] md:items-center">
            <div className="truncate rounded-md border border-info-border bg-info-soft px-2 py-1 text-xs font-semibold text-info-text" title={String(row[sourceKey] ?? "Unknown")}>{String(row[sourceKey] ?? "Unknown")}</div>
            <div className="relative h-7 rounded-full bg-surface-muted">
              <div className="h-7 rounded-full bg-gradient-to-r from-primary to-secondary" style={{ width }} />
              <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-ink">{value}</div>
            </div>
            <div className="truncate rounded-md border border-primary/25 bg-primary-soft-2 px-2 py-1 text-xs font-semibold text-primary-active" title={String(row[targetKey] ?? "Unknown")}>{String(row[targetKey] ?? "Unknown")}</div>
          </button>
        );
      })}
    </div>
  );
}
