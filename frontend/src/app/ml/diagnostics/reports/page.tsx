"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, ArrowLeft, BarChart3, Download, ExternalLink, Package, Printer, RotateCcw, Search, Tags, Trash2 } from "lucide-react";

import { Card, CardHeader, EmptyState, Input, Select, StatusBadge, Button } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { MLDiagnosticsReportRecord } from "@/lib/types";

type QueryValue = string | number | boolean | null | undefined;

export default function DiagnosticsReportLibraryPage() {
  return (
    <Suspense fallback={<div className="page-shell"><EmptyState title="Loading report library" /></div>}>
      <ReportLibrary />
    </Suspense>
  );
}

function ReportLibrary() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const search = useSearchParams();
  const [selected, setSelected] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const page = Number(search.get("page") || "1");
  const pageSize = Number(search.get("page_size") || "12");
  const query = Object.fromEntries(search.entries());
  const params = useMemo(() => ({
    q: query.q || "",
    target: query.target || "",
    model: query.model || "",
    template: query.template || "",
    pdf_status: query.pdf_status || "",
    status: query.status || "active",
    tag: query.tag || "",
    include_trashed: query.status === "trashed",
    date_from: query.date_from || "",
    date_to: query.date_to || "",
    sort_by: query.sort_by || "created_at",
    sort_order: query.sort_order || "desc",
    page,
    page_size: pageSize,
  }), [query.q, query.target, query.model, query.template, query.pdf_status, query.status, query.tag, query.date_from, query.date_to, query.sort_by, query.sort_order, page, pageSize]);
  const reports = useQuery({ queryKey: ["ml-diagnostics-report-library", params], queryFn: () => api.mlDiagnosticsReports(params), refetchInterval: 15000 });
  const items = reports.data?.items ?? [];
  const total = reports.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const update = (changes: Record<string, QueryValue>) => {
    const next = new URLSearchParams(search.toString());
    Object.entries(changes).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") next.set(key, String(value));
      else next.delete(key);
    });
    if (!("page" in changes)) next.set("page", "1");
    router.replace(`/ml/diagnostics/reports?${next.toString()}`);
  };
  const toggle = (id: string) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : current.length >= 5 ? current : [...current, id]);
  const compareHref = `/ml/diagnostics/reports/compare?ids=${encodeURIComponent(selected.join(","))}`;
  const bulkAction = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.mlDiagnosticsReportsBulk(body),
    onSuccess: async () => {
      setSelected([]);
      await queryClient.invalidateQueries({ queryKey: ["ml-diagnostics-report-library"] });
    },
  });
  const bulkExport = useMutation({
    mutationFn: () => api.mlDiagnosticsReportsBulkExport({ ids: selected, formats: ["html", "pdf", "xlsx", "json", "manifest"] }),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `diagnostics-reports-${selected.length}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
  });
  const tags = tagInput.split(",").map((item) => item.trim()).filter(Boolean);
  const runBulk = (action: string, actionTags: string[] = []) => bulkAction.mutate({ action, ids: selected, tags: actionTags });

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3" data-tour-id="reports-overview">
        <div>
          <Link href="/ml/diagnostics" className="mb-3 inline-flex items-center gap-2 text-sm font-semibold text-primary-active"><ArrowLeft className="h-4 w-4" />Diagnostics Workbench</Link>
          <h1 className="text-2xl font-semibold text-ink">{t("page.reports.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("page.reports.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={compareHref} aria-disabled={selected.length < 2} className={`inline-flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold ${selected.length >= 2 ? "bg-primary text-white" : "pointer-events-none bg-surface-muted text-muted"}`}>
            <BarChart3 className="h-4 w-4" />
            Compare {selected.length || ""}
          </Link>
        </div>
      </div>

      {selected.length ? (
        <Card tone="magenta">
          <CardHeader eyebrow="Bulk Actions" title={`${selected.length} selected reports`} action={<Package className="h-5 w-5 text-[var(--module-ml)]" />} />
          <div className="grid gap-3 lg:grid-cols-[1fr_auto]">
            <Input value={tagInput} onChange={(event) => setTagInput(event.target.value)} placeholder="tags, comma separated" />
            <div className="flex flex-wrap gap-2">
              <Button disabled={bulkExport.isPending} onClick={() => bulkExport.mutate()}><Package className="h-4 w-4" />Bulk ZIP</Button>
              <Button variant="secondary" disabled={bulkAction.isPending} onClick={() => runBulk("archive")}><Archive className="h-4 w-4" />Archive</Button>
              <Button variant="secondary" disabled={bulkAction.isPending} onClick={() => runBulk("trash")}><Trash2 className="h-4 w-4" />Move to trash</Button>
              <Button variant="secondary" disabled={bulkAction.isPending} onClick={() => runBulk("restore")}><RotateCcw className="h-4 w-4" />Restore</Button>
              <Button variant="secondary" disabled={!tags.length || bulkAction.isPending} onClick={() => runBulk("add_tags", tags)}><Tags className="h-4 w-4" />Add tags</Button>
              <Button variant="secondary" disabled={!tags.length || bulkAction.isPending} onClick={() => runBulk("remove_tags", tags)}>Remove tags</Button>
            </div>
          </div>
          {bulkAction.error || bulkExport.error ? <p className="mt-3 text-sm text-danger-text">{String((bulkAction.error || bulkExport.error)?.message)}</p> : null}
        </Card>
      ) : null}

      <Card tone="primary">
        <CardHeader eyebrow="Filters" title="Artifact search" action={<Search className="h-5 w-5 text-primary-active" />} />
        <div className="grid gap-3 md:grid-cols-4">
          <Input value={query.q || ""} onChange={(event) => update({ q: event.target.value })} placeholder="Search title, ID, model..." />
          <Select value={query.target || ""} onChange={(event) => update({ target: event.target.value })}>
            <option value="">All targets</option>
            <option value="category">Category</option>
            <option value="source">Source</option>
            <option value="sentiment">Sentiment</option>
          </Select>
          <Select value={query.model || ""} onChange={(event) => update({ model: event.target.value })}>
            <option value="">All models</option>
            <option value="logistic_regression">Logistic Regression</option>
            <option value="linear_svm">Linear SVM</option>
            <option value="naive_bayes">Naive Bayes</option>
            <option value="decision_tree">Decision Tree</option>
            <option value="random_forest">Random Forest</option>
          </Select>
          <Select value={query.pdf_status || ""} onChange={(event) => update({ pdf_status: event.target.value })}>
            <option value="">All PDF states</option>
            <option value="not_generated">Not generated</option>
            <option value="ready">Ready</option>
            <option value="fallback_html">Fallback HTML</option>
            <option value="error">Error</option>
          </Select>
          <Select value={query.status || "active"} onChange={(event) => update({ status: event.target.value })}>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="trashed">Trash</option>
          </Select>
          <Input value={query.tag || ""} onChange={(event) => update({ tag: event.target.value })} placeholder="filter by tag" />
          <Input type="date" value={query.date_from || ""} onChange={(event) => update({ date_from: event.target.value })} />
          <Input type="date" value={query.date_to || ""} onChange={(event) => update({ date_to: event.target.value })} />
          <Select value={query.sort_by || "created_at"} onChange={(event) => update({ sort_by: event.target.value })}>
            <option value="created_at">Created</option>
            <option value="report_title">Title</option>
            <option value="accuracy">Accuracy</option>
            <option value="f1_macro">Macro F1</option>
            <option value="error_samples">Error Samples</option>
          </Select>
          <Select value={query.sort_order || "desc"} onChange={(event) => update({ sort_order: event.target.value })}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </Select>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        {items.length ? items.map((report) => (
          <ReportCard key={report.report_id} report={report} selected={selected.includes(report.report_id)} onToggle={() => toggle(report.report_id)} onAction={(action) => bulkAction.mutate({ action, ids: [report.report_id] })} />
        )) : (
          <div className="lg:col-span-3"><EmptyState title={reports.isLoading ? "Loading reports" : "No reports found"} detail="Run a diagnostics report job or clear filters to populate this library." /></div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface p-3 text-sm text-muted">
        <div>Showing {items.length} of {total} reports · Page {page} / {totalPages}</div>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={page <= 1} onClick={() => update({ page: page - 1 })}>Previous</Button>
          <Button variant="secondary" disabled={page >= totalPages} onClick={() => update({ page: page + 1 })}>Next</Button>
        </div>
      </div>
    </div>
  );
}

function ReportCard({ report, selected, onToggle, onAction }: { report: MLDiagnosticsReportRecord; selected: boolean; onToggle: () => void; onAction: (action: string) => void }) {
  const target = String(report.params?.target ?? "-");
  const model = String(report.params?.model ?? "-");
  return (
    <Card tone={selected ? "magenta" : "secondary"}>
      <CardHeader
        eyebrow={report.template}
        title={report.report_title}
        action={<input type="checkbox" checked={selected} onChange={onToggle} aria-label={`Select ${report.report_id}`} />}
      />
      <div className="space-y-3 text-sm">
        <div className="break-all font-semibold text-ink">{report.report_id}</div>
        <div className="numeric text-xs text-muted">{report.created_at || "No timestamp"}</div>
        <div className="flex flex-wrap gap-2">
          <StatusBadge status={report.status} />
          <StatusBadge status={report.pdf_status} />
          <span className="rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs font-semibold text-muted">{target}</span>
          <span className="rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs font-semibold text-muted">{model}</span>
        </div>
        {report.tags.length ? (
          <div className="flex flex-wrap gap-1">
            {report.tags.map((tag) => <span key={tag} className="rounded-full border border-info-border bg-info-soft px-2 py-0.5 text-xs font-semibold text-info-text">{tag}</span>)}
          </div>
        ) : null}
        {report.pdf_fallback_reason ? <p className="rounded-md border border-warn-border bg-warn-soft p-2 text-xs leading-5 text-warn-text">PDF fallback: {report.pdf_fallback_reason}</p> : null}
        <div className="grid grid-cols-3 gap-2 border-y border-line py-3">
          <Metric label="Accuracy" value={report.summary_metrics.accuracy} />
          <Metric label="Macro F1" value={report.summary_metrics.f1_macro} />
          <Metric label="Errors" value={report.row_counts.error_samples} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={api.mlDiagnosticsReportDetailUrl(report.report_id)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 font-semibold text-ink"><ExternalLink className="h-4 w-4" />Detail</Link>
          <a href={api.mlDiagnosticsReportPreviewUrl(report.report_id)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 font-semibold text-ink"><Printer className="h-4 w-4" />Print</a>
          <DownloadLink id={report.report_id} format="pdf" label="PDF" />
          <DownloadLink id={report.report_id} format="xlsx" label="Excel" />
          <DownloadLink id={report.report_id} format="json" label="JSON" />
          {report.status === "trashed" ? (
            <button type="button" onClick={() => onAction("restore")} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 font-semibold text-ink"><RotateCcw className="h-4 w-4" />Restore</button>
          ) : (
            <>
              <button type="button" onClick={() => onAction("archive")} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 font-semibold text-ink"><Archive className="h-4 w-4" />Archive</button>
              <button type="button" onClick={() => onAction("trash")} className="inline-flex items-center gap-2 rounded-md border border-danger-border bg-danger-soft px-3 py-2 font-semibold text-danger-text"><Trash2 className="h-4 w-4" />Trash</button>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className="numeric mt-1 text-lg font-semibold text-ink">{value === undefined || value === null ? "-" : String(value)}</div>
    </div>
  );
}

function DownloadLink({ id, format, label }: { id: string; format: string; label: string }) {
  return (
    <a href={api.mlDiagnosticsReportDownloadUrl(id, format)} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
      <Download className="h-4 w-4" />
      {label}
    </a>
  );
}
