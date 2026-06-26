"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Brain, ExternalLink, Network, Sparkles } from "lucide-react";

import { DataTable } from "@/components/data-display";
import { Card, CardHeader, EmptyState, Select, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

export default function ArticleDetailPage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const [summaryMethod, setSummaryMethod] = useState("mmr");
  const [explanationMode, setExplanationMode] = useState("linear_coefficients");
  const [explanationTarget, setExplanationTarget] = useState("source");
  const article = useQuery({ queryKey: ["article", id], queryFn: () => api.article(id), enabled: Boolean(id) });
  const summary = useQuery({ queryKey: ["article-summary", id, summaryMethod], queryFn: () => api.articleSummary(id, { method: summaryMethod, k: 4 }), enabled: Boolean(id) });
  const related = useQuery({ queryKey: ["related-articles", id], queryFn: () => api.relatedArticles(id, { limit: 8 }), enabled: Boolean(id) });
  const prediction = useQuery({ queryKey: ["article-prediction", id], queryFn: () => api.mlPredictArticle(id, { targets: "category,source,sentiment", prefer_artifact: true }), enabled: Boolean(id) });
  const explanation = useQuery({ queryKey: ["article-explanation", id, explanationTarget, explanationMode], queryFn: () => api.mlArticleExplanation(id, { target: explanationTarget, mode: explanationMode, feature_limit: 1000, max_depth: 4 }), enabled: Boolean(id) });

  if (article.isLoading) return <div className="page-shell"><EmptyState title="Loading article" /></div>;
  if (!article.data) return <div className="page-shell"><EmptyState title="Article not found" /></div>;

  const data = article.data;
  const entityRows = data.nlp?.entities.map(([entity, type]) => ({ entity, type })) ?? [];
  const keywordRows = data.nlp?.keywords.map(([keyword, score]) => ({ keyword, score })) ?? [];

  return (
    <div className="page-shell">
      <Link href="/articles" className="inline-flex items-center gap-2 text-sm font-medium text-primary-active">
        <ArrowLeft className="h-4 w-4" />
        Back to articles
      </Link>

      <div className="page-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="max-w-5xl text-2xl font-semibold leading-9 text-ink">{data.title}</h1>
            <div className="mt-2 text-sm text-muted">
              {data.source_name || data.source} · {data.publish_date || "No date"} · {data.author || "No author"}
            </div>
          </div>
          <StatusBadge status={data.status} />
        </div>
        {data.url ? (
          <a href={data.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-primary-active">
            Original article
            <ExternalLink className="h-4 w-4" />
          </a>
        ) : null}
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
        <Card tone="primary">
          <CardHeader eyebrow="Content" title="Full article text" />
          <article className="max-h-[760px] overflow-auto whitespace-pre-wrap rounded-md border border-line bg-surface-elevated p-4 text-sm leading-7 text-text-secondary">
            {data.content_clean || "No content."}
          </article>
        </Card>

        <div className="space-y-5">
          <Card tone="blue">
            <CardHeader eyebrow="Model" title="Prediction & explanation" action={<Brain className="h-5 w-5 text-primary-active" />} />
            <div className="mb-4 grid gap-2 md:grid-cols-2">
              <Select value={explanationTarget} onChange={(event) => setExplanationTarget(event.target.value)}>
                <option value="source">Source</option>
                <option value="category">Category</option>
                <option value="sentiment">Sentiment</option>
              </Select>
              <Select value={explanationMode} onChange={(event) => setExplanationMode(event.target.value)}>
                <option value="linear_coefficients">Linear contribution</option>
                <option value="tree_path">Decision tree path</option>
                <option value="top_terms">Top terms</option>
              </Select>
            </div>
            <div className="space-y-3">
              {prediction.data?.predictions.length ? prediction.data.predictions.map((item) => (
                <div key={`${String(item.target)}-${String(item.prediction)}`} className="rounded-md border border-line bg-surface-elevated p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{String(item.target)} · {String(item.model)}</div>
                      <div className="mt-1 text-base font-semibold text-ink">{String(item.prediction)}</div>
                    </div>
                    <span className="numeric rounded-full bg-primary-soft px-2 py-1 text-xs font-semibold text-primary-active">{item.confidence ? `${Math.round(Number(item.confidence) * 100)}%` : String(item.model_source)}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted">{String(item.explanation ?? "")}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Array.isArray(item.top_terms) ? (item.top_terms as Array<Record<string, unknown>>).slice(0, 6).map((term) => (
                      <span key={String(term.term)} className="rounded-full bg-info-soft px-2 py-0.5 text-[0.68rem] font-semibold text-info-text">{String(term.term)}</span>
                    )) : null}
                  </div>
                </div>
              )) : <EmptyState title={prediction.isLoading ? "Loading predictions" : "No model prediction"} detail={prediction.data?.notes?.join(" ") || "Train or persist a model artifact for richer article explanations."} />}
            </div>
            <div className="mt-4 rounded-md border border-line bg-surface-subtle p-3">
              {explanation.data?.status === "ready" ? (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{explanation.data.mode.replaceAll("_", " ")} · {explanation.data.model}</div>
                      <div className="mt-1 font-semibold text-ink">{explanation.data.prediction || "-"} <span className="text-sm text-muted">actual {explanation.data.actual_label || "-"}</span></div>
                    </div>
                    <span className="numeric rounded-full bg-primary-soft px-2 py-1 text-xs font-semibold text-primary-active">{explanation.data.confidence ? `${Math.round(explanation.data.confidence * 100)}%` : explanation.data.model_source}</span>
                  </div>
                  <p className="text-sm leading-6 text-muted">{explanation.data.explanation}</p>
                  {explanation.data.mode === "tree_path" ? <MiniTable rows={explanation.data.path} /> : <MiniTable rows={explanation.data.contributions} />}
                </div>
              ) : <EmptyState title={explanation.isLoading ? "Loading explanation" : "No explanation"} detail={explanation.data?.notes?.join(" ") || "Try a different target or explanation mode."} />}
            </div>
          </Card>

          <Card tone="magenta">
            <CardHeader eyebrow="Text Mining" title="Topic & cluster assignments" action={<Network className="h-5 w-5 text-magenta-text" />} />
            <div className="space-y-3">
              {data.assignments.length ? data.assignments.map((item) => (
                <div key={`${String(item.assignment_type)}-${String(item.label)}`} className="rounded-md border border-line bg-surface-elevated p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-semibold text-ink">{String(item.label)}</div>
                    <div className="numeric text-xs font-semibold text-muted">{String(item.assignment_type)} · {Number(item.score ?? 0).toFixed(3)}</div>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Array.isArray(item.terms) ? (item.terms as Array<Record<string, unknown>>).slice(0, 6).map((term) => (
                      <span key={String(term.term)} className="rounded-full bg-primary-soft-2 px-2 py-0.5 text-[0.68rem] font-semibold text-primary-active">{String(term.term)}</span>
                    )) : null}
                  </div>
                </div>
              )) : <EmptyState title="No persisted assignments" detail="Run text mining assignment persistence to enable topic and cluster drill-down." />}
            </div>
          </Card>

          <Card tone="secondary">
            <CardHeader eyebrow={`Summary · ${summary.data?.provider ?? "extractive"}`} title="Article summarization" action={<Sparkles className="h-5 w-5 text-info-text" />} />
            <Select value={summaryMethod} onChange={(event) => setSummaryMethod(event.target.value)}>
              <option value="mmr">MMR summary</option>
              <option value="extractive">Extractive</option>
              <option value="lead_k">Lead sentences</option>
            </Select>
            <div className="mt-4 space-y-3">
              {summary.data?.sentences.length ? summary.data.sentences.map((sentence, index) => (
                <div key={`${sentence}-${index}`} className="rounded-md border border-line bg-surface-subtle p-3 text-sm leading-6 text-muted">{sentence}</div>
              )) : <EmptyState title={summary.isLoading ? "Generating summary" : "No summary"} />}
              {summary.data?.notes?.length ? <div className="rounded-md border border-warn-border bg-warn-soft px-3 py-2 text-xs font-medium text-warn-text">{summary.data.notes.join(" ")}</div> : null}
            </div>
          </Card>

          <Card tone="accent">
            <CardHeader eyebrow="Metadata" title="Article profile" />
            <dl className="space-y-3 text-sm">
              <Row label="Category" value={data.category_name || data.category || "None"} />
              <Row label="Characters" value={data.char_count.toLocaleString()} />
              <Row label="Words" value={data.word_count.toLocaleString()} />
              <Row label="Crawled" value={data.crawled_at || "None"} />
              <Row label="Cleaned" value={data.cleaned_at || "None"} />
            </dl>
          </Card>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <Card tone="blue">
          <CardHeader eyebrow="NLP" title="Keywords" />
          <DataTable rows={keywordRows} limit={20} emptyTitle="No keywords available" />
        </Card>
        <Card tone="magenta">
          <CardHeader eyebrow="NLP" title="Entities" action={<span className="rounded-full border border-info-border bg-info-soft px-2.5 py-1 text-xs font-semibold text-info-text">source {String(data.nlp?.entity_source ?? "fallback")}</span>} />
          {data.nlp?.entity_run_id ? <p className="numeric mb-3 text-xs text-muted">Entity run: {String(data.nlp.entity_run_id)}</p> : null}
          <DataTable rows={entityRows} limit={20} emptyTitle="No entities available" />
        </Card>
        <Card tone="warning">
          <CardHeader eyebrow="Quality" title="Article issues" />
          <DataTable rows={data.quality_issues} limit={20} emptyTitle="No quality issues detected" />
        </Card>
      </div>

      <Card tone="secondary">
        <CardHeader eyebrow="Related" title="Similar or contextually related articles" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {related.data?.length ? related.data.map((item) => (
            <Link key={item.article_id} href={`/articles/${encodeURIComponent(item.article_id)}`} className="rounded-md border border-line bg-surface-elevated p-3 transition hover:border-primary hover:bg-primary-soft-2">
              <div className="line-clamp-2 text-sm font-semibold leading-5 text-ink">{item.title}</div>
              <div className="mt-2 text-xs text-muted">{item.source} · {item.category}</div>
              <div className="numeric mt-2 text-xs font-semibold text-primary-active">score {item.score}</div>
            </Link>
          )) : <EmptyState title={related.isLoading ? "Loading related articles" : "No related articles"} />}
        </div>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 rounded-md border border-line bg-surface-subtle px-3 py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-semibold text-ink">{value}</dd>
    </div>
  );
}

function MiniTable({ rows }: { rows: Array<Record<string, string | number>> }) {
  const headers = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 4);
  if (!rows.length) return <EmptyState title="No explanation details" />;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-line text-xs">
        <thead><tr>{headers.map((header) => <th key={header} className="px-2 py-2 text-left font-semibold uppercase tracking-wide text-muted">{header.replaceAll("_", " ")}</th>)}</tr></thead>
        <tbody className="divide-y divide-line">{rows.slice(0, 10).map((row, index) => <tr key={index}>{headers.map((header) => <td key={header} className="px-2 py-2 text-muted">{String(row[header] ?? "")}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}
