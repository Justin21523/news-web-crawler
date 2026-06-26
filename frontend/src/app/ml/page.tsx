"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Play } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { InsightCard } from "@/components/analysis-cards";
import { HeatmapMatrix, HorizontalBarChart, MetricComparisonChart } from "@/components/charts";
import { ScrollableTabs } from "@/components/data-display";
import { Button, Card, CardHeader, EmptyState, Input, Select, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import type { DecisionTreeResponse, MLArtifactListResponse, MLCompareResponse, MLDatasetResponse, MLDiagnosticsResponse, MLOverviewResponse, MLTarget, MLTrainResponse } from "@/lib/types";

const tabs = [
  { key: "overview", label: "Overview" },
  { key: "dataset", label: "Dataset" },
  { key: "comparison", label: "Model Comparison" },
  { key: "diagnostics", label: "Diagnostics" },
  { key: "category", label: "Category" },
  { key: "source", label: "Source" },
  { key: "sentiment", label: "Sentiment" },
  { key: "tree", label: "Decision Tree" },
  { key: "artifacts", label: "Saved Artifacts" },
] as const;

type TabKey = typeof tabs[number]["key"];
type Row = Record<string, string | number | boolean | null | undefined>;

export default function MLPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [active, setActive] = useState<TabKey>("overview");
  const [target, setTarget] = useState<MLTarget>("source");
  const [model, setModel] = useState("logistic_regression");
  const [featureLimit, setFeatureLimit] = useState("1000");
  const [maxDepth, setMaxDepth] = useState("4");
  const [articleId, setArticleId] = useState("");

  const baseParams = useMemo(() => ({ target, feature_limit: featureLimit, min_class_count: 2, collapse_rare: true }), [target, featureLimit]);
  const treeParams = useMemo(() => ({ ...baseParams, max_depth: maxDepth, model: "decision_tree" }), [baseParams, maxDepth]);

  const overview = useQuery({ queryKey: ["ml-overview"], queryFn: () => api.mlOverview({}), refetchInterval: 30000 });
  const dataset = useQuery({ queryKey: ["ml-dataset", target], queryFn: () => api.mlDataset({ target }), refetchInterval: 30000 });
  const train = useQuery({ queryKey: ["ml-train", baseParams, model], queryFn: () => api.mlTrain({ ...baseParams, model }), refetchInterval: 30000 });
  const compare = useQuery({ queryKey: ["ml-compare", target, featureLimit], queryFn: () => api.mlCompare(baseParams), refetchInterval: 30000 });
  const diagnostics = useQuery({ queryKey: ["ml-diagnostics", target, model, featureLimit, maxDepth], queryFn: () => api.mlDiagnostics(model === "decision_tree" ? treeParams : { ...baseParams, model }), refetchInterval: 30000 });
  const tree = useQuery({ queryKey: ["ml-tree", treeParams], queryFn: () => api.mlDecisionTree(treeParams), refetchInterval: 30000 });
  const artifacts = useQuery({ queryKey: ["ml-artifacts"], queryFn: () => api.mlArtifacts({ limit: 50 }), refetchInterval: 10000 });
  const selectedArticleId = articleId || String(dataset.data?.sample_rows?.[0]?.article_id ?? "");
  const path = useQuery({
    queryKey: ["ml-tree-path", treeParams, selectedArticleId],
    queryFn: () => api.mlDecisionPath({ ...treeParams, article_id: selectedArticleId }),
    enabled: Boolean(selectedArticleId),
    refetchInterval: 30000,
  });
  const createTrainingJob = useMutation({
    mutationFn: () => api.createJob(model === "decision_tree" ? "train_decision_tree" : "train_ml", model === "decision_tree" ? treeParams : { ...baseParams, model }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
      await queryClient.invalidateQueries({ queryKey: ["ml-artifacts"] });
      setActive("artifacts");
    },
  });

  const effectiveTarget: MLTarget = active === "category" || active === "source" || active === "sentiment" ? active : target;

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3" data-tour-id="ml-overview">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{t("page.ml.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("page.ml.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={createTrainingJob.isPending} onClick={() => createTrainingJob.mutate()}>
            <Play className="h-4 w-4" />
            Run Training Job
          </Button>
          <Link href={`/ml/diagnostics?target=${target}&model=${model}&feature_limit=${featureLimit}&max_depth=${maxDepth}`} className="inline-flex items-center gap-2 rounded-md bg-secondary px-3 py-2 text-sm font-semibold text-white">
            Diagnostics Workbench
          </Link>
          <ExportButton href={api.mlExportUrl({ ...baseParams, model, section: "metrics", format: "json" })} label="Metrics JSON" />
          <ExportButton href={api.mlExportUrl({ ...treeParams, section: "feature_importance", format: "csv" })} label="Features CSV" />
          <ExportButton href={api.mlExportUrl({ ...treeParams, section: "tree_image", format: "svg" })} label="Tree SVG" />
        </div>
      </div>
      {createTrainingJob.error ? <div className="rounded-md border border-danger-border bg-danger-soft p-3 text-sm text-danger-text">{String(createTrainingJob.error.message)}</div> : null}

      <Card>
        <CardHeader eyebrow="Controls" title="Model inputs" />
        <div className="grid gap-3 md:grid-cols-5">
          <Select value={target} onChange={(event) => setTarget(event.target.value as MLTarget)}>
            <option value="source">Source</option>
            <option value="category">Category</option>
            <option value="sentiment">Sentiment</option>
          </Select>
          <Select value={model} onChange={(event) => setModel(event.target.value)}>
            <option value="logistic_regression">Logistic Regression</option>
            <option value="linear_svm">Linear SVM</option>
            <option value="naive_bayes">Naive Bayes</option>
            <option value="decision_tree">Decision Tree</option>
            <option value="random_forest">Random Forest</option>
          </Select>
          <Input type="number" min="100" max="30000" value={featureLimit} onChange={(event) => setFeatureLimit(event.target.value)} />
          <Input type="number" min="1" max="30" value={maxDepth} onChange={(event) => setMaxDepth(event.target.value)} />
          <Input value={articleId} onChange={(event) => setArticleId(event.target.value)} placeholder="article_id for path" />
        </div>
      </Card>

      <ScrollableTabs
        tabs={[...tabs]}
        active={active}
        onChange={(key) => {
          setActive(key);
          if (key === "category" || key === "source" || key === "sentiment") setTarget(key);
        }}
      />

      {active === "overview" ? <Overview data={overview.data} loading={overview.isLoading} /> : null}
      {active === "dataset" ? <Dataset data={dataset.data} loading={dataset.isLoading} /> : null}
      {active === "comparison" ? <Comparison data={compare.data} loading={compare.isLoading} /> : null}
      {active === "diagnostics" ? <Diagnostics data={diagnostics.data} loading={diagnostics.isLoading} /> : null}
      {active === "category" || active === "source" || active === "sentiment" ? <Training title={`${effectiveTarget} classification`} data={train.data} loading={train.isLoading} /> : null}
      {active === "tree" ? <DecisionTree data={tree.data} loading={tree.isLoading} imageUrl={api.mlDecisionTreeImageUrl({ ...treeParams, format: "svg" })} pathData={path.data} pathLoading={path.isLoading} /> : null}
      {active === "artifacts" ? <Artifacts data={artifacts.data} loading={artifacts.isLoading} /> : null}
    </div>
  );
}

function Overview({ data, loading }: { data: MLOverviewResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading ML overview" />;
  if (!data) return <EmptyState title="No ML data" detail="Run ingestion before training baseline models." />;
  const rows = Object.entries(data.targets).map(([target, value]) => ({ target, status: value.status, labels: Object.keys(value.prepared_distribution).length, documents: Object.values(value.prepared_distribution).reduce((a, b) => a + b, 0) }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Articles available for ML preparation." />
        <InsightCard title="Targets" metric={String(Object.keys(data.targets).length)} detail="Category, source, and sentiment baselines." />
        <InsightCard title="Ready Targets" metric={String(rows.filter((row) => row.status === "ready").length)} detail="Targets with enough labels for evaluation." />
        <InsightCard title="Mode" metric="On-demand" detail="Models train from the current filtered corpus." />
      </div>
      <Table title="Target readiness" rows={rows} />
      <Notes notes={[...data.notes, ...data.recommended_next_steps]} />
    </div>
  );
}

function Dataset({ data, loading }: { data: MLDatasetResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading ML dataset" />;
  if (!data) return <EmptyState title="No dataset" />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <InsightCard title="Target" metric={data.target} detail="Current supervised label source." />
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Raw documents before label filtering." />
        <InsightCard title="Status" metric={data.status} detail="Readiness for train/test evaluation." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Labels" title="Raw label distribution" /><BarChartBlock data={toChartRows(data.label_distribution)} xKey="name" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Prepared" title="Prepared distribution" /><BarChartBlock data={toChartRows(data.prepared_distribution)} xKey="name" yKey="count" fill="var(--chart-1)" /></Card>
      </div>
      <Table title="Sample rows" rows={data.sample_rows as Row[]} />
      <Notes notes={data.notes} />
    </div>
  );
}

function Comparison({ data, loading }: { data: MLCompareResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Training baseline comparison" />;
  if (!data) return <EmptyState title="No comparison data" />;
  const rows = data.results.map((item) => ({ model: item.model, status: item.status, accuracy: item.metrics.accuracy ?? "-", f1_macro: item.metrics.f1_macro ?? "-", train_seconds: item.timings.training_seconds ?? "-" }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card tone="secondary"><CardHeader eyebrow="Models" title="Metric comparison" /><MetricComparisonChart data={rows} labelKey="model" metrics={[{ key: "accuracy", label: "Accuracy" }, { key: "f1_macro", label: "Macro F1" }]} /></Card>
        <Card tone="primary"><CardHeader eyebrow="Runtime" title="Training time by model" /><HorizontalBarChart data={rows} labelKey="model" valueKey="train_seconds" /></Card>
      </div>
      <Table title="Baseline model comparison" rows={rows} />
      <Notes notes={data.notes} />
    </div>
  );
}

function Diagnostics({ data, loading }: { data: MLDiagnosticsResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Running diagnostics" />;
  if (!data || data.status !== "ready") return <EmptyState title="Diagnostics not ready" detail={data?.notes?.join(" ") || "Train a model with enough labeled data."} />;
  const classRows = data.class_metrics.map((row) => ({
    label: String(row.label ?? ""),
    precision: Number(row.precision ?? 0),
    recall: Number(row.recall ?? 0),
    f1: Number(row.f1 ?? 0),
    support: Number(row.support ?? 0),
  }));
  const failureRows = data.failure_factors.map((item) => ({ title: String(item.title), severity: String(item.severity), factor: String(item.factor), detail: String(item.detail) }));
  const recommendations = data.recommendations.map((item) => ({ priority: String(item.priority), title: String(item.title), detail: String(item.detail) }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Accuracy" metric={String(data.metrics.accuracy ?? "-")} detail={`${data.target} / ${data.model}`} />
        <InsightCard title="Macro F1" metric={String(data.metrics.f1_macro ?? "-")} detail="Primary class-balance signal." />
        <InsightCard title="Error Samples" metric={String(data.error_samples.length)} detail="Misclassified examples in sample set." />
        <InsightCard title="Weak Classes" metric={String(data.low_performing_classes.length)} detail="Classes below review threshold." />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card tone="primary"><CardHeader eyebrow="Diagnostics" title="Confusion heatmap" /><HeatmapMatrix labels={data.labels} matrix={data.confusion_matrix} /></Card>
        <Card tone="warning"><CardHeader eyebrow="Class quality" title="Precision / Recall / F1" /><MetricComparisonChart data={classRows} labelKey="label" metrics={[{ key: "precision", label: "Precision" }, { key: "recall", label: "Recall" }, { key: "f1", label: "F1" }]} /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Model failure factors" rows={failureRows} />
        <Table title="Improvement recommendations" rows={recommendations} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Error Analysis" title="Misclassified samples" /><Table title="Error samples" rows={data.error_samples as Row[]} /></Card>
        <Card><CardHeader eyebrow="Features" title="Top diagnostic features" /><HorizontalBarChart data={(data.feature_diagnostics.top_features ?? []) as Row[]} labelKey="feature" valueKey="weight" /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Low-performing classes" rows={data.low_performing_classes as Row[]} />
        <Table title="Confusion pairs" rows={data.confusion_pairs as Row[]} />
      </div>
      <Notes notes={[...data.notes, ...(data.feature_diagnostics.notes ?? [])]} />
    </div>
  );
}

function Training({ title, data, loading }: { title: string; data: MLTrainResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Training model" />;
  if (!data || data.status !== "ready") return <EmptyState title="Model is not ready" detail={data?.notes?.join(" ") || "Add more labeled articles to train this target."} />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Accuracy" metric={String(data.metrics.accuracy)} detail={title} />
        <InsightCard title="Macro F1" metric={String(data.metrics.f1_macro)} detail="Balanced score across labels." />
        <InsightCard title="Train/Test" metric={`${data.train_test_split.train_documents}/${data.train_test_split.test_documents}`} detail="Documents in split." />
        <InsightCard title="Vocabulary" metric={String(data.vectorizer.vocabulary_size)} detail="TF-IDF feature space." />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Evaluation" title="Confusion heatmap" /><HeatmapMatrix labels={data.labels} matrix={data.confusion_matrix} /></Card>
        <Card><CardHeader eyebrow="Features" title="Top feature importance" /><HorizontalBarChart data={data.feature_importance} labelKey="feature" valueKey="weight" /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Per-class metrics" rows={data.class_metrics as Row[]} />
        <Table title="Prediction examples" rows={data.sample_predictions as Row[]} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Confusion pairs" rows={data.confusion_pairs as Row[]} />
        <Table title="Classification report" rows={reportRows(data.classification_report)} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function DecisionTree({ data, loading, imageUrl, pathData, pathLoading }: { data: DecisionTreeResponse | undefined; loading: boolean; imageUrl: string; pathData: Awaited<ReturnType<typeof api.mlDecisionPath>> | undefined; pathLoading: boolean }) {
  if (loading) return <EmptyState title="Training Decision Tree" />;
  if (!data || data.status !== "ready") return <EmptyState title="Decision Tree is not ready" detail={data?.notes?.join(" ") || "Add more labeled articles."} />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Tree Depth" metric={String(data.tree.max_depth)} detail="Maximum decision depth." />
        <InsightCard title="Nodes" metric={String(data.tree.node_count)} detail="Split and leaf nodes." />
        <InsightCard title="Leaves" metric={String(data.tree.n_leaves)} detail="Terminal prediction leaves." />
        <InsightCard title="Macro F1" metric={String(data.metrics.f1_macro)} detail="Evaluation on test split." />
      </div>
      <Card>
        <CardHeader eyebrow="Visualization" title="Decision tree graph" action={<StatusBadge status={data.status} />} />
        <div className="overflow-auto rounded-md border border-line bg-surface p-3">
          <object data={imageUrl} type="image/svg+xml" aria-label="Decision tree visualization" className="h-[520px] min-w-[960px] w-full" />
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Explanation" title="Decision path" />{pathLoading ? <EmptyState title="Loading decision path" /> : <PathPanel data={pathData} />}</Card>
        <Card><CardHeader eyebrow="Features" title="Top split features" /><HorizontalBarChart data={data.feature_importance} labelKey="feature" valueKey="weight" /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Evaluation" title="Decision Tree heatmap" /><HeatmapMatrix labels={data.labels} matrix={data.confusion_matrix} /></Card>
        <Table title="Decision Tree sample predictions" rows={data.sample_predictions as Row[]} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function Artifacts({ data, loading }: { data: MLArtifactListResponse | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading saved artifacts" />;
  if (!data?.items.length) return <EmptyState title="No saved model artifacts" detail="Run a training job to persist model, vectorizer, metrics, and reports." />;
  const rows = data.items.map((item) => ({
    artifact_id: item.artifact_id,
    job_id: item.job_id ?? "-",
    target: item.target,
    model: item.model,
    status: item.status,
    accuracy: item.metrics.accuracy ?? "-",
    f1_macro: item.metrics.f1_macro ?? "-",
    created_at: item.created_at ?? "-",
  }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Saved Runs" metric={String(data.total)} detail="Persisted ML training artifacts." />
        <InsightCard title="Ready" metric={String(data.items.filter((item) => item.status === "ready").length)} detail="Artifacts available for download." />
        <InsightCard title="Decision Trees" metric={String(data.items.filter((item) => item.model === "decision_tree").length)} detail="Runs with tree visualization files." />
        <InsightCard title="Storage" metric="data/models" detail="Model files are stored under the ML artifacts directory." />
      </div>
      <Table title="Saved artifacts" rows={rows} />
      <div className="grid gap-4 lg:grid-cols-2">
        {data.items.slice(0, 6).map((item) => (
          <Card key={item.artifact_id}>
            <CardHeader eyebrow={item.model} title={item.artifact_id} action={<StatusBadge status={item.status} />} />
            <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
              <Metric label="Target" value={item.target} />
              <Metric label="Accuracy" value={String(item.metrics.accuracy ?? "-")} />
              <Metric label="Macro F1" value={String(item.metrics.f1_macro ?? "-")} />
              <Metric label="Files" value={String(item.files.length)} />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "manifest")} label="Manifest" />
              <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "model")} label="Model" />
              <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "vectorizer")} label="Vectorizer" />
              <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "metrics")} label="Metrics" />
              <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "feature_importance")} label="Features" />
              {item.files.includes("decision_tree.svg") ? <ExportButton href={api.mlArtifactDownloadUrl(item.artifact_id, "tree_svg")} label="Tree SVG" /> : null}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function PathPanel({ data }: { data: Awaited<ReturnType<typeof api.mlDecisionPath>> | undefined }) {
  if (!data || data.status !== "ready") return <EmptyState title="No decision path" detail={data?.notes?.join(" ") || "Choose an article from the current corpus."} />;
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-line bg-surface-subtle p-3 text-sm text-muted">{data.explanation}</div>
      <div className="grid grid-cols-3 gap-2 text-sm">
        <Metric label="Prediction" value={data.prediction ?? "-"} />
        <Metric label="Actual" value={data.actual_label ?? "-"} />
        <Metric label="Confidence" value={String(data.confidence ?? "-")} />
      </div>
      <Table title="Path steps" rows={data.path as Row[]} />
    </div>
  );
}

function BarChartBlock({ data, xKey, yKey, fill }: { data: Row[]; xKey: string; yKey: string; fill: string }) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return <div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey={xKey} tick={{ fontSize: 12 }} /><YAxis allowDecimals={false} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey={yKey} fill={fill} radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

function Table({ title, rows }: { title: string; rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 7);
  return <Card><CardHeader eyebrow="Table" title={title} />{rows.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-line text-sm"><thead><tr className="text-left text-xs uppercase tracking-wide text-muted">{headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}</tr></thead><tbody className="divide-y divide-line">{rows.slice(0, 30).map((row, index) => <tr key={index}>{headers.map((header) => <td key={header} className="px-3 py-2 text-muted">{String(row[header] ?? "")}</td>)}</tr>)}</tbody></table></div> : <EmptyState title="No table data" />}</Card>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-line bg-surface-elevated p-2 shadow-[var(--shadow-inset)]"><div className="text-xs text-muted">{label}</div><div className="mt-1 font-semibold text-ink">{value}</div></div>;
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes.length) return null;
  return <Card><CardHeader eyebrow="Notes" title="Model caveats" /><div className="space-y-2">{notes.map((note) => <div key={note} className="rounded-md border border-line bg-surface-subtle p-3 text-sm text-muted">{note}</div>)}</div></Card>;
}

function ExportButton({ href, label }: { href: string; label: string }) {
  return <a href={href} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Download className="h-4 w-4" />{label}</a>;
}

function toChartRows(values: Record<string, number>): Row[] {
  return Object.entries(values).map(([name, count]) => ({ name, count }));
}

function reportRows(report: Record<string, unknown>): Row[] {
  return Object.entries(report).map(([label, value]) => ({ label, ...(typeof value === "object" && value ? value as Row : { value: String(value) }) }));
}
