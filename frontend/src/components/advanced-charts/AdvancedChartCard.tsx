"use client";

import { useRef } from "react";
import { Download, X } from "lucide-react";

import { DataTable } from "@/components/data-display";
import { Button, Card, CardHeader } from "@/components/ui";
import { type ChartDatum, downloadText, rowsToCsv } from "@/components/advanced-charts/chart-theme";
import { downloadNodeImage } from "@/components/advanced-charts/chart-export";

export function AdvancedChartCard({
  eyebrow = "Visualization",
  title,
  insight,
  metric,
  children,
  rows = [],
  exportName,
  tableTitle = "Drill-down",
  selectedSummary,
  onClearSelection,
}: {
  eyebrow?: string;
  title: string;
  insight: string;
  metric?: string | number;
  children: React.ReactNode;
  rows?: ChartDatum[];
  exportName: string;
  tableTitle?: string;
  selectedSummary?: string;
  onClearSelection?: () => void;
}) {
  const chartRef = useRef<HTMLDivElement | null>(null);
  return (
    <Card data-testid={`advanced-chart-${exportName}`}>
      <CardHeader
        eyebrow={eyebrow}
        title={title}
        action={
          <div className="flex flex-wrap gap-2">
            {metric !== undefined ? (
              <span className="numeric rounded-md border border-info-border bg-info-soft px-2.5 py-1 text-xs font-semibold text-info-text">
                {metric}
              </span>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              className="min-h-8 px-2 py-1 text-xs"
              data-testid={`chart-export-png-${exportName}`}
              onClick={() => downloadNodeImage(chartRef.current, exportName, "png")}
            >
              <Download className="h-3.5 w-3.5" />
              PNG
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="min-h-8 px-2 py-1 text-xs"
              data-testid={`chart-export-svg-${exportName}`}
              onClick={() => downloadNodeImage(chartRef.current, exportName, "svg")}
            >
              SVG
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="min-h-8 px-2 py-1 text-xs"
              disabled={!rows.length}
              onClick={() => downloadText(`${exportName}.csv`, rowsToCsv(rows), "text/csv")}
            >
              CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="min-h-8 px-2 py-1 text-xs"
              disabled={!rows.length}
              onClick={() => downloadText(`${exportName}.json`, JSON.stringify(rows, null, 2), "application/json")}
            >
              JSON
            </Button>
          </div>
        }
      />
      <p className="mb-4 text-sm leading-6 text-muted">{insight}</p>
      {selectedSummary ? (
        <div className="mb-4 flex flex-wrap items-center gap-2 rounded-md border border-primary/25 bg-primary-soft-2 px-3 py-2 text-sm text-primary-active">
          <span className="font-semibold">Selected:</span>
          <span>{selectedSummary}</span>
          {onClearSelection ? (
            <button type="button" className="ml-auto inline-flex items-center gap-1 text-xs font-semibold" onClick={onClearSelection}>
              <X className="h-3.5 w-3.5" />
              Clear
            </button>
          ) : null}
        </div>
      ) : null}
      <div ref={chartRef}>
        {children}
      </div>
      {rows.length ? (
        <div className="mt-5 border-t border-line pt-4">
          <DataTable title={tableTitle} rows={rows} limit={10} maxColumns={8} />
        </div>
      ) : null}
    </Card>
  );
}
