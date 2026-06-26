"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, ExternalLink, Printer } from "lucide-react";

import { Card, CardHeader, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

type Row = Record<string, string | number | boolean | null | undefined>;

export default function DiagnosticsReportDetailPage() {
  const params = useParams<{ id: string }>();
  const reportId = decodeURIComponent(params.id);
  const report = useQuery({ queryKey: ["ml-diagnostics-report", reportId], queryFn: () => api.mlDiagnosticsReport(reportId) });
  const previewHtml = useQuery({
    queryKey: ["ml-diagnostics-report-preview", report.data?.report_id],
    queryFn: () => api.mlDiagnosticsReportPreviewHtml(report.data!.report_id),
    enabled: Boolean(report.data?.report_id),
  });

  if (report.isLoading) {
    return <div className="page-shell"><EmptyState title="Loading diagnostics report" /></div>;
  }

  if (!report.data) {
    return <div className="page-shell"><EmptyState title="Report not found" detail="The report artifact may have been deleted or moved." /></div>;
  }

  const data = report.data;
  const previewUrl = api.mlDiagnosticsReportPreviewUrl(data.report_id);
  const metricRows = Object.entries(data.summary_metrics ?? {}).map(([metric, value]) => ({ metric, value: String(value) }));
  const countRows = Object.entries(data.row_counts ?? {}).map(([name, value]) => ({ name, value }));
  const sectionRows = (data.sections ?? []).map((section) => ({ section, status: data.section_status?.[section] ?? "unknown" }));

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/ml/diagnostics" className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-primary-active"><ArrowLeft className="h-4 w-4" />Diagnostics Workbench</Link>
          <h1 className="text-2xl font-semibold text-ink">{data.report_title}</h1>
          <p className="mt-1 text-sm text-muted">{data.report_id} · {data.template} · {data.sections.length} sections</p>
        </div>
        <StatusBadge status="ready" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <Card tone="primary">
            <CardHeader eyebrow="Artifact" title="Report metadata" />
            <dl className="space-y-3 text-sm">
              <Meta label="Created" value={data.created_at || "-"} />
              <Meta label="Prepared for" value={data.prepared_for || "-"} />
              <Meta label="Job ID" value={String(data.job_id ?? "-")} />
              <Meta label="Template" value={data.template} />
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              <a href={previewUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Printer className="h-4 w-4" />Print View</a>
              <DownloadLink id={data.report_id} format="pdf" label="PDF" />
              <DownloadLink id={data.report_id} format="html" label="HTML" />
              <DownloadLink id={data.report_id} format="markdown" label="Markdown" />
              <DownloadLink id={data.report_id} format="xlsx" label="Excel" />
              <DownloadLink id={data.report_id} format="json" label="JSON" />
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-muted">
              <span>PDF status</span>
              <StatusBadge status={data.pdf_status} />
              {data.pdf_fallback_reason ? <span className="text-warn-text">Fallback: {data.pdf_fallback_reason}</span> : null}
            </div>
          </Card>

          <Card>
            <CardHeader eyebrow="Metrics" title="Summary metrics" />
            <SimpleTable rows={metricRows} />
          </Card>

          <Card>
            <CardHeader eyebrow="Rows" title="Exported row counts" />
            <SimpleTable rows={countRows} />
          </Card>

          <Card tone="secondary">
            <CardHeader eyebrow="Sections" title="Section status" />
            <SimpleTable rows={sectionRows} />
          </Card>
        </div>

        <Card className="min-h-[760px]" tone="secondary">
          <CardHeader
            eyebrow="Preview"
            title="Print-ready HTML"
            action={<a href={previewUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink"><ExternalLink className="h-4 w-4" />Open</a>}
          />
          {previewHtml.isLoading ? (
            <EmptyState title="Loading report preview" detail="Preparing the print-ready HTML preview." />
          ) : previewHtml.data ? (
            <iframe title="Diagnostics report preview" srcDoc={previewHtml.data} className="h-[680px] w-full rounded-md border border-line bg-white" />
          ) : (
            <EmptyState title="Preview unavailable" detail="Open the print view to inspect the generated HTML report." />
          )}
        </Card>
      </div>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3">
      <dt className="font-semibold text-muted">{label}</dt>
      <dd className="break-words text-ink">{value}</dd>
    </div>
  );
}

function DownloadLink({ id, format, label }: { id: string; format: string; label: string }) {
  return (
    <a href={api.mlDiagnosticsReportDownloadUrl(id, format)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink">
      <Download className="h-4 w-4" />
      {label}
    </a>
  );
}

function SimpleTable({ rows }: { rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  if (!rows.length) return <EmptyState title="No data" />;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-line text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-muted">{headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, index) => (
            <tr key={index}>{headers.map((header) => <td key={header} className="px-3 py-2 text-muted">{String(row[header] ?? "")}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
