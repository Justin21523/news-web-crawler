"use client";

import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PipelineStepper } from "@/components/pipeline-stepper";
import { QualityList } from "@/components/quality-list";
import { Card, CardHeader, ChartNote, EmptyState, KpiCard, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const { t } = useI18n();
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.stats, refetchInterval: 15000 });
  const quality = useQuery({ queryKey: ["data-quality"], queryFn: api.dataQuality, refetchInterval: 15000 });
  const pipeline = useQuery({ queryKey: ["pipeline-status"], queryFn: api.pipelineStatus, refetchInterval: 15000 });
  const analysis = useQuery({ queryKey: ["analysis-overview"], queryFn: api.analysisOverview, refetchInterval: 30000 });
  const data = stats.data;
  const sourceData = Object.entries(data?.sources ?? {}).map(([name, count]) => ({ name, count }));
  const readyReports = analysis.data?.reports.filter((report) => report.status === "ready").length ?? 0;

  return (
    <div className="page-shell">
      <div className="page-heading" data-tour-id="dashboard-overview">
        <h1 className="text-2xl font-semibold text-ink">{t("page.dashboard.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("page.dashboard.subtitle")}</p>
      </div>

      {stats.isLoading ? (
        <Card className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading statistics
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard label="Completeness" value={`${quality.data?.completeness_score ?? 0}%`} detail="Field + NLP coverage" tone="blue" />
        <KpiCard label="Total Articles" value={(data?.total_articles ?? 0).toLocaleString()} detail="SQLite article records" tone="green" />
        <KpiCard label="NLP Enriched" value={(data?.enriched ?? 0).toLocaleString()} detail="Token/entity coverage" tone="magenta" />
        <KpiCard label="Ready Reports" value={readyReports} detail="Generated analysis outputs" tone="yellow" />
      </div>

      <Card data-tour-id="dashboard-pipeline">
        <CardHeader eyebrow="Pipeline" title={`Processing flow (${pipeline.data?.completion_percent ?? 0}% complete)`} />
        {pipeline.data?.steps.length ? (
          <PipelineStepper steps={pipeline.data.steps} />
        ) : (
          <EmptyState title="No pipeline state yet" detail="Run ingest or crawl to start the flow." />
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-muted">Coverage</div>
              <h2 className="mt-1 font-semibold text-ink">Sources</h2>
            </div>
            <span className="text-sm text-muted">
              {data?.date_range?.[0] || "No start date"} - {data?.date_range?.[1] || "No end date"}
            </span>
          </div>
          {sourceData.length ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sourceData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="var(--chart-2)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No articles yet" detail="Start with an ingest or crawl job." />
          )}
          <ChartNote>分類色彩保持有限；來源比較使用單一主色，避免讓顏色承載過多意義。</ChartNote>
        </Card>

        <Card>
          <CardHeader eyebrow="Quality" title="Completeness checks" />
          {quality.data?.metrics.length ? <QualityList metrics={quality.data.metrics} /> : <EmptyState title="No quality metrics" />}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader eyebrow="Operations" title="Recent Jobs" />
          <div className="mt-4 space-y-3">
            {data?.latest_jobs.length ? (
              data.latest_jobs.map((job) => (
                <div key={job.id} className="rounded-md border border-line p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-ink">#{job.id} {job.type}</div>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="numeric mt-2 text-xs text-muted">{job.created_at || "No timestamp"}</div>
                </div>
              ))
            ) : (
              <EmptyState title="No jobs have been created." />
            )}
          </div>
        </Card>

        <Card>
          <CardHeader eyebrow="Executive summary" title="Recommended next actions" />
          <div className="space-y-3">
            {(quality.data?.recommendations.length || analysis.data?.recommendations.length) ? (
              [...(quality.data?.recommendations ?? []), ...(analysis.data?.recommendations ?? [])].map((item) => (
                <div key={item} className="rounded-md border border-line bg-surface-subtle p-3 text-sm leading-6 text-muted">{item}</div>
              ))
            ) : (
              <EmptyState title="No recommendations" detail="The current dataset is ready for review." />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
