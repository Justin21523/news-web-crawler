"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, ExternalLink } from "lucide-react";

import { Card, CardHeader, EmptyState, StatusBadge } from "@/components/ui";
import { MetricComparisonChart } from "@/components/charts";
import { api } from "@/lib/api";

type Row = Record<string, string | number | boolean | null | undefined>;

export default function DiagnosticsReportComparePage() {
  return (
    <Suspense fallback={<div className="page-shell"><EmptyState title="Loading report comparison" /></div>}>
      <ReportComparison />
    </Suspense>
  );
}

function ReportComparison() {
  const search = useSearchParams();
  const ids = search.get("ids") || "";
  const comparison = useQuery({
    queryKey: ["ml-diagnostics-report-compare", ids],
    queryFn: () => api.mlDiagnosticsReportsCompare({ ids }),
    enabled: ids.split(",").filter(Boolean).length >= 2,
  });
  const data = comparison.data;
  const metrics = (data?.metrics ?? []) as Row[];
  const chartRows = metrics.map((row) => ({
    report_id: String(row.report_id ?? "").slice(-8),
    accuracy: Number(row.accuracy ?? 0),
    f1_macro: Number(row.f1_macro ?? 0),
  }));

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/ml/diagnostics/reports" className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-primary-active"><ArrowLeft className="h-4 w-4" />Report Library</Link>
          <h1 className="text-2xl font-semibold text-ink">Diagnostics Report Comparison</h1>
          <p className="mt-1 text-sm text-muted">Compare report artifacts against the first selected baseline.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {ids ? (
            <>
              <a href={api.mlDiagnosticsReportsCompareDownloadUrl({ ids, format: "html" })} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink"><Download className="h-4 w-4" />Export HTML</a>
              <a href={api.mlDiagnosticsReportsCompareDownloadUrl({ ids, format: "pdf" })} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Download className="h-4 w-4" />Export PDF</a>
            </>
          ) : null}
          <StatusBadge status={data?.baseline_report_id ? "ready" : "pending"} />
        </div>
      </div>

      {!ids || ids.split(",").filter(Boolean).length < 2 ? (
        <EmptyState title="Select at least two reports" detail="Go back to the report library and choose two to five artifacts for comparison." />
      ) : comparison.isLoading ? (
        <EmptyState title="Loading comparison" />
      ) : data ? (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            {data.items.map((report) => (
              <Card key={report.report_id} tone={report.report_id === data.baseline_report_id ? "primary" : "secondary"}>
                <CardHeader eyebrow={report.report_id === data.baseline_report_id ? "Baseline" : report.template} title={report.report_title} />
                <div className="space-y-2 text-sm">
                  <div className="break-all font-semibold text-ink">{report.report_id}</div>
                  <div className="text-muted">{report.created_at}</div>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge status={report.pdf_status} />
                    <span className="rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs font-semibold text-muted">{String(report.params.target ?? "-")}</span>
                    <span className="rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs font-semibold text-muted">{String(report.params.model ?? "-")}</span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-2">
                    <Link href={api.mlDiagnosticsReportDetailUrl(report.report_id)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 font-semibold text-ink"><ExternalLink className="h-4 w-4" />Detail</Link>
                    <a href={api.mlDiagnosticsReportDownloadUrl(report.report_id, "pdf")} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 font-semibold text-white"><Download className="h-4 w-4" />PDF</a>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <Card tone="primary">
              <CardHeader eyebrow="Metrics" title="Accuracy / Macro F1" />
              <MetricComparisonChart data={chartRows} labelKey="report_id" metrics={[{ key: "accuracy", label: "Accuracy" }, { key: "f1_macro", label: "Macro F1" }]} />
            </Card>
            <Table title="Metric deltas" rows={data.metric_deltas as Row[]} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Table title="Row count deltas" rows={data.row_count_deltas as Row[]} />
            <Table title="Failure summaries" rows={data.failure_summary as Row[]} />
          </div>

          <Table title="Section availability matrix" rows={data.section_matrix as Row[]} />
          {data.notes.length ? <Card tone="warning"><CardHeader eyebrow="Notes" title="Comparison notes" /><ul className="list-disc space-y-2 pl-5 text-sm text-muted">{data.notes.map((note) => <li key={note}>{note}</li>)}</ul></Card> : null}
        </>
      ) : (
        <EmptyState title="Comparison unavailable" detail={comparison.error ? String(comparison.error.message) : "No comparison data returned."} />
      )}
    </div>
  );
}

function Table({ title, rows }: { title: string; rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const hasLongSummary = headers.includes("summary");
  return (
    <Card>
      <CardHeader eyebrow="Table" title={title} />
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className={`${hasLongSummary ? "min-w-[760px]" : "min-w-full"} divide-y divide-line text-sm`}>
            <thead><tr className="text-left text-xs uppercase tracking-wide text-muted">{headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}</tr></thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, 120).map((row, index) => (
                <tr key={index}>{headers.map((header) => <td key={header} className={`px-3 py-2 text-muted ${header === "summary" ? "min-w-[320px] leading-5" : ""}`}>{String(row[header] ?? "")}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState title="No comparison rows" />}
    </Card>
  );
}
