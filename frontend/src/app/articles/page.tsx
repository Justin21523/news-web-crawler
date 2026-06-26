"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, Filter, Search, SlidersHorizontal } from "lucide-react";

import { DataTable, FilterChip } from "@/components/data-display";
import { Button, Card, CardHeader, EmptyState, Input, Select, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

const lengthOptions = {
  "": { min: "", max: "" },
  short: { min: "0", max: "299" },
  medium: { min: "300", max: "999" },
  long: { min: "1000", max: "" },
};

export default function ArticlesPage() {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [searchScope, setSearchScope] = useState("all");
  const [ranking, setRanking] = useState("recent");
  const [sort, setSort] = useState("date_desc");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [lengthBucket, setLengthBucket] = useState("");
  const [keyword, setKeyword] = useState("");
  const [entity, setEntity] = useState("");
  const [qualityIssue, setQualityIssue] = useState("");
  const [topic, setTopic] = useState("");
  const [cluster, setCluster] = useState("");
  const [page, setPage] = useState(1);

  const length = lengthOptions[lengthBucket as keyof typeof lengthOptions] ?? lengthOptions[""];
  const params = useMemo(() => ({
    query,
    source,
    category,
    status,
    search_scope: searchScope,
    ranking,
    sort,
    date_from: dateFrom,
    date_to: dateTo,
    min_length: length.min,
    max_length: length.max,
    keyword,
    entity,
    quality_issue: qualityIssue,
    topic,
    cluster,
    page,
    page_size: 20,
  }), [query, source, category, status, searchScope, ranking, sort, dateFrom, dateTo, length.min, length.max, keyword, entity, qualityIssue, topic, cluster, page]);

  const articles = useQuery({ queryKey: ["articles", params], queryFn: () => api.articles(params), refetchInterval: 20000 });
  const facets = useQuery({ queryKey: ["facets"], queryFn: api.facets, refetchInterval: 30000 });
  const totalPages = Math.max(1, Math.ceil((articles.data?.total ?? 0) / 20));
  const resetPage = (fn: (value: string) => void) => (value: string) => {
    fn(value);
    setPage(1);
  };
  const activeFilters = [
    source && { label: `Source: ${source}`, clear: () => setSource("") },
    category && { label: `Category: ${category}`, clear: () => setCategory("") },
    status && { label: `Status: ${status}`, clear: () => setStatus("") },
    keyword && { label: `Keyword: ${keyword}`, clear: () => setKeyword("") },
    entity && { label: `Entity: ${entity}`, clear: () => setEntity("") },
    qualityIssue && { label: `Issue: ${qualityIssue.replaceAll("_", " ")}`, clear: () => setQualityIssue("") },
    topic && { label: `Topic: ${topic}`, clear: () => setTopic("") },
    cluster && { label: `Cluster: ${cluster}`, clear: () => setCluster("") },
    lengthBucket && { label: `Length: ${lengthBucket}`, clear: () => setLengthBucket("") },
  ].filter(Boolean) as Array<{ label: string; clear: () => void }>;

  const tableRows = (articles.data?.items ?? []).map((item) => ({
    title: item.title,
    source: item.source_name || item.source,
    category: item.category_name || item.category || "Uncategorized",
    published: item.publish_date || "-",
    status: item.status || "-",
    length: item.char_count,
    keywords: item.keywords.join(", "),
    entities: item.entities.join(", "),
  }));

  return (
    <div className="page-shell">
      <div className="page-heading flex flex-wrap items-start justify-between gap-3" data-tour-id="articles-overview">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{t("page.articles.title")}</h1>
          <p className="mt-1 text-sm text-muted">{t("page.articles.subtitle")}</p>
        </div>
        <div className="rounded-md border border-info-border bg-info-soft px-3 py-2 text-sm font-semibold text-info-text">
          {(articles.data?.total ?? 0).toLocaleString()} results
        </div>
      </div>

      <Card tone="blue">
        <CardHeader eyebrow="Search" title="Explore the article database" action={<Database className="h-5 w-5 text-primary-active" />} />
        <div className="grid gap-3 xl:grid-cols-[1.4fr_150px_150px_150px_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
            <Input value={query} onChange={(event) => resetPage(setQuery)(event.target.value)} placeholder="Search title, content, keyword, or entity" className="pl-9" />
          </div>
          <Select value={searchScope} onChange={(event) => resetPage(setSearchScope)(event.target.value)}>
            <option value="all">All fields</option>
            <option value="title">Title</option>
            <option value="content">Content</option>
            <option value="keyword">Keyword JSON</option>
            <option value="entity">Entity JSON</option>
          </Select>
          <Select value={ranking} onChange={(event) => resetPage(setRanking)(event.target.value)}>
            <option value="recent">Recent</option>
            <option value="fts">FTS</option>
            <option value="tfidf">TF-IDF related</option>
            <option value="hybrid">Hybrid</option>
          </Select>
          <Select value={sort} onChange={(event) => resetPage(setSort)(event.target.value)}>
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="relevance">Relevance</option>
            <option value="length_desc">Longest</option>
            <option value="length_asc">Shortest</option>
          </Select>
          <Button onClick={() => void articles.refetch()}>
            <SlidersHorizontal className="h-4 w-4" />
            Apply
          </Button>
        </div>
      </Card>

      <Card tone="secondary">
        <CardHeader eyebrow="Facets" title="Filter by source, category, quality, date, and NLP features" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <FacetSelect label="All sources" value={source} onChange={resetPage(setSource)} items={facets.data?.source_counts ?? []} />
          <FacetSelect label="All categories" value={category} onChange={resetPage(setCategory)} items={facets.data?.category_counts ?? []} />
          <FacetSelect label="All statuses" value={status} onChange={resetPage(setStatus)} items={facets.data?.status_counts ?? []} />
          <FacetSelect label="Quality issues" value={qualityIssue} onChange={resetPage(setQualityIssue)} items={facets.data?.issue_type_counts ?? []} />
          <FacetSelect label="Topic assignment" value={topic} onChange={resetPage(setTopic)} items={facets.data?.topic_counts ?? []} />
          <FacetSelect label="Cluster assignment" value={cluster} onChange={resetPage(setCluster)} items={facets.data?.cluster_counts ?? []} />
          <Select value={lengthBucket} onChange={(event) => resetPage(setLengthBucket)(event.target.value)}>
            <option value="">All lengths</option>
            {(facets.data?.length_buckets ?? []).map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
          </Select>
          <FacetSelect label="Keyword facet" value={keyword} onChange={resetPage(setKeyword)} items={facets.data?.keyword_counts ?? []} />
          <FacetSelect label="Entity facet" value={entity} onChange={resetPage(setEntity)} items={facets.data?.entity_counts ?? []} />
          <div className="grid grid-cols-2 gap-3">
            <Input type="date" value={dateFrom} onChange={(event) => resetPage(setDateFrom)(event.target.value)} />
            <Input type="date" value={dateTo} onChange={(event) => resetPage(setDateTo)(event.target.value)} />
          </div>
        </div>
        {activeFilters.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {activeFilters.map((item) => <FilterChip key={item.label} label={item.label} onRemove={item.clear} />)}
          </div>
        ) : null}
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Card tone="primary">
          <CardHeader eyebrow="Results" title="Search result table" />
          <DataTable rows={tableRows} limit={20} emptyTitle={articles.isLoading ? "Loading articles" : "No articles match the current filters"} />
        </Card>

        <Card tone="accent">
          <CardHeader eyebrow="Preview" title="Top matching articles" action={<Filter className="h-5 w-5 text-warn-text" />} />
          <div className="space-y-3">
            {articles.data?.items.length ? articles.data.items.slice(0, 8).map((article) => (
              <Link key={article.article_id} href={`/articles/${encodeURIComponent(article.article_id)}`} className="block rounded-md border border-line bg-surface-elevated p-3 transition hover:border-primary hover:bg-primary-soft-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="line-clamp-2 text-sm font-semibold leading-5 text-ink">{article.title}</h2>
                    <div className="mt-1 text-xs text-muted">{article.source_name || article.source} · {article.publish_date || "No date"}</div>
                  </div>
                  <StatusBadge status={article.status} />
                </div>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted">{article.snippet || "No preview available."}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {article.keywords.slice(0, 3).map((item) => <span key={item} className="rounded-full bg-primary-soft-2 px-2 py-0.5 text-[0.68rem] font-semibold text-primary-active">{item}</span>)}
                </div>
              </Link>
            )) : (
              <EmptyState title={articles.isLoading ? "Loading previews" : "No previews"} detail="Try fewer facets or run ingestion/NLP jobs." />
            )}
          </div>
        </Card>
      </div>

      <div className="flex items-center justify-between">
        <div className="numeric text-sm text-muted">Page {page} of {totalPages}</div>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</Button>
          <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</Button>
        </div>
      </div>
    </div>
  );
}

function FacetSelect({
  label,
  value,
  onChange,
  items,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  items: Array<{ value: string; count: number }>;
}) {
  return (
    <Select value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{label}</option>
      {items.map((item) => <option key={item.value} value={item.value}>{item.value} ({item.count})</option>)}
    </Select>
  );
}
