"use client";

import Link from "next/link";
import { Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, Play, Save, Search, X } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { InsightCard } from "@/components/analysis-cards";
import { AdvancedChartCard, BubbleScatterChart, CalendarHeatmapChart, ClusterProjectionChart, ForceGraphChart, HeatmapChart, MatrixHeatmapChart, NetworkGraphChart, RadarMetricChart, SankeyChart, TreemapChart, WordCloudChart } from "@/components/advanced-charts";
import { ScrollableTabs } from "@/components/data-display";
import { Button, Card, CardHeader, EmptyState, Input, Select, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";
import { readQuery, updateQueryString, validParam } from "@/lib/url-state";

const tabs = [
  { key: "overview", label: "Overview" },
  { key: "keywords", label: "Keyword Explorer" },
  { key: "tfidf", label: "TF-IDF" },
  { key: "ngrams", label: "N-grams" },
  { key: "topics", label: "Topics" },
  { key: "clusters", label: "Clustering" },
  { key: "similarity", label: "Similarity Search" },
  { key: "network", label: "Networks" },
  { key: "entities", label: "Entities" },
  { key: "collocations", label: "Collocations" },
  { key: "co-occurrence", label: "Co-occurrence" },
  { key: "relationships", label: "Relationships" },
  { key: "bursts", label: "Trends & Bursts" },
] as const;

type Row = Record<string, string | number | null | undefined>;

export default function TextMiningPage() {
  return (
    <Suspense fallback={<div className="page-shell"><EmptyState title="Loading text mining" /></div>}>
      <TextMiningWorkbench />
    </Suspense>
  );
}

function TextMiningWorkbench() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const search = useSearchParams();
  const active = validParam(search.get("tab"), tabs.map((tab) => tab.key), "overview");
  const source = readQuery(search, "source");
  const category = readQuery(search, "category");
  const dateFrom = readQuery(search, "date_from");
  const dateTo = readQuery(search, "date_to");
  const ngramN = readQuery(search, "ngram", "2");
  const topicMethod = readQuery(search, "topic_method", "nmf");
  const clusterMethod = readQuery(search, "cluster_method", "kmeans");
  const networkType = readQuery(search, "network_type", "keyword");
  const query = readQuery(search, "query", "資料 分析");
  const articleId = readQuery(search, "article_id");
  const topicId = readQuery(search, "topic_id");
  const clusterId = readQuery(search, "cluster_id");
  const entity = readQuery(search, "entity");
  const entityType = readQuery(search, "entity_type");
  const collocationMetric = readQuery(search, "collocation_metric", "npmi");
  const collocationLevel = readQuery(search, "collocation_level", "sentence");
  const collocationNgram = readQuery(search, "collocation_ngram", "bigram");
  const collocationWindow = readQuery(search, "collocation_window", "5");
  const cooccurrenceKind = readQuery(search, "co_kind", "keyword");
  const cooccurrenceMetric = readQuery(search, "co_metric", "npmi");
  const cooccurrenceFocus = readQuery(search, "focus");
  const recentWindow = readQuery(search, "recent_window", "7");
  const baselineWindow = readQuery(search, "baseline_window", "30");

  const update = (changes: Record<string, string | number | null | undefined>) => {
    const next = updateQueryString(search, changes);
    router.replace(next ? `/text-mining?${next}` : "/text-mining");
  };

  const quality = useQuery({ queryKey: ["data-quality"], queryFn: api.dataQuality, refetchInterval: 30000 });
  const params = useMemo(() => ({ source, category, date_from: dateFrom, date_to: dateTo, limit: 500 }), [source, category, dateFrom, dateTo]);
  const overview = useQuery({ queryKey: ["tm-overview", params], queryFn: () => api.textMiningOverview(params), refetchInterval: 30000 });
  const tfidf = useQuery({ queryKey: ["tm-tfidf", params], queryFn: () => api.textMiningTfidf(params), refetchInterval: 30000 });
  const ngrams = useQuery({ queryKey: ["tm-ngrams", params, ngramN], queryFn: () => api.textMiningNgrams({ ...params, n: ngramN }), refetchInterval: 30000 });
  const topics = useQuery({ queryKey: ["tm-topics", params, topicMethod], queryFn: () => api.textMiningTopics({ ...params, method: topicMethod, n_topics: 5 }), refetchInterval: 30000 });
  const clusters = useQuery({ queryKey: ["tm-clusters", params, clusterMethod], queryFn: () => api.textMiningClusters({ ...params, method: clusterMethod, n_clusters: 5 }), refetchInterval: 30000 });
  const similarity = useQuery({ queryKey: ["tm-similarity", params, query, articleId], queryFn: () => api.textMiningSimilarity({ ...params, query: articleId ? "" : query, article_id: articleId }), refetchInterval: 30000 });
  const network = useQuery({ queryKey: ["tm-network", params, networkType], queryFn: () => api.textMiningNetwork({ ...params, type: networkType }), refetchInterval: 30000 });
  const entities = useQuery({ queryKey: ["tm-entities", params, entity, entityType], queryFn: () => api.textMiningEntities({ ...params, entity, entity_type: entityType }), refetchInterval: 30000 });
  const collocations = useQuery({ queryKey: ["tm-collocations", params, collocationMetric, collocationLevel, collocationNgram, collocationWindow], queryFn: () => api.textMiningCollocations({ ...params, metric: collocationMetric, level: collocationLevel, ngram_type: collocationNgram, window_size: collocationWindow, min_freq: 2, top_k: 60 }), refetchInterval: 30000 });
  const cooccurrence = useQuery({ queryKey: ["tm-co-occurrence", params, cooccurrenceKind, cooccurrenceMetric, cooccurrenceFocus], queryFn: () => api.textMiningCooccurrence({ ...params, kind: cooccurrenceKind, weight_metric: cooccurrenceMetric, focus: cooccurrenceFocus, max_nodes: 80 }), refetchInterval: 30000 });
  const relationships = useQuery({ queryKey: ["tm-relationships", params, entityType], queryFn: () => api.textMiningRelationships({ ...params, entity_type: entityType }), refetchInterval: 30000 });
  const bursts = useQuery({ queryKey: ["tm-bursts", params, recentWindow, baselineWindow], queryFn: () => api.textMiningBursts({ ...params, recent_window_days: recentWindow, baseline_window_days: baselineWindow, min_count: 2 }), refetchInterval: 30000 });
  const entityProviders = useQuery({ queryKey: ["entity-providers"], queryFn: api.entityProviders, refetchInterval: 30000 });
  const entityRuns = useQuery({ queryKey: ["entity-runs"], queryFn: () => api.entityExtractionRuns({ limit: 10 }), refetchInterval: 30000 });
  const entityCompare = useQuery({ queryKey: ["entity-compare"], queryFn: () => api.compareEntityExtraction({}), refetchInterval: 30000 });
  const runEntityFallback = useMutation({
    mutationFn: () => api.runEntityExtraction({ provider: "fallback", activate: true, ...params }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tm-entities"] }),
        queryClient.invalidateQueries({ queryKey: ["entity-providers"] }),
        queryClient.invalidateQueries({ queryKey: ["entity-runs"] }),
        queryClient.invalidateQueries({ queryKey: ["entity-compare"] }),
        queryClient.invalidateQueries({ queryKey: ["facets"] }),
      ]);
    },
  });
  const latestAssignments = useQuery({ queryKey: ["tm-assignments-latest"], queryFn: () => api.textMiningAssignmentsLatest({ limit: 100 }), refetchInterval: 30000 });
  const persistAssignments = useMutation({
    mutationFn: () => api.textMiningPersistAssignments({ ...params, assignment_type: "both", topic_method: topicMethod, cluster_method: clusterMethod, n_topics: 5, n_clusters: 5 }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["tm-assignments-latest"] }),
        queryClient.invalidateQueries({ queryKey: ["facets"] }),
      ]);
    },
  });

  const exportSection = active === "similarity" ? "overview" : active === "co-occurrence" ? "co_occurrence" : active;

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3" data-tour-id="text-mining-overview">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{t("page.textMining.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("page.textMining.subtitle")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={persistAssignments.isPending} onClick={() => persistAssignments.mutate()}>
            <Save className="h-4 w-4" />
            Persist Assignments
          </Button>
          <ExportButton href={api.textMiningExportUrl({ ...params, section: exportSection, format: "json" })} label="JSON" />
          <ExportButton href={api.textMiningExportUrl({ ...params, section: exportSection, format: "csv" })} label="CSV" />
          <ExportButton href={api.textMiningExportUrl({ ...params, section: exportSection, format: "markdown" })} label="Markdown" />
        </div>
      </div>

      <Card>
        <CardHeader eyebrow="Filters" title="Corpus filters" />
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
      {persistAssignments.error ? <div className="rounded-md border border-danger-border bg-danger-soft p-3 text-sm text-danger-text">{String(persistAssignments.error.message)}</div> : null}
      <Card tone="magenta">
        <CardHeader eyebrow="Persistence" title="Latest topic/cluster assignment run" action={<StatusBadge status={latestAssignments.data?.status ?? "pending"} />} />
        {latestAssignments.data?.runs?.length ? (
          <div className="grid gap-3 md:grid-cols-4">
            <InsightCard title="Runs" metric={String(latestAssignments.data.runs.length)} detail="Persisted assignment runs." />
            <InsightCard title="Assignments" metric={String(latestAssignments.data.total_documents)} detail="Rows in latest run preview." />
            <InsightCard title="Latest Run" metric={String(latestAssignments.data.runs[0].run_id ?? "-")} detail="Used by Articles topic/cluster facets." />
            <InsightCard title="Status" metric={String(latestAssignments.data.runs[0].status ?? "-")} detail="Ready runs are searchable." />
          </div>
        ) : (
          <EmptyState title="No persisted assignments yet" detail="Click Persist Assignments after NLP/topic modeling is ready to enable topic and cluster facets in Articles." />
        )}
      </Card>

      <ScrollableTabs tabs={[...tabs]} active={active} onChange={(tab) => update({ tab })} />

      {active === "overview" ? <Overview data={overview.data} loading={overview.isLoading} /> : null}
      {active === "keywords" ? <KeywordExplorer data={overview.data} loading={overview.isLoading} /> : null}
      {active === "tfidf" ? <Tfidf data={tfidf.data} loading={tfidf.isLoading} /> : null}
      {active === "ngrams" ? <Ngrams data={ngrams.data} loading={ngrams.isLoading} n={ngramN} setN={(value) => update({ ngram: value })} /> : null}
      {active === "topics" ? <Topics data={topics.data} loading={topics.isLoading} method={topicMethod} setMethod={(value) => update({ topic_method: value })} onTopic={(id) => update({ topic_id: id, cluster_id: "" })} /> : null}
      {active === "clusters" ? <Clusters data={clusters.data} loading={clusters.isLoading} method={clusterMethod} setMethod={(value) => update({ cluster_method: value })} onCluster={(id) => update({ cluster_id: id, topic_id: "" })} /> : null}
      {active === "similarity" ? <Similarity data={similarity.data} loading={similarity.isLoading} query={query} setQuery={(value) => update({ query: value })} articleId={articleId} setArticleId={(value) => update({ article_id: value })} /> : null}
      {active === "network" ? <NetworkTab data={network.data} loading={network.isLoading} type={networkType} setType={(value) => update({ network_type: value })} /> : null}
      {active === "entities" ? <EntityIntelligence data={entities.data} providers={entityProviders.data} runs={entityRuns.data} compare={entityCompare.data} loading={entities.isLoading} running={runEntityFallback.isPending} selectedEntity={entity} selectedType={entityType} setEntity={(value) => update({ tab: "entities", entity: value })} setType={(value) => update({ tab: "entities", entity_type: value })} clear={() => update({ entity: "", entity_type: "" })} runFallback={() => runEntityFallback.mutate()} /> : null}
      {active === "collocations" ? <CollocationsTab data={collocations.data} loading={collocations.isLoading} metric={collocationMetric} level={collocationLevel} ngramType={collocationNgram} windowSize={collocationWindow} setMetric={(value) => update({ collocation_metric: value })} setLevel={(value) => update({ collocation_level: value })} setNgramType={(value) => update({ collocation_ngram: value })} setWindowSize={(value) => update({ collocation_window: value })} onCollocation={(value) => update({ query: value, tab: "similarity" })} /> : null}
      {active === "co-occurrence" ? <CooccurrenceTab data={cooccurrence.data} loading={cooccurrence.isLoading} kind={cooccurrenceKind} metric={cooccurrenceMetric} focus={cooccurrenceFocus} setKind={(value) => update({ co_kind: value })} setMetric={(value) => update({ co_metric: value })} setFocus={(value) => update({ focus: value })} /> : null}
      {active === "relationships" ? <RelationshipsTab data={relationships.data} loading={relationships.isLoading} selectedType={entityType} setType={(value) => update({ entity_type: value })} onEntity={(value) => update({ tab: "relationships", entity_type: "", focus: value })} /> : null}
      {active === "bursts" ? <BurstsTab data={bursts.data} loading={bursts.isLoading} recentWindow={recentWindow} baselineWindow={baselineWindow} setRecentWindow={(value) => update({ recent_window: value })} setBaselineWindow={(value) => update({ baseline_window: value })} onTerm={(value) => update({ query: value, tab: "similarity" })} /> : null}
      {topicId ? <TopicDrilldownModal topicId={topicId} data={topics.data} onClose={() => update({ topic_id: "" })} /> : null}
      {clusterId ? <ClusterDrilldownModal clusterId={clusterId} data={clusters.data} onClose={() => update({ cluster_id: "" })} /> : null}
      {entity && active === "entities" ? <EntityDrilldownModal entity={entity} data={entities.data} onClose={() => update({ entity: "" })} /> : null}
    </div>
  );
}

function Overview({ data, loading }: { data: Awaited<ReturnType<typeof api.textMiningOverview>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading text mining overview" />;
  if (!data) return <EmptyState title="No text mining data" />;
  const coverageRows = Object.entries(data.coverage ?? {}).map(([label, value]) => ({ label, value }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Filtered documents in corpus." />
        <InsightCard title="NLP documents" metric={String(data.coverage.nlp_documents ?? 0)} detail="Documents with tokens." />
        <InsightCard title="Sources" metric={String(data.coverage.sources ?? 0)} detail="Distinct source coverage." />
        <InsightCard title="Entities" metric={String(data.coverage.entity_documents ?? 0)} detail="Documents with entity outputs." />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card><CardHeader eyebrow="Keywords" title="Top keywords" /><BarChartBlock data={data.top_keywords} xKey="keyword" yKey="score" fill="var(--chart-1)" /></Card>
        <Card><CardHeader eyebrow="N-grams" title="Top bigrams" /><BarChartBlock data={data.top_ngrams} xKey="ngram" yKey="count" fill="var(--chart-2)" /></Card>
        <Card><CardHeader eyebrow="Entities" title="Entity preview" />{data.top_entities.length ? <BarChartBlock data={data.top_entities} xKey="entity" yKey="count" fill="var(--chart-4)" /> : <EmptyState title="No entities available" />}</Card>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <AdvancedChartCard eyebrow="Corpus Language" title="Keyword cloud" insight="Word size emphasizes important extracted keywords across the filtered corpus." metric={`${data.top_keywords.length} terms`} rows={data.top_keywords} exportName="text-mining-overview-keyword-cloud">
          <WordCloudChart data={data.top_keywords} nameKey="keyword" valueKey="score" exportName="text-mining-overview-keyword-cloud" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Coverage" title="NLP coverage radar" insight="Coverage dimensions reveal whether the corpus is ready for deeper text mining and relationship analysis." metric={`${data.total_documents} docs`} rows={coverageRows} exportName="text-mining-overview-coverage-radar">
          <RadarMetricChart rows={coverageRows} exportName="text-mining-overview-coverage-radar" />
        </AdvancedChartCard>
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function KeywordExplorer({ data, loading }: { data: Awaited<ReturnType<typeof api.textMiningOverview>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading keyword explorer" />;
  if (!data) return <EmptyState title="No keyword data" />;
  const keywordRows = data.top_keywords.map((item, index) => ({ ...item, rank: index + 1, score_rank: Number(item.score ?? 0) / Math.max(1, Number(data.top_keywords[0]?.score ?? 1)) }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <InsightCard title="Keywords" metric={String(data.top_keywords.length)} detail="Ranked extracted terms." />
        <InsightCard title="Top Score" metric={String(data.top_keywords[0]?.score ?? 0)} detail={String(data.top_keywords[0]?.keyword ?? "No dominant term")} />
        <InsightCard title="Entity Preview" metric={String(data.top_entities.length)} detail="Entity candidates available for relationship mining." />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <AdvancedChartCard eyebrow="Keyword Explorer" title="Semantic keyword cloud" insight="A dense word cloud helps scan the language fingerprint before moving into TF-IDF or collocation analysis." metric={`${keywordRows.length} keywords`} rows={keywordRows} exportName="text-mining-keyword-cloud">
          <WordCloudChart data={keywordRows} nameKey="keyword" valueKey="score" exportName="text-mining-keyword-cloud" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Ranking Shape" title="Keyword score curve" insight="The curve shows whether the corpus is dominated by a few terms or spread across many themes." metric="Score vs rank" rows={keywordRows} exportName="text-mining-keyword-score-curve">
          <BubbleScatterChart rows={keywordRows} xKey="rank" yKey="score" sizeKey="score" labelKey="keyword" exportName="text-mining-keyword-score-curve" />
        </AdvancedChartCard>
      </div>
      <Table title="Keyword Ranking" rows={keywordRows} />
      <Notes notes={data.notes} />
    </div>
  );
}

function Tfidf({ data, loading }: { data: Awaited<ReturnType<typeof api.textMiningTfidf>> | undefined; loading: boolean }) {
  if (loading) return <EmptyState title="Loading TF-IDF" />;
  if (!data) return <EmptyState title="No TF-IDF data" />;
  const rows = data.top_terms.map((item, index) => ({ ...item, rank: index + 1 }));
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Documents used for TF-IDF." />
        <InsightCard title="Vocabulary" metric={String(data.vocabulary_size)} detail="Terms in vectorizer vocabulary." />
        <InsightCard title="Status" metric={data.status} detail="TF-IDF readiness state." />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <AdvancedChartCard eyebrow="TF-IDF" title="Weighted term cloud" insight="TF-IDF highlights corpus terms that carry more discriminative information than raw frequency." metric={`${data.vocabulary_size} vocabulary`} rows={rows} exportName="text-mining-tfidf-cloud">
          <WordCloudChart data={rows} nameKey="term" valueKey="weight" exportName="text-mining-tfidf-cloud" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Term Diagnostics" title="TF-IDF rank vs weight" insight="This view makes outliers visible: terms with unusually high TF-IDF weight should explain article distinction." metric={`${rows.length} ranked terms`} rows={rows} exportName="text-mining-tfidf-bubble">
          <BubbleScatterChart rows={rows} xKey="rank" yKey="weight" sizeKey="weight" labelKey="term" exportName="text-mining-tfidf-bubble" />
        </AdvancedChartCard>
      </div>
      <Card><CardHeader eyebrow="TF-IDF" title="Top weighted terms" /><BarChartBlock data={data.top_terms} xKey="term" yKey="weight" fill="var(--chart-1)" /></Card>
      <Table title="Document Top Terms" rows={data.document_terms.map((item) => ({ article_id: item.article_id, terms: item.terms.map((term) => term.term).join(", ") }))} />
      <Notes notes={data.notes} />
    </div>
  );
}

function Ngrams({ data, loading, n, setN }: { data: Awaited<ReturnType<typeof api.textMiningNgrams>> | undefined; loading: boolean; n: string; setN: (value: string) => void }) {
  if (loading) return <EmptyState title="Loading n-grams" />;
  if (!data) return <EmptyState title="No n-gram data" />;
  return (
    <div className="space-y-5">
      <Card><CardHeader eyebrow="Controls" title="N-gram size" /><Select value={n} onChange={(event) => setN(event.target.value)}><option value="1">Unigram</option><option value="2">Bigram</option><option value="3">Trigram</option></Select></Card>
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <AdvancedChartCard eyebrow="N-grams" title={`${data.n}-gram phrase cloud`} insight="Phrase size emphasizes repeated language patterns and repeated framing in the news corpus." metric={`${data.ngrams.length} phrases`} rows={data.ngrams} exportName="text-mining-ngram-cloud">
          <WordCloudChart data={data.ngrams} nameKey="ngram" valueKey="count" exportName="text-mining-ngram-cloud" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Source Matrix" title="N-gram by source matrix" insight="This matrix shows whether phrases are source-specific or broadly shared across outlets." metric={`${data.by_source.length} pairs`} rows={data.by_source} exportName="text-mining-ngram-source-matrix">
          <MatrixHeatmapChart rows={data.by_source} xKey="ngram" yKey="source" exportName="text-mining-ngram-source-matrix" />
        </AdvancedChartCard>
      </div>
      <Card><CardHeader eyebrow="N-grams" title={`Top ${data.n}-grams`} /><BarChartBlock data={data.ngrams} xKey="ngram" yKey="count" fill="var(--chart-2)" /></Card>
      <AdvancedChartCard eyebrow="Category Matrix" title="N-gram by category matrix" insight="Category concentration reveals which repeated phrases define each news category." metric={`${data.by_category.length} pairs`} rows={data.by_category} exportName="text-mining-ngram-category-matrix">
        <MatrixHeatmapChart rows={data.by_category} xKey="ngram" yKey="category" exportName="text-mining-ngram-category-matrix" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-2"><Table title="By Source" rows={data.by_source} /><Table title="By Category" rows={data.by_category} /></div>
      <Notes notes={data.notes} />
    </div>
  );
}

function Topics({ data, loading, method, setMethod, onTopic }: { data: Awaited<ReturnType<typeof api.textMiningTopics>> | undefined; loading: boolean; method: string; setMethod: (value: string) => void; onTopic: (id: number) => void }) {
  if (loading) return <EmptyState title="Loading topics" />;
  if (!data) return <EmptyState title="No topic data" />;
  const rows = data.topics.map((topic) => ({ topic_id: topic.topic_id, terms: topic.top_terms.map((term) => term.term).join(", "), docs: topic.top_docs.map((doc) => doc.article_id).join(", ") }));
  const matrixRows = topicMatrixRows(data.topics);
  return (
    <div className="space-y-5">
      <Card><CardHeader eyebrow="Controls" title="Topic model" /><Select value={method} onChange={(event) => setMethod(event.target.value)}><option value="nmf">NMF</option><option value="lda">LDA</option></Select></Card>
      <AdvancedChartCard
        eyebrow="Topic Modeling"
        title="Topic keyword matrix"
        insight="Each row is a discovered topic; stronger cells show which words explain the topic most clearly."
        metric={`${data.topics.length} topics`}
        rows={matrixRows}
        exportName="text-mining-topic-keyword-matrix"
      >
        <MatrixHeatmapChart rows={matrixRows} xKey="term" yKey="topic" valueKey="weight" exportName="text-mining-topic-keyword-matrix" />
      </AdvancedChartCard>
      <AdvancedChartCard eyebrow="Topic Shape" title="Topic term strength radar" insight="Radar compares the strongest term weights across topics to expose broad or sharply defined themes." metric="Top topic terms" rows={matrixRows} exportName="text-mining-topic-radar">
        <RadarMetricChart rows={matrixRows.slice(0, 8).map((row) => ({ label: `${row.topic}:${row.term}`, value: Number(row.weight ?? 0) }))} exportName="text-mining-topic-radar" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        {data.topics.map((topic) => (
          <Card key={topic.topic_id} tone="secondary">
            <CardHeader eyebrow={`Topic ${topic.topic_id}`} title={topic.top_terms.slice(0, 3).map((term) => term.term).join(" / ") || "Untitled topic"} />
            <div className="flex flex-wrap gap-2">
              {topic.top_terms.map((term) => <span key={term.term} className="rounded-full bg-secondary-soft px-2 py-1 text-xs font-semibold text-info-text">{term.term} {term.weight}</span>)}
            </div>
            <div className="mt-4 space-y-2">
              {topic.top_docs.map((doc) => <a key={doc.article_id} href={`/articles/${encodeURIComponent(doc.article_id)}`} className="block rounded-md border border-line bg-surface-subtle px-3 py-2 text-xs font-semibold text-primary-active">Article {doc.article_id} · {doc.weight}</a>)}
            </div>
            <Button className="mt-4" variant="secondary" onClick={() => onTopic(topic.topic_id)}>Open topic drill-down</Button>
          </Card>
        ))}
      </div>
      <Table title="Topic table" rows={rows} />
      <Notes notes={data.notes} />
    </div>
  );
}

function Clusters({ data, loading, method, setMethod, onCluster }: { data: Awaited<ReturnType<typeof api.textMiningClusters>> | undefined; loading: boolean; method: string; setMethod: (value: string) => void; onCluster: (id: number) => void }) {
  if (loading) return <EmptyState title="Loading clusters" />;
  if (!data) return <EmptyState title="No cluster data" />;
  const rows = data.clusters.map((cluster) => ({ cluster_id: cluster.cluster_id, size: cluster.size, terms: cluster.top_terms.map((term) => term.term).join(", "), examples: cluster.examples.map((item) => item.title || item.article_id).join(" | ") }));
  const points = data.clusters.flatMap((cluster) => cluster.points ?? []);
  const clusterTerms = data.clusters.flatMap((cluster) => cluster.top_terms.map((term) => ({ cluster: `Cluster ${cluster.cluster_id}`, term: term.term, weight: term.weight })));
  return <div className="space-y-5"><Card><CardHeader eyebrow="Controls" title="Cluster model" /><Select value={method} onChange={(event) => setMethod(event.target.value)}><option value="kmeans">KMeans</option><option value="hierarchical">Hierarchical</option></Select></Card><div className="grid gap-4 md:grid-cols-2"><InsightCard title="Clusters" metric={String(data.metrics.n_clusters ?? data.clusters.length)} detail="Generated cluster groups." /><InsightCard title="Silhouette" metric={String(data.metrics.silhouette ?? "-")} detail="Higher is better when available." /></div><div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]"><AdvancedChartCard eyebrow="Clustering" title="Cluster projection" insight="TF-IDF vectors are projected into two dimensions; nearby points represent articles with similar wording." metric={`${points.length} articles`} rows={points} exportName="text-mining-cluster-projection"><ClusterProjectionChart points={points} exportName="text-mining-cluster-projection" onSelect={(point) => onCluster(Number(point.cluster_id))} /></AdvancedChartCard><AdvancedChartCard eyebrow="Cluster Terms" title="Cluster-term matrix" insight="Term concentration explains what each generated cluster is about." metric={`${clusterTerms.length} terms`} rows={clusterTerms} exportName="text-mining-cluster-term-matrix"><MatrixHeatmapChart rows={clusterTerms} xKey="term" yKey="cluster" valueKey="weight" exportName="text-mining-cluster-term-matrix" /></AdvancedChartCard></div><Table title="Clusters" rows={rows} /><Notes notes={data.notes} /></div>;
}

function Similarity({ data, loading, query, setQuery, articleId, setArticleId }: { data: Awaited<ReturnType<typeof api.textMiningSimilarity>> | undefined; loading: boolean; query: string; setQuery: (value: string) => void; articleId: string; setArticleId: (value: string) => void }) {
  const rows = (data?.results ?? []).map((item) => ({ ...item, open: `/articles/${item.article_id}` }));
  return <div className="space-y-5"><Card><CardHeader eyebrow="Search" title="Similarity inputs" /><div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]"><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="query terms" /><Input value={articleId} onChange={(event) => setArticleId(event.target.value)} placeholder="article_id overrides query" /><div className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Search className="h-4 w-4" />Live</div></div></Card>{loading ? <EmptyState title="Loading similarity" /> : <Table title="Similar Articles" rows={rows} />}<Notes notes={data?.notes ?? []} /></div>;
}

function NetworkTab({ data, loading, type, setType }: { data: Awaited<ReturnType<typeof api.textMiningNetwork>> | undefined; loading: boolean; type: string; setType: (value: string) => void }) {
  if (loading) return <EmptyState title="Loading network" />;
  if (!data) return <EmptyState title="No network data" />;
  return <div className="space-y-5"><Card><CardHeader eyebrow="Controls" title="Network type" /><Select value={type} onChange={(event) => setType(event.target.value)}><option value="keyword">Keyword</option><option value="entity">Entity</option></Select></Card><div className="grid gap-4 md:grid-cols-3"><InsightCard title="Nodes" metric={String(data.nodes.length)} detail="Terms or entities in graph." /><InsightCard title="Edges" metric={String(data.edges.length)} detail="Co-occurrence links." /><InsightCard title="Type" metric={data.type} detail="Current network mode." /></div><AdvancedChartCard eyebrow={data.type === "entity" ? "Entity Co-occurrence" : "Keyword Network"} title={data.type === "entity" ? "Entity force graph" : "Keyword force graph"} insight="Force layout exposes dense communities and important hubs more clearly than a flat node list." metric={`${data.nodes.length} nodes / ${data.edges.length} edges`} rows={[...data.nodes, ...data.edges]} exportName={`text-mining-${data.type}-force-network`}><ForceGraphChart nodes={data.nodes} edges={data.edges} exportName={`text-mining-${data.type}-force-network`} /></AdvancedChartCard><AdvancedChartCard eyebrow="Network Metrics" title="Node centrality radar" insight="Centrality distribution shows whether a few terms dominate the network or influence is more balanced." metric={`${data.nodes.length} nodes`} rows={data.nodes} exportName={`text-mining-${data.type}-centrality-radar`}><RadarMetricChart rows={data.nodes.slice(0, 8).map((node) => ({ label: node.label, value: node.centrality ?? node.degree }))} exportName={`text-mining-${data.type}-centrality-radar`} /></AdvancedChartCard><div className="grid gap-4 lg:grid-cols-2"><Table title="Nodes" rows={data.nodes} /><Table title="Edges" rows={data.edges} /></div><Notes notes={data.notes} /></div>;
}

function EntityIntelligence({
  data,
  providers,
  runs,
  compare,
  loading,
  running,
  selectedEntity,
  selectedType,
  setEntity,
  setType,
  clear,
  runFallback,
}: {
  data: Awaited<ReturnType<typeof api.textMiningEntities>> | undefined;
  providers: Awaited<ReturnType<typeof api.entityProviders>> | undefined;
  runs: Awaited<ReturnType<typeof api.entityExtractionRuns>> | undefined;
  compare: Awaited<ReturnType<typeof api.compareEntityExtraction>> | undefined;
  loading: boolean;
  running: boolean;
  selectedEntity: string;
  selectedType: string;
  setEntity: (value: string) => void;
  setType: (value: string) => void;
  clear: () => void;
  runFallback: () => void;
}) {
  if (loading) return <EmptyState title="Loading entity intelligence" />;
  if (!data) return <EmptyState title="No entity intelligence data" />;
  const sourceHeatmap = matrixRowsToHeatmap(data.entity_source_matrix, "source", "entity");
  const categoryHeatmap = matrixRowsToHeatmap(data.entity_category_matrix, "category", "entity");
  const typeOptions = data.entity_type_distribution.map((item) => item.type);
  const selected = [selectedEntity && `Entity: ${selectedEntity}`, selectedType && `Type: ${selectedType}`].filter(Boolean).join(" · ");
  return (
    <div className="space-y-5">
      <Card tone="secondary">
        <CardHeader
          eyebrow="NER Source"
          title="Entity extraction strategy"
          action={<StatusBadge status={data.active_entity_source || providers?.active_entity_source || "fallback"} />}
        />
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="grid gap-3 md:grid-cols-3">
            {(providers?.providers ?? data.provider_status ?? []).map((provider) => (
              <div key={provider.provider} className="rounded-md border border-line bg-surface-subtle p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-ink">{provider.provider}</span>
                  <StatusBadge status={provider.available ? "ready" : provider.status} />
                </div>
                <p className="mt-2 text-xs leading-5 text-muted">{provider.detail}</p>
                {provider.model ? <p className="numeric mt-2 text-xs text-muted">model: {provider.model}</p> : null}
              </div>
            ))}
          </div>
          <div className="rounded-md border border-info-border bg-info-soft p-4">
            <div className="text-sm font-semibold text-info-text">Active output</div>
            <div className="mt-2 numeric text-2xl font-semibold text-ink">{data.active_entity_source || "fallback"}</div>
            <p className="mt-1 text-xs text-muted">Run: {data.active_run_id || providers?.active_run_id || "not persisted"}</p>
            <Button className="mt-4" type="button" disabled={running} onClick={runFallback}>
              <Play className="h-4 w-4" />
              Run Fallback Extraction
            </Button>
          </div>
        </div>
      </Card>
      <Card tone="accent">
        <CardHeader eyebrow="Quality Comparison" title="Entity extraction run comparison" />
        {compare?.status === "ready" ? (
          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-1">
              <InsightCard title="Overlap Articles" metric={String(compare.metrics.overlap_articles ?? 0)} detail="Articles shared by compared runs." />
              <InsightCard title="Avg Jaccard" metric={String(compare.metrics.avg_jaccard ?? 0)} detail="Entity overlap; higher means similar outputs." />
              <InsightCard title="Left Only" metric={String(compare.metrics.left_only_entities ?? 0)} detail="Entities only found by the newer run." />
              <InsightCard title="Right Only" metric={String(compare.metrics.right_only_entities ?? 0)} detail="Entities only found by the baseline run." />
            </div>
            <div className="space-y-4">
              <Table title="Run Diff Samples" rows={compare.sample_diffs} />
              <Table title="Type Distribution Diff" rows={compare.type_distribution} />
            </div>
          </div>
        ) : (
          <EmptyState title="No run comparison yet" detail="Run fallback extraction, then run another provider such as CKIP or spaCy to compare entity quality." />
        )}
        {runs?.runs?.length ? <Table title="Recent Entity Extraction Runs" rows={runs.runs.map((run) => ({ run_id: run.run_id, provider: run.provider, strategy: run.strategy, status: run.status, created_at: run.created_at || "" }))} /> : null}
      </Card>
      <Card tone="info">
        <CardHeader eyebrow="Controls" title="Entity filters" />
        <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <Input value={selectedEntity} onChange={(event) => setEntity(event.target.value)} placeholder="Filter by entity" />
          <Select value={selectedType} onChange={(event) => setType(event.target.value)}>
            <option value="">All entity types</option>
            {typeOptions.map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Button type="button" variant="secondary" onClick={clear}>Clear</Button>
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Filtered article base." />
        <InsightCard title="Entities" metric={String(data.entity_frequency.length)} detail="Ranked entity candidates." />
        <InsightCard title="Types" metric={String(data.entity_type_distribution.length)} detail="Entity classes in current view." />
        <InsightCard title="Links" metric={String(data.cooccurrence_edges.length)} detail="Co-occurrence relationships." />
      </div>
      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <AdvancedChartCard
          eyebrow="Entity Intelligence"
          title="Entity frequency ranking"
          insight="Ranked entities summarize who, where, and what appears most often in the filtered news corpus."
          metric={`${data.entity_frequency.length} entities`}
          rows={data.entity_frequency}
          exportName="text-mining-entity-frequency"
          selectedSummary={selected || undefined}
          onClearSelection={clear}
        >
          <HorizontalBarChartBlock data={data.entity_frequency.slice(0, 18)} xKey="count" yKey="entity" fill="var(--chart-4)" onSelect={(row) => setEntity(String(row.entity ?? ""))} />
        </AdvancedChartCard>
        <AdvancedChartCard
          eyebrow="Entity Network"
          title="Entity co-occurrence graph"
          insight="Nodes are entities and edges show entities that appear together in the same article."
          metric={`${data.cooccurrence_nodes.length} nodes`}
          rows={[...data.cooccurrence_nodes, ...data.cooccurrence_edges]}
          exportName="text-mining-entity-intelligence-network"
          selectedSummary={selected || undefined}
          onClearSelection={clear}
        >
          <NetworkGraphChart nodes={data.cooccurrence_nodes} edges={data.cooccurrence_edges} exportName="text-mining-entity-intelligence-network" onSelect={(node) => setEntity(node.label || node.id)} />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard
          eyebrow="Source Matrix"
          title="Entity by source heatmap"
          insight="This matrix shows which sources repeatedly mention each entity, useful for share-of-voice monitoring."
          metric={`${data.entity_source_matrix.length} pairs`}
          rows={data.entity_source_matrix}
          exportName="text-mining-entity-source-heatmap"
          selectedSummary={selected || undefined}
          onClearSelection={clear}
        >
          <HeatmapChart xLabels={sourceHeatmap.xLabels} yLabels={sourceHeatmap.yLabels} values={sourceHeatmap.values} exportName="text-mining-entity-source-heatmap" onSelect={(item) => setEntity(item.xLabel)} />
        </AdvancedChartCard>
        <AdvancedChartCard
          eyebrow="Category Matrix"
          title="Entity by category heatmap"
          insight="Entity-category concentration helps explain which topics are tied to specific categories."
          metric={`${data.entity_category_matrix.length} pairs`}
          rows={data.entity_category_matrix}
          exportName="text-mining-entity-category-heatmap"
          selectedSummary={selected || undefined}
          onClearSelection={clear}
        >
          <HeatmapChart xLabels={categoryHeatmap.xLabels} yLabels={categoryHeatmap.yLabels} values={categoryHeatmap.values} exportName="text-mining-entity-category-heatmap" onSelect={(item) => setEntity(item.xLabel)} />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Entity Type Distribution" rows={data.entity_type_distribution} />
        <Table title="Entity Trend" rows={data.entity_trend} />
      </div>
      <Table title="Representative Articles" rows={data.representative_articles.map((item) => ({ ...item, open: `/articles/${item.article_id}` }))} />
      <Notes notes={data.notes} />
    </div>
  );
}

function CollocationsTab({
  data,
  loading,
  metric,
  level,
  ngramType,
  windowSize,
  setMetric,
  setLevel,
  setNgramType,
  setWindowSize,
  onCollocation,
}: {
  data: Awaited<ReturnType<typeof api.textMiningCollocations>> | undefined;
  loading: boolean;
  metric: string;
  level: string;
  ngramType: string;
  windowSize: string;
  setMetric: (value: string) => void;
  setLevel: (value: string) => void;
  setNgramType: (value: string) => void;
  setWindowSize: (value: string) => void;
  onCollocation: (value: string) => void;
}) {
  if (loading) return <EmptyState title="Loading collocation analysis" />;
  if (!data) return <EmptyState title="No collocation data" />;
  return (
    <div className="space-y-5">
      <Card tone="info">
        <CardHeader eyebrow="Controls" title="Collocation settings" />
        <div className="grid gap-3 md:grid-cols-4">
          <Select value={metric} onChange={(event) => setMetric(event.target.value)}>
            <option value="npmi">NPMI</option>
            <option value="pmi">PMI</option>
            <option value="ppmi">PPMI</option>
            <option value="log_likelihood">Log-likelihood</option>
            <option value="dice">Dice</option>
            <option value="t_score">T-score</option>
            <option value="frequency">Frequency</option>
          </Select>
          <Select value={level} onChange={(event) => setLevel(event.target.value)}>
            <option value="sentence">Sentence-level</option>
            <option value="document">Document-level</option>
            <option value="window">Sliding window</option>
          </Select>
          <Select value={ngramType} onChange={(event) => setNgramType(event.target.value)}>
            <option value="bigram">Bigram pairs</option>
            <option value="trigram">Trigram phrases</option>
          </Select>
          <Select value={windowSize} onChange={(event) => setWindowSize(event.target.value)}>
            <option value="2">Window 2</option>
            <option value="3">Window 3</option>
            <option value="5">Window 5</option>
            <option value="10">Window 10</option>
          </Select>
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Filtered corpus size." />
        <InsightCard title="Collocations" metric={String(data.collocations.length)} detail="Pairs or phrases above threshold." />
        <InsightCard title="Metric" metric={data.metric.toUpperCase()} detail="Current ranking score." />
        <InsightCard title="Level" metric={data.level} detail="Co-occurrence scope." />
      </div>
      <AdvancedChartCard eyebrow="Collocation Ranking" title="Ranked collocations" insight="High scoring terms appear together more strongly than expected from their individual frequencies." metric={`${data.collocations.length} rows`} rows={data.collocations} exportName="text-mining-collocation-ranking">
        <HorizontalBarChartBlock data={data.collocations.slice(0, 18)} xKey="score" yKey="collocation" fill="var(--chart-3)" onSelect={(row) => onCollocation(String(row.collocation ?? ""))} />
      </AdvancedChartCard>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Association Matrix" title="Collocation heatmap" insight="Cells highlight strong term-pair associations in the current corpus." metric={`${data.heatmap.length} cells`} rows={data.heatmap} exportName="text-mining-collocation-heatmap">
          <MatrixHeatmapChart rows={data.heatmap} xKey="term_b" yKey="term_a" valueKey="score" exportName="text-mining-collocation-heatmap" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Time Distribution" title="Collocation trend line" insight="Trend counts show when top collocations appear in the publication timeline." metric={`${data.trend.length} observations`} rows={data.trend} exportName="text-mining-collocation-trend">
          <LineChartBlock data={rollupTrend(data.trend, "date", "count")} xKey="date" yKey="count" />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Source Matrix" title="Source-collocation matrix" insight="Shows which sources repeatedly use specific collocated terms." metric={`${data.source_matrix.length} pairs`} rows={data.source_matrix} exportName="text-mining-source-collocation-matrix">
          <MatrixHeatmapChart rows={data.source_matrix} xKey="collocation" yKey="source" exportName="text-mining-source-collocation-matrix" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Category Matrix" title="Category-collocation matrix" insight="Shows category-specific language patterns and phrase concentration." metric={`${data.category_matrix.length} pairs`} rows={data.category_matrix} exportName="text-mining-category-collocation-matrix">
          <MatrixHeatmapChart rows={data.category_matrix} xKey="collocation" yKey="category" exportName="text-mining-category-collocation-matrix" />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard eyebrow="Scoring Diagnostics" title="Collocation metric landscape" insight="Bubble position compares association score and raw support, making unstable high-PMI pairs easier to spot." metric={`${data.collocations.length} ranked rows`} rows={data.collocations} exportName="text-mining-collocation-bubble">
        <BubbleScatterChart rows={data.collocations} xKey="count" yKey="score" sizeKey="frequency" labelKey="collocation" exportName="text-mining-collocation-bubble" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Collocation table" rows={data.collocations} />
        <Table title="Example articles" rows={data.examples.map((item) => ({ ...item, open: `/articles/${item.article_id}` }))} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function CooccurrenceTab({
  data,
  loading,
  kind,
  metric,
  focus,
  setKind,
  setMetric,
  setFocus,
}: {
  data: Awaited<ReturnType<typeof api.textMiningCooccurrence>> | undefined;
  loading: boolean;
  kind: string;
  metric: string;
  focus: string;
  setKind: (value: string) => void;
  setMetric: (value: string) => void;
  setFocus: (value: string) => void;
}) {
  if (loading) return <EmptyState title="Loading co-occurrence graph" />;
  if (!data) return <EmptyState title="No co-occurrence data" />;
  return (
    <div className="space-y-5">
      <Card tone="secondary">
        <CardHeader eyebrow="Controls" title="Network settings" />
        <div className="grid gap-3 md:grid-cols-3">
          <Select value={kind} onChange={(event) => setKind(event.target.value)}><option value="keyword">Keyword</option><option value="entity">Entity</option></Select>
          <Select value={metric} onChange={(event) => setMetric(event.target.value)}><option value="npmi">NPMI</option><option value="pmi">PMI</option><option value="jaccard">Jaccard</option><option value="count">Count</option></Select>
          <Input value={focus} onChange={(event) => setFocus(event.target.value)} placeholder="Focus node / ego network" />
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Nodes" metric={String(data.nodes.length)} detail="Terms/entities in graph." />
        <InsightCard title="Edges" metric={String(data.edges.length)} detail="Weighted co-occurrence links." />
        <InsightCard title="Communities" metric={String(data.communities.length)} detail="Detected graph groups." />
        <InsightCard title="Metrics" metric={data.metrics_degraded ? "Fallback" : "Full"} detail="Network centrality availability." />
      </div>
      <AdvancedChartCard eyebrow="Interactive Network" title="Keyword/entity co-occurrence network" insight="Node size reflects mentions; color groups are communities; edge weight reflects the selected association metric." metric={`${data.nodes.length} nodes / ${data.edges.length} edges`} rows={[...data.nodes, ...data.edges]} exportName="text-mining-cooccurrence-network" selectedSummary={focus ? `Focus: ${focus}` : undefined} onClearSelection={() => setFocus("")}>
        <ForceGraphChart nodes={data.nodes} edges={data.edges} exportName="text-mining-cooccurrence-network" />
      </AdvancedChartCard>
      <AdvancedChartCard eyebrow="Graph Diagnostics" title="Centrality vs frequency" insight="This bubble view separates frequent nodes from structurally important nodes." metric={`${data.nodes.length} nodes`} rows={data.nodes} exportName="text-mining-cooccurrence-centrality-bubble">
        <BubbleScatterChart rows={data.nodes} xKey="count" yKey="centrality" sizeKey="degree" labelKey="label" exportName="text-mining-cooccurrence-centrality-bubble" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-3">
        <Table title="Top Nodes" rows={data.nodes} />
        <Table title="Top Edges" rows={data.edges} />
        <Table title="Article Matches" rows={data.article_matches.map((item) => ({ ...item, open: `/articles/${item.article_id}` }))} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function RelationshipsTab({ data, loading, selectedType, setType, onEntity }: { data: Awaited<ReturnType<typeof api.textMiningRelationships>> | undefined; loading: boolean; selectedType: string; setType: (value: string) => void; onEntity: (value: string) => void }) {
  if (loading) return <EmptyState title="Loading relationship mining" />;
  if (!data) return <EmptyState title="No relationship data" />;
  return (
    <div className="space-y-5">
      <Card tone="magenta">
        <CardHeader eyebrow="Controls" title="Entity relationship filters" action={<StatusBadge status={data.active_entity_source} />} />
        <Select value={selectedType} onChange={(event) => setType(event.target.value)}>
          <option value="">All entity types</option>
          <option value="PERSON">PERSON</option>
          <option value="ORG">ORG</option>
          <option value="LOCATION">LOCATION</option>
          <option value="EVENT">EVENT</option>
        </Select>
      </Card>
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Documents" metric={String(data.total_documents)} detail="Relationship mining base." />
        <InsightCard title="Entities" metric={String(data.entity_frequency.length)} detail="Ranked entity mentions." />
        <InsightCard title="Links" metric={String(data.entity_network_edges.length)} detail="Entity relationship edges." />
        <InsightCard title="Risk Entities" metric={String(data.risk_summary.length)} detail="Entities in risk-related context." />
      </div>
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <AdvancedChartCard eyebrow="Share of Voice" title="Entity mention share" insight="Share of voice compares entity visibility within the filtered news corpus." metric={`${data.share_of_voice.length} entities`} rows={data.share_of_voice} exportName="text-mining-entity-share-of-voice">
          <TreemapChart data={data.share_of_voice.slice(0, 18).map((item) => ({ name: String(item.entity ?? ""), value: Number(item.count ?? 0) }))} exportName="text-mining-entity-share-of-voice" onSelect={(item) => onEntity(item.name)} />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Entity Network" title="Entity relationship graph" insight="Edges connect entities mentioned in the same article, helping reveal media-monitoring relationships." metric={`${data.entity_network_nodes.length} nodes`} rows={[...data.entity_network_nodes, ...data.entity_network_edges]} exportName="text-mining-entity-relationship-network">
          <ForceGraphChart nodes={data.entity_network_nodes} edges={data.entity_network_edges} exportName="text-mining-entity-relationship-network" />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard eyebrow="Entity Language" title="Entity word cloud" insight="Entity prominence gives a fast media-monitoring view of who and what dominates the current corpus." metric={`${data.entity_frequency.length} entities`} rows={data.entity_frequency} exportName="text-mining-entity-word-cloud">
        <WordCloudChart data={data.entity_frequency} nameKey="entity" valueKey="count" exportName="text-mining-entity-word-cloud" />
      </AdvancedChartCard>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Source Matrix" title="Entity-source heatmap" insight="Identifies which sources repeatedly cover specific entities." metric={`${data.entity_source_matrix.length} pairs`} rows={data.entity_source_matrix} exportName="text-mining-relationship-source-heatmap">
          <MatrixHeatmapChart rows={data.entity_source_matrix} xKey="entity" yKey="source" exportName="text-mining-relationship-source-heatmap" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Topic Flow" title="Entity-topic Sankey" insight="Links entities to persisted topic assignments when available." metric={`${data.entity_topic_links.length} links`} rows={data.entity_topic_links} exportName="text-mining-entity-topic-sankey">
          <SankeyChart rows={data.entity_topic_links} sourceKey="entity" targetKey="topic" valueKey="count" exportName="text-mining-entity-topic-sankey" />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Category Matrix" title="Entity-category heatmap" insight="Shows which categories concentrate coverage around each entity." metric={`${data.entity_category_matrix.length} pairs`} rows={data.entity_category_matrix} exportName="text-mining-relationship-category-heatmap">
          <MatrixHeatmapChart rows={data.entity_category_matrix} xKey="entity" yKey="category" exportName="text-mining-relationship-category-heatmap" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Trend Calendar" title="Entity mention calendar" insight="Calendar intensity shows how entity coverage changes over publication dates." metric={`${data.entity_trend_calendar.length} dates`} rows={data.entity_trend_calendar} exportName="text-mining-entity-trend-calendar">
          <CalendarHeatmapChart data={data.entity_trend_calendar} exportName="text-mining-entity-trend-calendar" />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard eyebrow="Risk Monitoring" title="Entity risk mentions" insight="Risk-context mentions highlight entities appearing near crisis, investigation, warning, or controversy language." metric={`${data.risk_summary.length} entities`} rows={data.risk_summary} exportName="text-mining-entity-risk-bubble">
        <BubbleScatterChart rows={data.risk_summary.map((row, index) => ({ ...row, rank: index + 1 }))} xKey="rank" yKey="risk_mentions" sizeKey="risk_mentions" labelKey="entity" exportName="text-mining-entity-risk-bubble" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-2">
        <Table title="Entity-keyword links" rows={data.entity_keyword_links} />
        <Table title="Risk summary" rows={data.risk_summary} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function BurstsTab({ data, loading, recentWindow, baselineWindow, setRecentWindow, setBaselineWindow, onTerm }: { data: Awaited<ReturnType<typeof api.textMiningBursts>> | undefined; loading: boolean; recentWindow: string; baselineWindow: string; setRecentWindow: (value: string) => void; setBaselineWindow: (value: string) => void; onTerm: (value: string) => void }) {
  if (loading) return <EmptyState title="Loading trend and burst detection" />;
  if (!data) return <EmptyState title="No burst data" />;
  return (
    <div className="space-y-5">
      <Card tone="accent">
        <CardHeader eyebrow="Controls" title="Burst windows" />
        <div className="grid gap-3 md:grid-cols-2">
          <Select value={recentWindow} onChange={(event) => setRecentWindow(event.target.value)}><option value="3">Recent 3 days</option><option value="7">Recent 7 days</option><option value="14">Recent 14 days</option><option value="30">Recent 30 days</option></Select>
          <Select value={baselineWindow} onChange={(event) => setBaselineWindow(event.target.value)}><option value="14">Baseline 14 days</option><option value="30">Baseline 30 days</option><option value="60">Baseline 60 days</option><option value="90">Baseline 90 days</option></Select>
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-4">
        <InsightCard title="Rising" metric={String(data.rising_terms.length)} detail="Terms with recent growth." />
        <InsightCard title="Burst" metric={String(data.burst_terms.length)} detail="Terms above z-score/growth threshold." />
        <InsightCard title="Declining" metric={String(data.declining_terms.length)} detail="Terms losing momentum." />
        <InsightCard title="Anomalies" metric={String(data.anomaly_timeline.filter((item) => item.is_anomaly).length)} detail="Unusual volume dates." />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Emerging Topics" title="Rising keywords" insight="Recent-window terms are compared against the baseline window to detect emerging attention." metric={`${data.rising_terms.length} terms`} rows={data.rising_terms} exportName="text-mining-rising-keywords">
          <HorizontalBarChartBlock data={data.rising_terms.slice(0, 18)} xKey="growth_rate" yKey="term" fill="var(--chart-5)" onSelect={(row) => onTerm(String(row.term ?? ""))} />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Burst Detection" title="Burst keyword z-score" insight="High z-score terms indicate unusual spikes relative to baseline coverage." metric={`${data.burst_terms.length} bursts`} rows={data.burst_terms} exportName="text-mining-burst-keywords">
          <HorizontalBarChartBlock data={data.burst_terms.slice(0, 18)} xKey="z_score" yKey="term" fill="var(--chart-7)" onSelect={(row) => onTerm(String(row.term ?? ""))} />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <AdvancedChartCard eyebrow="Burst Vocabulary" title="Burst word cloud" insight="The cloud highlights terms that are currently accelerating or spiking." metric={`${data.burst_terms.length || data.rising_terms.length} candidates`} rows={data.burst_terms.length ? data.burst_terms : data.rising_terms} exportName="text-mining-burst-word-cloud">
          <WordCloudChart data={data.burst_terms.length ? data.burst_terms : data.rising_terms} nameKey="term" valueKey={data.burst_terms.length ? "z_score" : "growth_rate"} exportName="text-mining-burst-word-cloud" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Growth Diagnostics" title="Growth vs anomaly score" insight="Terms in the upper-right are both growing and statistically unusual." metric="growth / z-score" rows={data.lifecycle} exportName="text-mining-burst-growth-bubble">
          <BubbleScatterChart rows={data.lifecycle} xKey="growth_rate" yKey="z_score" sizeKey="recent_count" labelKey="term" exportName="text-mining-burst-growth-bubble" />
        </AdvancedChartCard>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <AdvancedChartCard eyebrow="Volume Timeline" title="Article volume anomalies" insight="Dates with strong z-score shifts are potential news-cycle spikes." metric={`${data.anomaly_timeline.length} dates`} rows={data.anomaly_timeline} exportName="text-mining-volume-anomalies">
          <LineChartBlock data={data.anomaly_timeline as Row[]} xKey="date" yKey="count" />
        </AdvancedChartCard>
        <AdvancedChartCard eyebrow="Calendar" title="Publication calendar heatmap" insight="Calendar density helps spot quiet periods and concentrated news bursts." metric={`${data.calendar.length} dates`} rows={data.calendar} exportName="text-mining-burst-calendar">
          <CalendarHeatmapChart data={data.calendar} exportName="text-mining-burst-calendar" />
        </AdvancedChartCard>
      </div>
      <AdvancedChartCard eyebrow="Source Bursts" title="Source-specific burst matrix" insight="This matrix shows which outlets are driving specific rising terms." metric={`${data.source_bursts.length} pairs`} rows={data.source_bursts} exportName="text-mining-source-burst-matrix">
        <MatrixHeatmapChart rows={data.source_bursts} xKey="term" yKey="source" exportName="text-mining-source-burst-matrix" />
      </AdvancedChartCard>
      <div className="grid gap-4 lg:grid-cols-3">
        <Table title="Lifecycle classification" rows={data.lifecycle} />
        <Table title="Source-specific bursts" rows={data.source_bursts} />
        <Table title="Declining terms" rows={data.declining_terms} />
      </div>
      <Notes notes={data.notes} />
    </div>
  );
}

function BarChartBlock({ data, xKey, yKey, fill }: { data: Row[]; xKey: string; yKey: string; fill: string }) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return <div className="h-72"><ResponsiveContainer width="100%" height="100%"><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" /><XAxis dataKey={xKey} tick={{ fontSize: 12 }} /><YAxis allowDecimals={false} tick={{ fontSize: 12 }} /><Tooltip /><Bar dataKey={yKey} fill={fill} radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

function HorizontalBarChartBlock({ data, xKey, yKey, fill, onSelect }: { data: Row[]; xKey: string; yKey: string; fill: string; onSelect?: (row: Row) => void }) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return (
    <div className="h-96">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 32, right: 18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
          <YAxis type="category" dataKey={yKey} width={96} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={xKey} fill={fill} radius={[0, 3, 3, 0]} onClick={(row) => onSelect?.(row.payload as Row)} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function LineChartBlock({ data, xKey, yKey }: { data: Row[]; xKey: string; yKey: string }) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ left: 8, right: 18, top: 12, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey={yKey} stroke="var(--chart-1)" strokeWidth={2.5} dot={{ r: 2 }} activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function rollupTrend(rows: Array<Record<string, string | number | null>>, dateKey: string, countKey: string): Row[] {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    const date = String(row[dateKey] ?? "");
    if (!date) return;
    counts.set(date, (counts.get(date) ?? 0) + Number(row[countKey] ?? 0));
  });
  return Array.from(counts.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([date, count]) => ({ date, count }));
}

function Table({ title, rows }: { title: string; rows: Row[] }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 6);
  return <Card><CardHeader eyebrow="Table" title={title} />{rows.length ? <div className="overflow-x-auto"><table className="min-w-full divide-y divide-line text-sm"><thead><tr className="text-left text-xs uppercase tracking-wide text-muted">{headers.map((header) => <th key={header} className="px-3 py-2 font-semibold">{header.replaceAll("_", " ")}</th>)}</tr></thead><tbody className="divide-y divide-line">{rows.slice(0, 20).map((row, index) => <tr key={index}>{headers.map((header) => <td key={header} className="px-3 py-2 text-muted">{String(row[header] ?? "")}</td>)}</tr>)}</tbody></table></div> : <EmptyState title="No table data" />}</Card>;
}

function Notes({ notes }: { notes: string[] }) {
  if (!notes.length) return null;
  return <Card><CardHeader eyebrow="Notes" title="Caveats" /><div className="space-y-2">{notes.map((note) => <div key={note} className="rounded-md border border-line bg-surface-subtle p-3 text-sm text-muted">{note}</div>)}</div></Card>;
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

function matrixRowsToHeatmap(rows: Row[], rowKey: string, colKey: string) {
  const xLabels = Array.from(new Set(rows.map((row) => String(row[colKey] ?? "")))).slice(0, 18);
  const yLabels = Array.from(new Set(rows.map((row) => String(row[rowKey] ?? "")))).slice(0, 14);
  const values = rows
    .map((row) => [xLabels.indexOf(String(row[colKey] ?? "")), yLabels.indexOf(String(row[rowKey] ?? "")), Number(row.count ?? 0)] as [number, number, number])
    .filter(([x, y]) => x >= 0 && y >= 0);
  return { xLabels, yLabels, values };
}

function TopicDrilldownModal({ topicId, data, onClose }: { topicId: string; data: Awaited<ReturnType<typeof api.textMiningTopics>> | undefined; onClose: () => void }) {
  const topic = data?.topics.find((item) => String(item.topic_id) === String(topicId));
  return (
    <DrilldownShell title={`Topic ${topicId}`} onClose={onClose}>
      {topic ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {topic.top_terms.map((term) => <span key={term.term} className="rounded-full border border-info-border bg-info-soft px-3 py-1 text-xs font-semibold text-info-text">{term.term} · {term.weight}</span>)}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <DataBlock title="Term weights" rows={topic.top_terms.map((term) => ({ term: term.term, weight: term.weight }))} />
            <DataBlock title="Representative articles" rows={topic.top_docs.map((doc) => ({ article_id: doc.article_id, weight: doc.weight }))} articleLinks />
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/articles?topic=${encodeURIComponent(String(topic.topic_id))}`} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><ExternalLink className="h-4 w-4" />Apply to Articles facet</Link>
            <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copy link</Button>
          </div>
        </div>
      ) : (
        <EmptyState title="Topic unavailable" detail="Run topic modeling or adjust the current filters." />
      )}
    </DrilldownShell>
  );
}

function ClusterDrilldownModal({ clusterId, data, onClose }: { clusterId: string; data: Awaited<ReturnType<typeof api.textMiningClusters>> | undefined; onClose: () => void }) {
  const cluster = data?.clusters.find((item) => String(item.cluster_id) === String(clusterId));
  const points = cluster?.points ?? [];
  return (
    <DrilldownShell title={`Cluster ${clusterId}`} onClose={onClose}>
      {cluster ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <InsightCard title="Size" metric={String(cluster.size)} detail="Documents in this cluster." />
            <InsightCard title="Examples" metric={String(cluster.examples.length)} detail="Representative article preview." />
            <InsightCard title="Projection points" metric={String(points.length)} detail="Articles with 2D coordinates." />
          </div>
          <div className="flex flex-wrap gap-2">
            {cluster.top_terms.map((term) => <span key={term.term} className="rounded-full border border-primary/25 bg-primary-soft-2 px-3 py-1 text-xs font-semibold text-primary-active">{term.term} · {term.weight}</span>)}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <DataBlock title="Example articles" rows={cluster.examples.map((item) => ({ article_id: item.article_id, title: item.title }))} articleLinks />
            <DataBlock title="Projection articles" rows={points.map((point) => ({ article_id: point.article_id, title: point.title, source: point.source, category: point.category }))} articleLinks />
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href={`/articles?cluster=${encodeURIComponent(String(cluster.cluster_id))}`} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><ExternalLink className="h-4 w-4" />Apply to Articles facet</Link>
            <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copy link</Button>
          </div>
        </div>
      ) : (
        <EmptyState title="Cluster unavailable" detail="Run clustering or adjust the current filters." />
      )}
    </DrilldownShell>
  );
}

function EntityDrilldownModal({ entity, data, onClose }: { entity: string; data: Awaited<ReturnType<typeof api.textMiningEntities>> | undefined; onClose: () => void }) {
  const matches = data?.entity_frequency.filter((item) => item.entity === entity) ?? [];
  const articles = data?.representative_articles.filter((item) => item.entities.includes(entity)) ?? [];
  const edges = data?.cooccurrence_edges.filter((edge) => edge.source === entity || edge.target === entity) ?? [];
  return (
    <DrilldownShell title={`Entity: ${entity}`} onClose={onClose}>
      {matches.length || articles.length || edges.length ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <InsightCard title="Frequency" metric={String(matches.reduce((sum, item) => sum + Number(item.count || 0), 0))} detail="Occurrences in current filters." />
            <InsightCard title="Articles" metric={String(articles.length)} detail="Representative articles." />
            <InsightCard title="Links" metric={String(edges.length)} detail="Co-occurring entity links." />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <DataBlock title="Entity rows" rows={matches} />
            <DataBlock title="Related entities" rows={edges.map((edge) => ({ related: edge.source === entity ? edge.target : edge.source, weight: edge.weight }))} />
          </div>
          <DataBlock title="Representative articles" rows={articles.map((item) => ({ article_id: item.article_id, title: item.title, source: item.source, category: item.category, publish_date: item.publish_date }))} articleLinks />
          <div className="flex flex-wrap gap-2">
            <Link href={`/articles?entity=${encodeURIComponent(entity)}`} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><ExternalLink className="h-4 w-4" />Apply to Articles facet</Link>
            <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copy link</Button>
          </div>
        </div>
      ) : (
        <EmptyState title="Entity unavailable" detail="Adjust filters or select an entity from the chart." />
      )}
    </DrilldownShell>
  );
}

function DrilldownShell({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-slate-950/50 p-3 md:p-6" role="dialog" aria-modal="true" aria-label={title} data-testid="drilldown-modal">
      <div className="mx-auto max-h-full max-w-5xl overflow-auto rounded-lg border border-line bg-surface shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-surface p-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">Drill-down</div>
            <h2 className="text-lg font-semibold text-ink">{title}</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-md border border-line bg-surface-elevated p-2 text-muted hover:text-ink" aria-label="Close drill-down">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

function DataBlock({ title, rows, articleLinks = false }: { title: string; rows: Row[]; articleLinks?: boolean }) {
  if (!articleLinks) return <Table title={title} rows={rows} />;
  return (
    <Card>
      <CardHeader eyebrow="Drill-down" title={title} />
      {rows.length ? (
        <div className="space-y-2">
          {rows.slice(0, 12).map((row) => (
            <Link key={String(row.article_id)} href={`/articles/${encodeURIComponent(String(row.article_id))}`} className="block rounded-md border border-line bg-surface-subtle px-3 py-2 text-sm text-primary-active">
              <span className="font-semibold">{String(row.title || row.article_id)}</span>
              <span className="numeric ml-2 text-xs text-muted">{String(row.weight ?? row.source ?? "")}</span>
            </Link>
          ))}
        </div>
      ) : <EmptyState title="No drill-down rows" />}
    </Card>
  );
}

function ExportButton({ href, label }: { href: string; label: string }) {
  return <a href={href} className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"><Download className="h-4 w-4" />{label}</a>;
}
