"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Copy, Download, ExternalLink, Eye, FileSpreadsheet, Filter, GripVertical, Play, Printer, X } from "lucide-react";

import { InsightCard } from "@/components/analysis-cards";
import { AdvancedChartCard, HeatmapChart, SankeyChart } from "@/components/advanced-charts";
import { HorizontalBarChart, MetricComparisonChart } from "@/components/charts";
import { Card, CardHeader, EmptyState, Input, Select, StatusBadge, Button } from "@/components/ui";
import { api } from "@/lib/api";
import type { MLArtifactRecord, MLDiagnosticsReportRecord, MLModelName, MLTarget } from "@/lib/types";

type Row = Record<string, string | number | boolean | null | undefined>;

const reportSections = [
  { id: "cover", label: "Cover" },
  { id: "executive_summary", label: "Executive Summary" },
  { id: "metrics", label: "Metrics" },
  { id: "confusion_matrix", label: "Confusion Matrix" },
  { id: "class_quality", label: "Class Quality" },
  { id: "failure_narrative", label: "Failure Narrative" },
  { id: "recommendations", label: "Recommendations" },
  { id: "error_samples", label: "Error Samples" },
  { id: "artifact_comparison", label: "Artifact Comparison" },
  { id: "article_explanations", label: "Article Explanations" },
  { id: "appendix_filters", label: "Filters Appendix" },
  { id: "appendix_predictions", label: "Predictions Appendix" },
];

export default function DiagnosticsPage() {
  return (
    <Suspense fallback={<div className="page-shell"><EmptyState title="Loading diagnostics workbench" /></div>}>
      <DiagnosticsWorkbench />
    </Suspense>
  );
}

function DiagnosticsWorkbench() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const search = useSearchParams();
  const target = (search.get("target") || "source") as MLTarget;
  const model = (search.get("model") || "logistic_regression") as MLModelName;
  const artifactIds = search.get("artifact_ids") || "";
  const actual = search.get("actual") || "";
  const predicted = search.get("predicted") || "";
  const classLabel = search.get("class_label") || "";
  const featureLimit = search.get("feature_limit") || "1000";
  const maxDepth = search.get("max_depth") || "4";
  const page = search.get("page") || "1";
  const selectedIds = artifactIds.split(",").map((item) => item.trim()).filter(Boolean);
  const [reportTitle, setReportTitle] = useState("ML Diagnostics Report");
  const [preparedFor, setPreparedFor] = useState("Portfolio Review");
  const [template, setTemplate] = useState("portfolio");
  const [sectionOrder, setSectionOrder] = useState(reportSections.map((section) => section.id));
  const [enabledSections, setEnabledSections] = useState(reportSections.map((section) => section.id));
  const [draggingSection, setDraggingSection] = useState<string | null>(null);
  const [previewReport, setPreviewReport] = useState<MLDiagnosticsReportRecord | null>(null);
  const sections = sectionOrder.filter((section) => enabledSections.includes(section));

  const update = (changes: Record<string, string>) => {
    const next = new URLSearchParams(search.toString());
    Object.entries(changes).forEach(([key, value]) => {
      if (value) next.set(key, value);
      else next.delete(key);
    });
    router.replace(`/ml/diagnostics?${next.toString()}`);
  };

  const baseParams = useMemo(() => ({ target, model, feature_limit: featureLimit, max_depth: maxDepth, min_class_count: 2, collapse_rare: true }), [target, model, featureLimit, maxDepth]);
  const artifacts = useQuery({ queryKey: ["ml-artifacts", target], queryFn: () => api.mlArtifacts({ target, limit: 50 }), refetchInterval: 10000 });
  const diagnostics = useQuery({ queryKey: ["ml-diagnostics-workbench", baseParams], queryFn: () => api.mlDiagnostics(baseParams), refetchInterval: 30000 });
  const errors = useQuery({
    queryKey: ["ml-diagnostics-errors", baseParams, artifactIds, actual, predicted, classLabel, page],
    queryFn: () => api.mlDiagnosticsErrors({ ...baseParams, artifact_id: selectedIds[0] || "", actual, predicted, class_label: classLabel, page, page_size: 20 }),
    refetchInterval: 30000,
  });
  const comparison = useQuery({
    queryKey: ["ml-artifact-diagnostics-compare", target, artifactIds],
    queryFn: () => api.mlArtifactDiagnosticsCompare({ target, ids: artifactIds }),
    enabled: selectedIds.length > 0,
    refetchInterval: 30000,
  });
  const reports = useQuery({ queryKey: ["ml-diagnostics-reports"], queryFn: () => api.mlDiagnosticsReports({ limit: 10 }), refetchInterval: 10000 });
  const createReport = useMutation({
    mutationFn: () => api.createJob("export_ml_diagnostics_report", {
      target,
      model,
      artifact_ids: selectedIds,
      actual,
      predicted,
      class_label: classLabel,
      feature_limit: Number(featureLimit),
      max_depth: Number(maxDepth),
      limit: 2000,
      explanation_modes: ["linear_coefficients", "tree_path"],
      template,
      sections,
      report_title: reportTitle,
      prepared_for: preparedFor,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["jobs"] }),
        queryClient.invalidateQueries({ queryKey: ["ml-diagnostics-reports"] }),
      ]);
    },
  });

  const artifactOptions = artifacts.data?.items ?? [];
  const classRows = (diagnostics.data?.class_metrics ?? []).map((row) => ({
    label: String(row.label ?? ""),
    precision: Number(row.precision ?? 0),
    recall: Number(row.recall ?? 0),
    f1: Number(row.f1 ?? 0),
    support: Number(row.support ?? 0),
  }));
  const errorRows = errors.data?.items ?? [];
  const labels = diagnostics.data?.labels ?? [];
  const confusionValues = matrixToHeatmapValues(diagnostics.data?.confusion_matrix ?? []);
  const confusionRows = matrixToRows(labels, diagnostics.data?.confusion_matrix ?? []);
  const confusionPairRows = (diagnostics.data?.confusion_pairs ?? []) as Row[];
  const topFeatures = (diagnostics.data?.feature_diagnostics.top_features ?? []) as Row[];
  const lowClassRows = (diagnostics.data?.low_performing_classes ?? []) as Row[];

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Model Diagnostics Workbench</h1>
          <p className="mt-1 text-sm text-muted">Shareable diagnostics, error drill-down, artifact comparison, and explanation-ready model analysis.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/ml/diagnostics/reports" className="inline-flex min-h-10 items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink">
            <FileSpreadsheet className="h-4 w-4" />
            Report Library
          </Link>
          <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(window.location.href)}>
            <Copy className="h-4 w-4" />
            Copy URL
          </Button>
        </div>
      </div>

      <Card tone="primary">
        <CardHeader eyebrow="URL State" title="Diagnostics controls" action={<Filter className="h-5 w-5 text-primary-active" />} />
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Select value={target} onChange={(event) => update({ target: event.target.value, actual: "", predicted: "", class_label: "", page: "1" })}>
            <option value="source">Source</option>
            <option value="category">Category</option>
            <option value="sentiment">Sentiment</option>
          </Select>
          <Select value={model} onChange={(event) => update({ model: event.target.value, page: "1" })}>
            <option value="logistic_regression">Logistic Regression</option>
            <option value="linear_svm">Linear SVM</option>
            <option value="naive_bayes">Naive Bayes</option>
            <option value="decision_tree">Decision Tree</option>
            <option value="random_forest">Random Forest</option>
          </Select>
          <Input type="number" value={featureLimit} onChange={(event) => update({ feature_limit: event.target.value })} />
          <Input type="number" value={maxDepth} onChange={(event) => update({ max_depth: event.target.value })} />
          <Input value={actual} onChange={(event) => update({ actual: event.target.value, page: "1" })} placeholder="actual label" />
          <Input value={predicted} onChange={(event) => update({ predicted: event.target.value, page: "1" })} placeholder="predicted label" />
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr]">
          <Select value={selectedIds[0] ?? ""} onChange={(event) => update({ artifact_ids: mergeArtifactIds(event.target.value, selectedIds.slice(1)), page: "1" })}>
            <option value="">On-demand diagnostics</option>
            {artifactOptions.map((artifact) => <option key={artifact.artifact_id} value={artifact.artifact_id}>{artifact.artifact_id} · {artifact.model}</option>)}
          </Select>
          <ArtifactMultiSelect artifacts={artifactOptions} selected={selectedIds} onChange={(ids) => update({ artifact_ids: ids.join(",") })} />
        </div>
      </Card>

      <Card tone="secondary">
        <CardHeader eyebrow="Report Export" title="Full diagnostics report" action={<FileSpreadsheet className="h-5 w-5 text-info-text" />} />
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <div>
            <div className="space-y-3">
              <Input value={reportTitle} onChange={(event) => setReportTitle(event.target.value)} placeholder="Report title" />
              <Input value={preparedFor} onChange={(event) => setPreparedFor(event.target.value)} placeholder="Prepared for" />
              <Select value={template} onChange={(event) => setTemplate(event.target.value)}>
                <option value="portfolio">Portfolio</option>
                <option value="technical_audit">Technical Audit</option>
                <option value="executive">Executive</option>
              </Select>
            </div>
            <div className="mt-3 rounded-md border border-line bg-surface-muted p-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Report sections</div>
              <div className="space-y-2">
                {sectionOrder.map((sectionId, index) => {
                  const section = reportSections.find((item) => item.id === sectionId) ?? { id: sectionId, label: sectionId };
                  const enabled = enabledSections.includes(section.id);
                  return (
                  <div
                    key={section.id}
                    draggable
                    onDragStart={() => setDraggingSection(section.id)}
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={() => {
                      if (!draggingSection || draggingSection === section.id) return;
                      setSectionOrder((current) => moveTo(current, draggingSection, section.id));
                      setDraggingSection(null);
                    }}
                    className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-2 rounded-md border border-line bg-surface-elevated px-2 py-1.5 text-sm"
                  >
                    <GripVertical className="h-4 w-4 text-muted" />
                    <label className="flex items-center gap-2 text-muted">
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(event) => setEnabledSections((current) => event.target.checked ? [...current, section.id] : current.filter((item) => item !== section.id))}
                    />
                    {section.label}
                  </label>
                    <button type="button" className="text-muted disabled:opacity-30" disabled={index === 0} onClick={() => setSectionOrder((current) => moveByIndex(current, index, index - 1))} aria-label={`Move ${section.label} up`}><ArrowUp className="h-4 w-4" /></button>
                    <button type="button" className="text-muted disabled:opacity-30" disabled={index === sectionOrder.length - 1} onClick={() => setSectionOrder((current) => moveByIndex(current, index, index + 1))} aria-label={`Move ${section.label} down`}><ArrowDown className="h-4 w-4" /></button>
                  </div>
                );})}
              </div>
            </div>
            <Button className="mt-3" disabled={createReport.isPending} onClick={() => createReport.mutate()}>
              <Play className="h-4 w-4" />
              Run Report Job
            </Button>
            <p className="mt-3 text-sm leading-6 text-muted">Exports current filters, full test predictions, error samples, artifact comparison, and article explanations into HTML, Markdown, Excel, and JSON.</p>
            {createReport.error ? <div className="mt-3 text-sm text-danger-text">{String(createReport.error.message)}</div> : null}
          </div>
          <div className="space-y-2">
            {reports.data?.items.length ? reports.data.items.map((report) => (
              <div key={report.report_id} className="rounded-md border border-line bg-surface-elevated p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="font-semibold text-ink">{report.report_id}</div>
                    <div className="numeric mt-1 text-xs text-muted">{report.created_at || "No timestamp"} · {report.template} · {report.sections.length} sections · errors {report.row_counts.error_samples ?? 0} · predictions {report.row_counts.all_predictions ?? 0}</div>
                    <div className="mt-1 text-xs text-muted">{report.report_title}</div>
                  </div>
                  <StatusBadge status="ready" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={() => setPreviewReport(report)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink">
                    <Eye className="h-4 w-4" />
                    Preview
                  </button>
                  <Link href={api.mlDiagnosticsReportDetailUrl(report.report_id)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink">
                    <ExternalLink className="h-4 w-4" />
                    Detail
                  </Link>
                  <a href={api.mlDiagnosticsReportPreviewUrl(report.report_id)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-sm font-semibold text-ink">
                    <Printer className="h-4 w-4" />
                    Print View
                  </a>
                  <ReportDownload id={report.report_id} format="html" label="HTML" />
                  <ReportDownload id={report.report_id} format="markdown" label="Markdown" />
                  <ReportDownload id={report.report_id} format="xlsx" label="Excel" />
                  <ReportDownload id={report.report_id} format="pdf" label="PDF" />
                  <ReportDownload id={report.report_id} format="json" label="JSON" />
                </div>
              </div>
            )) : <EmptyState title={reports.isLoading ? "Loading reports" : "No diagnostics reports"} detail="Run a report job to generate downloadable artifacts." />}
          </div>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Accuracy" metric={String(diagnostics.data?.metrics.accuracy ?? "-")} detail={`${target} / ${model}`} />
        <InsightCard title="Macro F1" metric={String(diagnostics.data?.metrics.f1_macro ?? "-")} detail="Balanced performance signal." />
        <InsightCard title="Error Samples" metric={String(errors.data?.total ?? 0)} detail="Filtered misclassified samples." />
        <InsightCard title="Artifacts" metric={String(comparison.data?.items.length ?? selectedIds.length)} detail="Selected comparison runs." />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <AdvancedChartCard
          eyebrow="Diagnostics"
          title="Confusion heatmap"
          insight="Diagonal cells are correct classifications; off-diagonal cells reveal the most important confusion patterns."
          metric={`${confusionPairRows.length} confusion pairs`}
          rows={confusionRows}
          exportName="ml-confusion-heatmap"
        >
          <HeatmapChart xLabels={labels} yLabels={labels} values={confusionValues} exportName="ml-confusion-heatmap" />
        </AdvancedChartCard>
        <Card tone="warning"><CardHeader eyebrow="Class Quality" title="Precision / Recall / F1" /><MetricComparisonChart data={classRows} labelKey="label" metrics={[{ key: "precision", label: "Precision" }, { key: "recall", label: "Recall" }, { key: "f1", label: "F1" }]} /></Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <AdvancedChartCard
          eyebrow="Error Patterns"
          title="Actual to predicted error flow"
          insight="Thicker flows show repeated misclassification paths and point to label definitions or feature overlap that need review."
          metric={`${confusionPairRows.reduce((sum, row) => sum + Number(row.count ?? 0), 0)} errors`}
          rows={confusionPairRows}
          exportName="ml-error-pattern-flow"
        >
          <SankeyChart rows={confusionPairRows} sourceKey="actual" targetKey="predicted" valueKey="count" exportName="ml-error-pattern-flow" />
        </AdvancedChartCard>
        <Card tone="danger">
          <CardHeader eyebrow="Low-performing Classes" title="Classes needing review" action={<StatusBadge status={lowClassRows.length ? "warning" : "ready"} />} />
          {lowClassRows.length ? (
            <div className="space-y-3">
              {lowClassRows.slice(0, 8).map((row) => (
                <button key={String(row.label)} type="button" onClick={() => update({ class_label: String(row.label ?? ""), page: "1" })} className="block w-full rounded-md border border-danger-border bg-danger-soft p-3 text-left">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-danger-text">{String(row.label ?? "Unknown")}</span>
                    <span className="numeric text-xs font-semibold text-danger-text">F1 {String(row.f1 ?? "-")}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-danger-text/80">{String(row.reason ?? "Review support, precision, recall, and confusion pairs for this class.")}</p>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title="No low-performing classes" detail="Current class-level metrics do not cross the warning threshold." />
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <NarrativePanel title="Model failure factors" rows={(diagnostics.data?.failure_factors ?? []) as Row[]} />
        <NarrativePanel title="Model recommendations" rows={(diagnostics.data?.recommendations ?? []) as Row[]} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card tone="danger">
          <CardHeader eyebrow="Error Drill-down" title="Filtered error samples" action={<StatusBadge status={errors.data?.status ?? "pending"} />} />
          {errorRows.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-line text-sm">
                <thead><tr className="text-left text-xs uppercase tracking-wide text-muted"><th className="px-3 py-2">Article</th><th className="px-3 py-2">Actual</th><th className="px-3 py-2">Predicted</th><th className="px-3 py-2">Confidence</th><th className="px-3 py-2">Open</th></tr></thead>
                <tbody className="divide-y divide-line">
                  {errorRows.map((row, index) => (
                    <tr key={`${String(row.article_id)}-${index}`}>
                      <td className="max-w-sm px-3 py-2 text-ink">{String(row.title ?? row.article_id)}</td>
                      <td className="px-3 py-2 text-muted"><button onClick={() => update({ actual: String(row.actual ?? ""), page: "1" })}>{String(row.actual ?? "")}</button></td>
                      <td className="px-3 py-2 text-muted"><button onClick={() => update({ predicted: String(row.predicted ?? ""), page: "1" })}>{String(row.predicted ?? "")}</button></td>
                      <td className="numeric px-3 py-2 text-muted">{String(row.confidence ?? "-")}</td>
                      <td className="px-3 py-2"><Link className="text-primary-active" href={`/articles/${encodeURIComponent(String(row.article_id))}`}><ExternalLink className="h-4 w-4" /></Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <EmptyState title={errors.isLoading ? "Loading error samples" : "No error samples"} detail="Try clearing actual/predicted filters or retrain a persisted artifact." />}
        </Card>
        <AdvancedChartCard
          eyebrow="Features"
          title="Top diagnostic features"
          insight="Feature weights identify terms that most strongly influence the current model and help explain fragile predictions."
          metric={`${topFeatures.length} features`}
          rows={topFeatures}
          exportName="ml-top-diagnostic-features"
        >
          <HorizontalBarChart data={topFeatures} labelKey="feature" valueKey="weight" />
        </AdvancedChartCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Artifact metric deltas" rows={(comparison.data?.metric_deltas ?? []) as Row[]} />
        <Table title="Artifact class deltas" rows={(comparison.data?.class_deltas ?? []) as Row[]} />
      </div>
      {previewReport ? <ReportPreviewModal report={previewReport} onClose={() => setPreviewReport(null)} /> : null}
    </div>
  );
}

function ReportPreviewModal({ report, onClose }: { report: MLDiagnosticsReportRecord; onClose: () => void }) {
  const previewUrl = api.mlDiagnosticsReportPreviewUrl(report.report_id);
  const previewHtml = useQuery({
    queryKey: ["ml-diagnostics-report-preview", report.report_id],
    queryFn: () => api.mlDiagnosticsReportPreviewHtml(report.report_id),
  });

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/55 p-3 md:p-6" role="dialog" aria-modal="true" aria-label="Report preview">
      <div className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden rounded-lg border border-line bg-surface shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
          <div>
            <div className="text-sm font-semibold text-ink">{report.report_title}</div>
            <div className="numeric text-xs text-muted">{report.report_id} · {report.sections.length} sections</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <a href={previewUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Printer className="h-4 w-4" />Print View</a>
            <Link href={api.mlDiagnosticsReportDetailUrl(report.report_id)} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink"><ExternalLink className="h-4 w-4" />Detail</Link>
            <button type="button" onClick={onClose} className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink"><X className="h-4 w-4" />Close</button>
          </div>
        </div>
        {previewHtml.isLoading ? (
          <div className="min-h-0 flex-1 bg-white p-6"><EmptyState title="Loading report preview" detail="Preparing the print-ready HTML preview." /></div>
        ) : previewHtml.data ? (
          <iframe title="Diagnostics report preview" srcDoc={previewHtml.data} className="min-h-0 flex-1 bg-white" />
        ) : (
          <div className="min-h-0 flex-1 bg-white p-6"><EmptyState title="Preview unavailable" detail="Open the print view to inspect the generated HTML report." /></div>
        )}
      </div>
    </div>
  );
}

function ReportDownload({ id, format, label }: { id: string; format: string; label: string }) {
  return (
    <a href={api.mlDiagnosticsReportDownloadUrl(id, format)} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
      <Download className="h-4 w-4" />
      {label}
    </a>
  );
}

function ArtifactMultiSelect({ artifacts, selected, onChange }: { artifacts: MLArtifactRecord[]; selected: string[]; onChange: (ids: string[]) => void }) {
  return (
    <Select value="" onChange={(event) => {
      const value = event.target.value;
      if (!value) return;
      onChange(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
    }}>
      <option value="">{selected.length ? `Comparing ${selected.length} artifacts` : "Add artifact to comparison"}</option>
      {artifacts.map((artifact) => <option key={artifact.artifact_id} value={artifact.artifact_id}>{selected.includes(artifact.artifact_id) ? "Remove" : "Add"} {artifact.artifact_id}</option>)}
    </Select>
  );
}

function moveByIndex(items: string[], from: number, to: number) {
  if (to < 0 || to >= items.length) return items;
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

function moveTo(items: string[], moving: string, target: string) {
  const from = items.indexOf(moving);
  const to = items.indexOf(target);
  if (from < 0 || to < 0) return items;
  return moveByIndex(items, from, to);
}

function mergeArtifactIds(primary: string, rest: string[]): string {
  return [primary, ...rest.filter((item) => item !== primary)].filter(Boolean).join(",");
}

function NarrativePanel({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <Card>
      <CardHeader eyebrow="Narrative" title={title} />
      {rows.length ? (
        <div className="space-y-3">
          {rows.map((row, index) => (
            <div key={`${String(row.title ?? row.factor ?? index)}-${index}`} className="rounded-md border border-line bg-surface-subtle p-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="font-semibold text-ink">{String(row.title ?? row.factor ?? row.label ?? `Finding ${index + 1}`)}</div>
                {row.severity || row.impact ? <StatusBadge status={String(row.severity ?? row.impact)} /> : null}
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">{String(row.detail ?? row.reason ?? row.recommendation ?? "Review diagnostics before using this model for production decisions.")}</p>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No narrative items" detail="Run diagnostics or train a persisted artifact to generate model-specific guidance." />
      )}
    </Card>
  );
}

function matrixToHeatmapValues(matrix: number[][]): Array<[number, number, number]> {
  return matrix.flatMap((row, y) => row.map((value, x) => [x, y, Number(value || 0)] as [number, number, number]));
}

function matrixToRows(labels: string[], matrix: number[][]): Row[] {
  return matrix.flatMap((row, y) =>
    row.map((value, x) => ({
      actual: labels[y] ?? String(y),
      predicted: labels[x] ?? String(x),
      count: value,
      correct: x === y,
    })),
  );
}

function Table({ title, rows }: { title: string; rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 7);
  return <Card><CardHeader eyebrow="Table" title={title} />{rows.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-line text-sm"><thead><tr className="text-left text-xs uppercase tracking-wide text-muted">{headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}</tr></thead><tbody className="divide-y divide-line">{rows.slice(0, 30).map((row, index) => <tr key={index}>{headers.map((header) => <td key={header} className="px-3 py-2 text-muted">{String(row[header] ?? "")}</td>)}</tr>)}</tbody></table></div> : <EmptyState title="No table data" />}</Card>;
}
