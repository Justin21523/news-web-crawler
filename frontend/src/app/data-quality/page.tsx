"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ExternalLink } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PipelineStepper } from "@/components/pipeline-stepper";
import { QualityList } from "@/components/quality-list";
import { Button, Card, CardHeader, ChartNote, EmptyState, Input, KpiCard, Select } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

export default function DataQualityPage() {
  const { t } = useI18n();
  const [issueType, setIssueType] = useState("");
  const [severity, setSeverity] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);

  const quality = useQuery({ queryKey: ["data-quality"], queryFn: api.dataQuality, refetchInterval: 15000 });
  const pipeline = useQuery({ queryKey: ["pipeline-status"], queryFn: api.pipelineStatus, refetchInterval: 15000 });
  const issueParams = useMemo(() => ({
    issue_type: issueType,
    severity,
    source,
    category,
    date_from: dateFrom,
    date_to: dateTo,
    page,
    page_size: 10,
  }), [issueType, severity, source, category, dateFrom, dateTo, page]);
  const issueRows = useQuery({
    queryKey: ["data-quality-issues", issueParams],
    queryFn: () => api.dataQualityIssues(issueParams),
    refetchInterval: 15000,
  });

  const sourceRows = Object.entries(quality.data?.source_coverage ?? {}).map(([source, count]) => ({ source, count }));
  const categoryRows = Object.entries(quality.data?.category_coverage ?? {}).map(([category, count]) => ({ category, count }));
  const missingRows = Object.entries(quality.data?.missing_fields ?? {}).map(([field, count]) => ({ field, count }));
  const issueCountRows = Object.entries(quality.data?.issue_counts ?? {}).map(([issue, count]) => ({ issue: issue.replaceAll("_", " "), count }));
  const severityRows = Object.entries(quality.data?.severity_counts ?? {}).map(([severity, count]) => ({ severity, count }));
  const resetPage = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setPage(1);
  };
  const exportParams = {
    issue_type: issueType,
    severity,
    source,
    category,
    date_from: dateFrom,
    date_to: dateTo,
  };

  return (
    <div className="page-shell">
      <div className="page-heading" data-tour-id="data-quality-overview">
        <h1 className="text-2xl font-semibold text-ink">{t("page.quality.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("page.quality.subtitle")}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard label="Quality Score" value={`${quality.data?.quality_score ?? 0}%`} detail="Missing, duplicate, URL, and content checks" />
        <KpiCard label="Completeness Score" value={`${quality.data?.completeness_score ?? 0}%`} detail="Required fields + NLP coverage" />
        <KpiCard label="Articles" value={(quality.data?.total_articles ?? 0).toLocaleString()} detail="Total records" tone="green" />
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_1fr_1fr]">
        <KpiCard
          label="Date Range"
          value={quality.data?.date_range?.[0] ? "Ready" : "Missing"}
          detail={`${quality.data?.date_range?.[0] ?? "-"} to ${quality.data?.date_range?.[1] ?? "-"}`}
          tone="yellow"
        />
        <KpiCard label="Quality Issues" value={(quality.data?.issues.length ?? 0).toLocaleString()} detail="Top issue rows available for review" tone="magenta" />
        <KpiCard label="Sources" value={Object.keys(quality.data?.source_coverage ?? {}).length.toLocaleString()} detail="Distinct source coverage" />
      </div>

      <Card>
        <CardHeader eyebrow="Process" title={`Pipeline completion ${pipeline.data?.completion_percent ?? 0}%`} />
        {pipeline.isLoading ? (
          <EmptyState title="Loading pipeline state" />
        ) : pipeline.data?.steps.length ? (
          <PipelineStepper steps={pipeline.data.steps} />
        ) : (
          <EmptyState title="No pipeline state" />
        )}
      </Card>

      <Card>
        <CardHeader eyebrow="Filters" title="Issue drill-down controls" />
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Select value={issueType} onChange={(event) => resetPage(setIssueType)(event.target.value)}>
            <option value="">All issues</option>
            {Object.keys(quality.data?.issue_counts ?? {}).map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
          </Select>
          <Select value={severity} onChange={(event) => resetPage(setSeverity)(event.target.value)}>
            <option value="">All severity</option>
            <option value="danger">danger</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </Select>
          <Select value={source} onChange={(event) => resetPage(setSource)(event.target.value)}>
            <option value="">All sources</option>
            {Object.keys(quality.data?.source_coverage ?? {}).map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Select value={category} onChange={(event) => resetPage(setCategory)(event.target.value)}>
            <option value="">All categories</option>
            {Object.keys(quality.data?.category_coverage ?? {}).map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Input type="date" value={dateFrom} onChange={(event) => resetPage(setDateFrom)(event.target.value)} />
          <Input type="date" value={dateTo} onChange={(event) => resetPage(setDateTo)(event.target.value)} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <ExportButton href={api.dataQualityExportUrl({ ...exportParams, format: "json" })} label="JSON" />
          <ExportButton href={api.dataQualityExportUrl({ ...exportParams, format: "csv" })} label="CSV" />
          <ExportButton href={api.dataQualityExportUrl({ ...exportParams, format: "markdown" })} label="Markdown" />
          <button
            className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-muted hover:text-ink"
            onClick={() => {
              setIssueType("");
              setSeverity("");
              setSource("");
              setCategory("");
              setDateFrom("");
              setDateTo("");
              setPage(1);
            }}
          >
            Reset filters
          </button>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader eyebrow="Completeness" title="Quality checks" />
          {quality.isLoading ? (
            <EmptyState title="Loading quality metrics" />
          ) : quality.data?.metrics.length ? (
            <QualityList metrics={quality.data.metrics} />
          ) : (
            <EmptyState title="No metrics available" />
          )}
          <ChartNote>High missing-date or low NLP coverage directly affects time-series, topic modeling, and IR quality.</ChartNote>
        </Card>

        <Card>
          <CardHeader eyebrow="Missing fields" title="Field gaps" />
          {missingRows.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={missingRows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="field" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="var(--chart-4)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No missing-field summary" />
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader eyebrow="Issues" title="Issue types" />
          {issueCountRows.length ? (
            <Chart data={issueCountRows} xKey="issue" barKey="count" fill="var(--chart-1)" height="18rem" />
          ) : (
            <EmptyState title="No issue type data" />
          )}
        </Card>
        <Card>
          <CardHeader eyebrow="Issues" title="Severity distribution" />
          {severityRows.length ? (
            <Chart data={severityRows} xKey="severity" barKey="count" fill="var(--chart-5)" height="18rem" />
          ) : (
            <EmptyState title="No severity data" />
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader eyebrow="Coverage" title="Source distribution" />
          {sourceRows.length ? (
            <Chart data={sourceRows} xKey="source" barKey="count" fill="var(--chart-2)" height="20rem" />
          ) : (
            <EmptyState title="No source data" detail="Run crawl or ingest first." />
          )}
        </Card>

        <Card>
          <CardHeader eyebrow="Coverage" title="Category distribution" />
          {categoryRows.length ? (
            <Chart data={categoryRows} xKey="category" barKey="count" fill="var(--chart-2)" height="20rem" />
          ) : (
            <EmptyState title="No category data" detail="Run crawl or ingest first." />
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader eyebrow="Coverage" title="Date coverage" />
          {quality.data?.date_coverage.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={quality.data.date_coverage}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No date coverage" detail="Publish dates are required for trend analysis." />
          )}
        </Card>
        <Card>
          <CardHeader eyebrow="Length" title="Article length distribution" />
          {quality.data?.length_distribution.length ? (
            <Chart data={quality.data.length_distribution} xKey="bucket" barKey="count" fill="var(--chart-4)" height="18rem" />
          ) : (
            <EmptyState title="No length data" />
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr]">
        <Card>
          <CardHeader eyebrow="Actions" title="Recommended fixes" />
          <div className="space-y-3">
            {quality.data?.recommendations.length ? (
              quality.data.recommendations.map((item) => (
                <div key={item} className="rounded-md border border-line bg-surface-subtle p-3 text-sm leading-6 text-muted">{item}</div>
              ))
            ) : (
              <EmptyState title="No immediate fixes" detail="The current dataset passes the core readiness checks." />
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader
          eyebrow="Drill-down"
          title={`Quality issues${issueRows.data ? ` (${issueRows.data.total})` : ""}`}
          action={<div className="text-xs text-muted">Page {issueRows.data?.page ?? page}</div>}
        />
        {issueRows.data?.items.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-line text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-muted">
                  <th className="px-3 py-2 font-semibold">Article ID</th>
                  <th className="px-3 py-2 font-semibold">Title</th>
                  <th className="px-3 py-2 font-semibold">Source</th>
                  <th className="px-3 py-2 font-semibold">Date</th>
                  <th className="px-3 py-2 font-semibold">Issue</th>
                  <th className="px-3 py-2 font-semibold">Severity</th>
                  <th className="px-3 py-2 font-semibold">Message</th>
                  <th className="px-3 py-2 font-semibold">Suggested fix</th>
                  <th className="px-3 py-2 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {issueRows.data.items.map((issue) => (
                  <tr key={`${issue.article_id}-${issue.issue_type}`} className="text-ink">
                    <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">{issue.article_id}</td>
                    <td className="min-w-[220px] px-3 py-2">{issue.title || "Untitled"}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-muted">{issue.source || "unknown"}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-muted">{issue.publish_date || "-"}</td>
                    <td className="whitespace-nowrap px-3 py-2">{issue.issue_type.replaceAll("_", " ")}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        issue.severity === "danger"
                          ? "bg-danger-soft text-danger-text"
                          : issue.severity === "warning"
                            ? "bg-warn-soft text-warn-text"
                            : "bg-surface-muted text-text-secondary"
                      }`}>
                        {issue.severity}
                      </span>
                    </td>
                    <td className="min-w-[220px] px-3 py-2 text-muted">{issue.message}</td>
                    <td className="min-w-[260px] px-3 py-2 text-muted">{issue.suggested_fix}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <Link href={`/articles/${encodeURIComponent(issue.article_id)}`} className="inline-flex items-center gap-1 text-primary-active">
                        View
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-4">
              <Button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button>
              <div className="text-sm text-muted">
                Showing {issueRows.data.items.length} of {issueRows.data.total}
              </div>
              <Button
                disabled={!issueRows.data || page * issueRows.data.page_size >= issueRows.data.total}
                onClick={() => setPage((value) => value + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        ) : issueRows.isLoading ? (
          <EmptyState title="Loading quality issues" />
        ) : (
          <EmptyState title="No matching issues" detail="Change filters or run the demo job to populate quality checks." />
        )}
      </Card>
    </div>
  );
}

function Chart({
  data,
  xKey,
  barKey,
  fill,
  height,
}: {
  data: Array<Record<string, string | number>>;
  xKey: string;
  barKey: string;
  fill: string;
  height: string;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={barKey} fill={fill} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ExportButton({ href, label }: { href: string; label: string }) {
  return (
    <a href={href} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
      <Download className="h-4 w-4" />
      {label}
    </a>
  );
}
