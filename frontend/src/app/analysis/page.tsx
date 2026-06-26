"use client";

import { Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { InsightCard } from "@/components/analysis-cards";
import { AdvancedChartCard, CalendarHeatmapChart, HeatmapChart, SankeyChart, TreemapChart } from "@/components/advanced-charts";
import { DataTable, ScrollableTabs } from "@/components/data-display";
import { Card, CardHeader, ChartNote, EmptyState, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { readQuery, updateQueryString, validParam } from "@/lib/url-state";

const tabs = [
  { key: "overview", label: "Overview" },
  { key: "trends", label: "Trends" },
  { key: "sources", label: "Sources" },
  { key: "categories", label: "Categories" },
  { key: "topics", label: "Topic Intelligence" },
  { key: "keywords_entities", label: "Keywords & Entities" },
  { key: "business", label: "Business Insights" },
] as const;

type Row = Record<string, string | number | null | undefined>;

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="page-shell"><EmptyState title="Loading analysis dashboard" /></div>}>
      <AnalysisWorkbench />
    </Suspense>
  );
}

function AnalysisWorkbench() {
  const { t } = useI18n();
  const router = useRouter();
  const search = useSearchParams();
  const active = validParam(search.get("tab"), tabs.map((tab) => tab.key), "overview");
  const source = readQuery(search, "source");
  const category = readQuery(search, "category");
  const dateFrom = readQuery(search, "date_from");
  const dateTo = readQuery(search, "date_to");

  const update = (changes: Record<string, string | number | null | undefined>) => {
    const next = updateQueryString(search, changes);
    router.replace(next ? `/analysis?${next}` : "/analysis");
  };

  const params = useMemo(() => ({
    source,
    category,
    date_from: dateFrom,
    date_to: dateTo,
    limit: 30,
  }), [source, category, dateFrom, dateTo]);

  const dashboard = useQuery({ queryKey: ["analysis-dashboard", params], queryFn: () => api.analysisDashboard(params), refetchInterval: 30000 });
  const trends = useQuery({ queryKey: ["analysis-trends", params], queryFn: () => api.analysisTrends(params), refetchInterval: 30000 });
  const sources = useQuery({ queryKey: ["analysis-sources", params], queryFn: () => api.analysisSources(params), refetchInterval: 30000 });
  const categories = useQuery({ queryKey: ["analysis-categories", params], queryFn: () => api.analysisCategories(params), refetchInterval: 30000 });
  const keywordsEntities = useQuery({ queryKey: ["analysis-keywords-entities", params], queryFn: () => api.analysisKeywordsEntities(params), refetchInterval: 30000 });
  const business = useQuery({ queryKey: ["analysis-business", params], queryFn: () => api.analysisBusinessInsights(params), refetchInterval: 30000 });
  const topics = useQuery({ queryKey: ["analysis-topic-intelligence", params], queryFn: () => api.textMiningTopics({ ...params, method: "nmf", n_topics: 6 }), refetchInterval: 30000 });
  const liveSummary = useQuery({ queryKey: ["analysis-live-summary", params], queryFn: () => api.analysisLiveSummary(params), refetchInterval: 30000 });
  const quality = useQuery({ queryKey: ["data-quality"], queryFn: api.dataQuality, refetchInterval: 30000 });

  const exportParams = { ...params, section: active, format: "json" };
  const csvExportParams = { ...params, section: active, format: "csv" };
  const markdownExportParams = { ...params, section: active, format: "markdown" };

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3" data-tour-id="analysis-overview">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{t("page.analysis.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("page.analysis.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ExportButton href={api.analysisExportUrl(exportParams)} label="JSON" />
          <ExportButton href={api.analysisExportUrl(csvExportParams)} label="CSV" />
          <ExportButton href={api.analysisExportUrl(markdownExportParams)} label="Markdown" />
        </div>
      </div>

      <Card>
        <CardHeader eyebrow="Filters" title="Global analysis filters" />
        <div className="grid gap-3 md:grid-cols-4">
          <Select value={source} onChange={(event) => update({ source: event.target.value })}>
            <option value="">All sources</option>
            {Object.keys(quality.data?.source_coverage ?? {}).map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Select value={category} onChange={(event) => update({ category: event.target.value })}>
            <option value="">All categories</option>
            {Object.keys(quality.data?.category_coverage ?? {}).map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Input type="date" value={dateFrom} onChange={(event) => update({ date_from: event.target.value })} />
          <Input type="date" value={dateTo} onChange={(event) => update({ date_to: event.target.value })} />
        </div>
      </Card>

      <ScrollableTabs tabs={[...tabs]} active={active} onChange={(tab) => update({ tab })} />

      {active === "overview" ? <OverviewTab data={dashboard.data} live={liveSummary.data} loading={dashboard.isLoading} /> : null}
      {active === "trends" ? <TrendsTab data={trends.data} loading={trends.isLoading} onFilter={(changes) => update(changes)} selected={selectionSummary({ source, category, dateFrom, dateTo })} /> : null}
      {active === "sources" ? <SourcesTab data={sources.data} loading={sources.isLoading} onFilter={(changes) => update(changes)} selected={selectionSummary({ source, category, dateFrom, dateTo })} /> : null}
      {active === "categories" ? <CategoriesTab data={categories.data} loading={categories.isLoading} onFilter={(changes) => update(changes)} selected={selectionSummary({ source, category, dateFrom, dateTo })} /> : null}
      {active === "topics" ? <TopicIntelligenceTab data={topics.data} loading={topics.isLoading} /> : null}
      {active === "keywords_entities" ? <KeywordsEntitiesTab data={keywordsEntities.data} loading={keywordsEntities.isLoading} /> : null}
      {active === "business" ? <BusinessTab data={business.data} loading={business.isLoading} /> : null}
    </div>
  );
}

function OverviewTab({ data, live, loading }: { data: Awaited<ReturnType<typeof api.analysisDashboard>> | undefined; live: Awaited<ReturnType<typeof api.analysisLiveSummary>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading overview" />;
  if (!data) return <EmptyState title="No overview data" detail="Run the demo or analysis job first." />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-5">
        <InsightCard title="Articles" metric={String(data.kpis.total_articles ?? 0)} detail="Filtered article base." />
        <InsightCard title="NLP enriched" metric={String(data.kpis.nlp_enriched ?? 0)} detail="Documents with NLP outputs." />
        <InsightCard title="Sources" metric={String(data.kpis.source_count ?? 0)} detail="Distinct source coverage." />
        <InsightCard title="Categories" metric={String(data.kpis.category_count ?? 0)} detail="Distinct category coverage." />
        <InsightCard title="Date coverage" metric={`${data.kpis.date_coverage_percent ?? 0}%`} detail="Articles usable for trends." />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader eyebrow="Trend" title="Daily article volume" />
          <LineChartBlock data={data.daily_volume} xKey="date" yKey="count" />
          <ChartNote>Publication dates drive trend and lifecycle analysis; missing dates are excluded.</ChartNote>
        </Card>
        <Card>
          <CardHeader eyebrow="Insights" title="Executive summary" />
          <InsightList items={data.insights} />
        </Card>
      </div>
      <Card tone="secondary">
        <CardHeader eyebrow={`Live analysis · ${live?.provider ?? "extractive"}`} title="On-demand corpus summary" />
        {live?.status === "ready" ? (
          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-3">
              {live.bullets.map((item, index) => (
                <div key={`${item}-${index}`} className="rounded-md border border-line bg-surface-subtle p-3 text-sm leading-6 text-muted">{item}</div>
              ))}
            </div>
            <div className="space-y-4">
              <DataTable title="Top live terms" rows={live.top_terms} limit={12} />
              <DataTable title="Representative articles" rows={live.representative_articles as Row[]} limit={8} />
            </div>
          </div>
        ) : (
          <EmptyState title="No live summary" detail={live?.notes?.join(" ") || "Run ingestion/NLP or adjust filters."} />
        )}
      </Card>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card><CardHeader eyebrow="Source" title="Article share" /><BarChartBlock data={data.source_distribution} xKey="name" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Category" title="Category mix" /><BarChartBlock data={data.category_distribution} xKey="name" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Keywords" title="Top keywords" /><BarChartBlock data={data.top_keywords} xKey="keyword" yKey="score" fill="var(--chart-1)" /></Card>
      </div>
      <Table title="Top Keywords" rows={data.top_keywords.slice(0, 10)} />
      <Notes notes={data.notes} />
    </div>
  );
}

function TrendsTab({ data, loading, onFilter, selected }: { data: Awaited<ReturnType<typeof api.analysisTrends>> | undefined; loading: boolean; onFilter: (changes: Record<string, string>) => void; selected?: string }) {
  if (loading) return <EmptyState title="Loading trends" />;
  if (!data) return <EmptyState title="No trend data" />;
  return (
    <div className="space-y-5">
      <AdvancedChartCard
        eyebrow="Trend"
        title="Publication calendar heatmap"
        insight="Darker days indicate stronger news volume; gaps highlight missing date coverage or crawler inactivity."
        metric={`${data.daily_volume.length} active days`}
        rows={data.daily_volume}
        exportName="analysis-calendar-heatmap"
        selectedSummary={selected}
        onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
      >
        <CalendarHeatmapChart data={data.daily_volume} exportName="analysis-calendar-heatmap" onSelect={(item) => onFilter({ date_from: item.date, date_to: item.date })} />
      </AdvancedChartCard>
      <Card><CardHeader eyebrow="Trend" title="Daily article volume" /><LineChartBlock data={data.daily_volume} xKey="date" yKey="count" /></Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Category Trend" rows={data.category_trend} />
        <Table title="Source Trend" rows={data.source_trend} />
      </div>
      <Table title="Keyword Trend" rows={data.keyword_trend} />
      <Notes notes={data.notes} />
    </div>
  );
}

function SourcesTab({ data, loading, onFilter, selected }: { data: Awaited<ReturnType<typeof api.analysisSources>> | undefined; loading: boolean; onFilter: (changes: Record<string, string>) => void; selected?: string }) {
  if (loading) return <EmptyState title="Loading source analysis" />;
  if (!data) return <EmptyState title="No source data" />;
  const heatmap = matrixRowsToHeatmap(data.source_category_matrix, "source", "category");
  return (
    <div className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <AdvancedChartCard
          eyebrow="Source Intelligence"
          title="Source volume treemap"
          insight="Treemap area shows share of voice by source, making concentration and crawler imbalance easy to spot."
          metric={`${data.source_volume.length} sources`}
          rows={data.source_volume}
          exportName="source-volume-treemap"
          selectedSummary={selected}
          onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
        >
          <TreemapChart data={data.source_volume.map((item) => ({ name: item.name, value: item.count }))} exportName="source-volume-treemap" onSelect={(item) => onFilter({ source: item.name })} />
        </AdvancedChartCard>
        <AdvancedChartCard
          eyebrow="Coverage Matrix"
          title="Source-category heatmap"
          insight="This matrix shows which sources dominate each category and where coverage gaps exist."
          metric={`${data.source_category_matrix.length} pairs`}
          rows={data.source_category_matrix}
          exportName="source-category-heatmap"
          selectedSummary={selected}
          onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
        >
          <HeatmapChart xLabels={heatmap.xLabels} yLabels={heatmap.yLabels} values={heatmap.values} exportName="source-category-heatmap" onSelect={(item) => onFilter({ source: item.yLabel, category: item.xLabel })} />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard
        eyebrow="Flow"
        title="Source to category flow"
        insight="Sankey width shows article flow from media source into category, useful for source positioning analysis."
        metric={`${data.source_category_matrix.reduce((sum, row) => sum + Number(row.count || 0), 0)} articles`}
        rows={data.source_category_matrix}
        exportName="source-category-sankey"
        selectedSummary={selected}
        onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
      >
        <SankeyChart rows={data.source_category_matrix} sourceKey="source" targetKey="category" exportName="source-category-sankey" onSelect={(row) => onFilter({ source: String(row.source ?? ""), category: String(row.category ?? "") })} />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card><CardHeader eyebrow="Sources" title="Source volume" /><BarChartBlock data={data.source_volume} xKey="name" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Insights" title="Source notes" /><InsightList items={data.insights} /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Source-Category Matrix" rows={data.source_category_matrix} />
        <Table title="Source Keyword Profile" rows={data.source_keyword_profile} />
      </div>
    </div>
  );
}

function CategoriesTab({ data, loading, onFilter, selected }: { data: Awaited<ReturnType<typeof api.analysisCategories>> | undefined; loading: boolean; onFilter: (changes: Record<string, string>) => void; selected?: string }) {
  if (loading) return <EmptyState title="Loading category analysis" />;
  if (!data) return <EmptyState title="No category data" />;
  const heatmap = matrixRowsToHeatmap(data.category_source_mix, "category", "source");
  return (
    <div className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <AdvancedChartCard
          eyebrow="Category Intelligence"
          title="Category distribution treemap"
          insight="Treemap area highlights dominant categories and whether the corpus has enough topical variety."
          metric={`${data.category_distribution.length} categories`}
          rows={data.category_distribution}
          exportName="category-distribution-treemap"
          selectedSummary={selected}
          onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
        >
          <TreemapChart data={data.category_distribution.map((item) => ({ name: item.name, value: item.count }))} exportName="category-distribution-treemap" onSelect={(item) => onFilter({ category: item.name })} />
        </AdvancedChartCard>
        <AdvancedChartCard
          eyebrow="Coverage Matrix"
          title="Category-source heatmap"
          insight="This matrix exposes source concentration inside each category and supports crawler target decisions."
          metric={`${data.category_source_mix.length} pairs`}
          rows={data.category_source_mix}
          exportName="category-source-heatmap"
          selectedSummary={selected}
          onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
        >
          <HeatmapChart xLabels={heatmap.xLabels} yLabels={heatmap.yLabels} values={heatmap.values} exportName="category-source-heatmap" onSelect={(item) => onFilter({ category: item.yLabel, source: item.xLabel })} />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard
        eyebrow="Flow"
        title="Category to source flow"
        insight="Sankey width compares which sources contribute most to each category."
        metric={`${data.category_source_mix.reduce((sum, row) => sum + Number(row.count || 0), 0)} articles`}
        rows={data.category_source_mix}
        exportName="category-source-sankey"
        selectedSummary={selected}
        onClearSelection={() => onFilter({ source: "", category: "", date_from: "", date_to: "" })}
      >
        <SankeyChart rows={data.category_source_mix} sourceKey="category" targetKey="source" exportName="category-source-sankey" onSelect={(row) => onFilter({ category: String(row.category ?? ""), source: String(row.source ?? "") })} />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card><CardHeader eyebrow="Categories" title="Category distribution" /><BarChartBlock data={data.category_distribution} xKey="name" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Insights" title="Coverage notes" /><InsightList items={data.insights} /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Category Source Mix" rows={data.category_source_mix} />
        <Table title="Category Keywords" rows={data.category_keywords} />
      </div>
    </div>
  );
}

function TopicIntelligenceTab({ data, loading }: { data: Awaited<ReturnType<typeof api.textMiningTopics>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading topic intelligence" />;
  if (!data) return <EmptyState title="No topic data" />;
  const rows = topicMatrixRows(data.topics);
  const heatmap = topicRowsToHeatmap(rows);
  return (
    <div className="space-y-5">
      <AdvancedChartCard
        eyebrow="Topic Intelligence"
        title="Topic keyword matrix"
        insight="Rows are discovered topics and columns are high-weight terms; strong cells explain each topic theme."
        metric={`${data.topics.length} topics`}
        rows={rows}
        exportName="topic-keyword-matrix"
      >
        <HeatmapChart xLabels={heatmap.xLabels} yLabels={heatmap.yLabels} values={heatmap.values} exportName="topic-keyword-matrix" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        {data.topics.map((topic) => (
          <Card key={topic.topic_id} tone="secondary">
            <CardHeader eyebrow={`Topic ${topic.topic_id}`} title={topic.top_terms.slice(0, 4).map((term) => term.term).join(" / ") || "Untitled topic"} />
            <div className="flex flex-wrap gap-2">
              {topic.top_terms.map((term) => <span key={term.term} className="rounded-full bg-secondary-soft px-2 py-1 text-xs font-semibold text-info-text">{term.term} {term.weight}</span>)}
            </div>
            <DataTable title="Representative articles" rows={topic.top_docs.map((doc) => ({ article_id: doc.article_id, weight: doc.weight, open: `/articles/${doc.article_id}` }))} limit={5} />
          </Card>
        ))}
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function KeywordsEntitiesTab({ data, loading }: { data: Awaited<ReturnType<typeof api.analysisKeywordsEntities>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading keyword and entity analysis" />;
  if (!data) return <EmptyState title="No keyword/entity data" />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Keywords" title="Top keywords" /><BarChartBlock data={data.top_keywords} xKey="keyword" yKey="score" fill="var(--chart-1)" /></Card>
        <Card>
          <CardHeader eyebrow="Entities" title="Named entities" />
          {data.top_entities.length ? <BarChartBlock data={data.top_entities} xKey="entity" yKey="count" fill="var(--chart-4)" /> : <EmptyState title="No entities available" detail="Run CKIP NER or an entity extraction job." />}
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Keyword by Source" rows={data.keyword_by_source} />
        <Table title="Keyword by Category" rows={data.keyword_by_category} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Entity by Source" rows={data.entity_by_source} />
        <Table title="Entity by Category" rows={data.entity_by_category} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function BusinessTab({ data, loading }: { data: Awaited<ReturnType<typeof api.analysisBusinessInsights>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading business insights" />;
  if (!data) return <EmptyState title="No business insights" />;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        {data.cards.map((item) => <InsightCard key={item.title} title={item.title} metric={String(item.metric ?? "-")} detail={item.detail} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader eyebrow="Recommendations" title="Content strategy suggestions" /><InsightList items={data.recommendations} /></Card>
        <Card><CardHeader eyebrow="Risk" title="Monitoring warnings" /><InsightList items={data.risks} /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Table title="Under-covered Categories" rows={data.tables.under_covered_categories ?? []} />
        <Table title="Source Concentration" rows={data.tables.source_concentration ?? []} />
        <Table title="Hot Topics" rows={data.tables.hot_topics ?? []} />
      </div>
    </div>
  );
}

function BarChartBlock({ data, xKey, yKey, fill }: { data: Row[]; xKey: string; yKey: string; fill: string }) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={yKey} fill={fill} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function LineChartBlock({ data, xKey, yKey }: { data: Row[]; xKey: string; yKey: string }) {
  if (!data.length) return <EmptyState title="No trend data" />;
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey={yKey} stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Table({ title, rows }: { title: string; rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 6);
  return (
    <Card>
      <CardHeader eyebrow="Table" title={title} />
      {rows.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-line text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-muted">
                {headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, 12).map((row, index) => (
                <tr key={index}>
                  {headers.map((header) => <td key={header} className="whitespace-nowrap px-3 py-2 text-muted">{String(row[header] ?? "")}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No table data" />
      )}
    </Card>
  );
}

function InsightList({ items }: { items: Array<{ title: string; detail: string; metric?: string; severity?: string }> }) {
  if (!items.length) return <EmptyState title="No insights available" />;
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={`${item.title}-${item.detail}`} className="rounded-md border border-line bg-surface-subtle p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold text-ink">{item.title}</div>
            {item.metric || item.severity ? <div className="text-xs font-semibold uppercase text-muted">{item.metric || item.severity}</div> : null}
          </div>
          <div className="mt-2 text-sm leading-6 text-muted">{item.detail}</div>
        </div>
      ))}
    </div>
  );
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes.length) return null;
  return (
    <Card>
      <CardHeader eyebrow="Notes" title="Analysis caveats" />
      <div className="space-y-2">
        {notes.map((note) => <div key={note} className="rounded-md border border-line bg-surface-subtle p-3 text-sm text-muted">{note}</div>)}
      </div>
    </Card>
  );
}

function matrixRowsToHeatmap(rows: Row[], yKey: string, xKey: string) {
  const xLabels = Array.from(new Set(rows.map((row) => String(row[xKey] ?? "Unknown")))).slice(0, 14);
  const yLabels = Array.from(new Set(rows.map((row) => String(row[yKey] ?? "Unknown")))).slice(0, 14);
  const values = rows
    .map((row) => [xLabels.indexOf(String(row[xKey] ?? "Unknown")), yLabels.indexOf(String(row[yKey] ?? "Unknown")), Number(row.count ?? 0)] as [number, number, number])
    .filter(([x, y]) => x >= 0 && y >= 0);
  return { xLabels, yLabels, values };
}

function topicMatrixRows(topics: Array<{ topic_id: number; top_terms: Array<{ term: string; weight: number }> }>): Row[] {
  return topics.flatMap((topic) =>
    topic.top_terms.slice(0, 10).map((term) => ({
      topic: `Topic ${topic.topic_id}`,
      term: term.term,
      weight: term.weight,
    })),
  );
}

function topicRowsToHeatmap(rows: Row[]) {
  const xLabels = Array.from(new Set(rows.map((row) => String(row.term ?? "")))).slice(0, 24);
  const yLabels = Array.from(new Set(rows.map((row) => String(row.topic ?? ""))));
  const values = rows
    .map((row) => [xLabels.indexOf(String(row.term ?? "")), yLabels.indexOf(String(row.topic ?? "")), Number(row.weight ?? 0)] as [number, number, number])
    .filter(([x, y]) => x >= 0 && y >= 0);
  return { xLabels, yLabels, values };
}

function selectionSummary({ source, category, dateFrom, dateTo }: { source: string; category: string; dateFrom: string; dateTo: string }) {
  const parts = [
    source ? `Source: ${source}` : "",
    category ? `Category: ${category}` : "",
    dateFrom || dateTo ? `Date: ${dateFrom || "start"} to ${dateTo || "end"}` : "",
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : undefined;
}

function ExportButton({ href, label }: { href: string; label: string }) {
  return (
    <a href={href} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white">
      <Download className="h-4 w-4" />
      {label}
    </a>
  );
}
