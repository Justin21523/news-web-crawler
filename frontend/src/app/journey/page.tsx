"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Database, FileUp, Play, Route, Sparkles, Workflow } from "lucide-react";

import { ScrollableTabs } from "@/components/data-display";
import { PipelineStepper } from "@/components/pipeline-stepper";
import { Button, Card, CardHeader, EmptyState, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import type { ImportUploadResponse } from "@/lib/types";
import { useI18n } from "@/i18n";

type JourneyKey =
  | "acquisition"
  | "quality"
  | "cleaning"
  | "nlp"
  | "keywords"
  | "collocation"
  | "entities"
  | "topics"
  | "bursts"
  | "search"
  | "ml"
  | "reports";

const journeySteps: Array<{
  key: JourneyKey;
  label: string;
  route: string;
  accent: string;
  meaning: string;
  output: string;
  interaction: string;
}> = [
  { key: "acquisition", label: "Data Acquisition", route: "/journey", accent: "cyan", meaning: "將 crawler、manual import 與 sample dataset 統一成可追蹤的 raw articles。", output: "JSONL raw dataset + ingest job", interaction: "上傳資料或執行 sample pipeline。" },
  { key: "quality", label: "Data Quality", route: "/data-quality", accent: "emerald", meaning: "先找出資料缺口，避免後續分析建立在髒資料上。", output: "quality score、issues table、coverage charts", interaction: "依 severity / issue type drill down 到文章。" },
  { key: "cleaning", label: "Cleaning", route: "/jobs", accent: "sky", meaning: "標準化 URL、日期、內容長度、重複資料與欄位格式。", output: "cleaned articles", interaction: "透過 Jobs 追蹤每個清理任務與 logs。" },
  { key: "nlp", label: "NLP Features", route: "/text-mining?tab=overview", accent: "violet", meaning: "把不可直接量化的文字轉為 tokens、entities、keywords 與 embedding features。", output: "tokens、keywords、entities、sentiment baseline", interaction: "切換 fallback/model NER strategy 比較品質。" },
  { key: "keywords", label: "TF-IDF / Keywords", route: "/text-mining?tab=tfidf", accent: "amber", meaning: "找出最能代表 corpus、source、category 的關鍵詞。", output: "TF-IDF ranking、keyword trend、word cloud", interaction: "點擊 keyword 反向套用 Articles 搜尋。" },
  { key: "collocation", label: "Collocation", route: "/text-mining?tab=collocations", accent: "pink", meaning: "判斷詞語是否經常一起出現，而不是只看單詞頻率。", output: "PMI、NPMI、Dice、LLR、co-occurrence graph", interaction: "調整 window size 與 scoring method。" },
  { key: "entities", label: "Entity Relationship", route: "/text-mining?tab=entities", accent: "cyan", meaning: "把人名、組織、地點與議題關係變成 media monitoring 視角。", output: "entity network、entity-source heatmap、Sankey", interaction: "點選 entity 查看相關文章與共現對象。" },
  { key: "topics", label: "Topic Modeling", route: "/text-mining?tab=topics", accent: "indigo", meaning: "用 NMF/LDA baseline 將大量新聞分群成可解釋主題。", output: "topic keywords、representative articles、topic timeline", interaction: "topic drill-down modal 查看代表文章。" },
  { key: "bursts", label: "Trend / Burst", route: "/text-mining?tab=bursts", accent: "orange", meaning: "偵測新興、下降與異常爆量關鍵詞，適合新聞趨勢監控。", output: "burst timeline、calendar heatmap、rising/declining cards", interaction: "點擊 burst term 進入 Articles facet。" },
  { key: "search", label: "Exploratory Search", route: "/articles", accent: "teal", meaning: "結合 facets、keyword/entity/topic/cluster，讓使用者快速找到內文與證據。", output: "search results、article detail、related articles", interaction: "用 source/category/topic/cluster/quality issue 交叉篩選。" },
  { key: "ml", label: "ML Diagnostics", route: "/ml", accent: "fuchsia", meaning: "訓練 baseline 模型後，不只看 accuracy，也分析錯誤類別與失敗因素。", output: "confusion heatmap、feature importance、error samples", interaction: "切換 target/model/artifact 比較診斷結果。" },
  { key: "reports", label: "Report Export", route: "/ml/diagnostics/reports", accent: "lime", meaning: "把分析結果整理成可展示、可下載、可比較的作品集報告。", output: "HTML / Markdown / Excel / PDF fallback", interaction: "預覽報表、批次匯出、版本比較。" },
];

export default function JourneyPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [active, setActive] = useState<JourneyKey>("acquisition");
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<ImportUploadResponse | null>(null);
  const pipeline = useQuery({ queryKey: ["pipeline"], queryFn: api.pipelineStatus, refetchInterval: 5000 });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs, refetchInterval: 5000 });

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("No file selected");
      return api.importUpload(file, true);
    },
    onSuccess: (result) => {
      setUploadResult(result);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });

  const sample = useMutation({
    mutationFn: () => api.createJob("demo", { reset: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });

  const activeStep = useMemo(() => journeySteps.find((item) => item.key === active) ?? journeySteps[0], [active]);

  return (
    <div className="page-shell">
      <div className="page-heading" data-tour-id="journey-overview">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary-soft px-3 py-1 text-xs font-bold text-primary-active">
              <Sparkles className="h-4 w-4" />
              {t("journey.badge")}
            </div>
            <h1 className="mt-3 text-3xl font-semibold text-ink">{t("journey.title")}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{t("journey.subtitle")}</p>
          </div>
          <Link href="/jobs" className="inline-flex min-h-10 items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink transition hover:border-primary/40">
            <Workflow className="h-4 w-4" />
            Jobs
          </Link>
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card tone="primary" data-tour-id="journey-upload">
          <CardHeader title={t("journey.uploadTitle")} eyebrow="Dataset" tone="primary" />
          <p className="text-sm leading-6 text-muted">{t("journey.uploadDetail")}</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto_auto]">
            <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-md border border-dashed border-primary/35 bg-primary-soft-2 px-3 text-sm font-semibold text-ink">
              <FileUp className="h-5 w-5 text-primary-active" />
              <span className="truncate">{file?.name ?? "CSV / JSON / JSONL"}</span>
              <input className="sr-only" type="file" accept=".csv,.json,.jsonl" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </label>
            <Button onClick={() => upload.mutate()} disabled={!file || upload.isPending}>
              <FileUp className="h-4 w-4" />
              {upload.isPending ? t("common.loading") : t("journey.uploadCta")}
            </Button>
            <Button variant="secondary" onClick={() => sample.mutate()} disabled={sample.isPending}>
              <Play className="h-4 w-4" />
              {sample.isPending ? t("common.loading") : t("journey.sampleCta")}
            </Button>
          </div>
          <div className="mt-5 rounded-md border border-line bg-surface-elevated p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted">{t("journey.currentUpload")}</div>
            {uploadResult ? (
              <div className="mt-2 grid gap-2 text-sm text-secondary sm:grid-cols-2">
                <div><span className="font-semibold text-ink">upload_id:</span> {uploadResult.upload_id}</div>
                <div><span className="font-semibold text-ink">format:</span> {uploadResult.detected_format}</div>
                <div><span className="font-semibold text-ink">articles:</span> {uploadResult.article_count_preview}</div>
                <div><span className="font-semibold text-ink">job:</span> {uploadResult.job_id ?? "manual ingest"}</div>
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted">{t("journey.noUpload")}</p>
            )}
            {upload.error ? <p className="mt-3 text-sm font-semibold text-danger-text">{String(upload.error.message)}</p> : null}
          </div>
        </Card>

        <Card tone="info" data-tour-id="journey-pipeline">
          <CardHeader title={t("journey.pipelineTitle")} eyebrow="Live Status" tone="info" />
          <p className="mb-4 text-sm leading-6 text-muted">{t("journey.pipelineDetail")}</p>
          {pipeline.data?.steps.length ? <PipelineStepper steps={pipeline.data.steps} /> : <EmptyState title="No pipeline status" detail="Run sample data or upload a dataset to populate workflow progress." />}
        </Card>
      </section>

      <section className="journey-rail" data-tour-id="journey-tabs">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">{t("journey.tabsTitle")}</div>
            <h2 className="mt-1 text-xl font-semibold text-ink">{activeStep.label}</h2>
          </div>
          <Link href={activeStep.route} className="inline-flex min-h-10 items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-ink transition hover:border-primary/40">
            {t("journey.openPage")}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <ScrollableTabs tabs={journeySteps.map((step) => ({ key: step.key, label: step.label }))} active={active} onChange={setActive} />
        <div className="mt-5 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <JourneyAnimation step={activeStep} />
          <div className="grid gap-3">
            <InfoBlock icon={<Route className="h-4 w-4" />} title={t("journey.meaning")} body={activeStep.meaning} />
            <InfoBlock icon={<Database className="h-4 w-4" />} title={t("journey.output")} body={activeStep.output} />
            <InfoBlock icon={<Sparkles className="h-4 w-4" />} title={t("journey.interaction")} body={activeStep.interaction} />
            <Card className="p-4" tone="secondary">
              <div className="text-sm font-semibold text-ink">Recent Jobs</div>
              <div className="mt-3 space-y-2">
                {(jobs.data ?? []).slice(0, 4).map((job) => (
                  <div key={job.id} className="flex items-center justify-between gap-3 rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm">
                    <div className="min-w-0">
                      <div className="truncate font-semibold text-ink">#{job.id} {job.type}</div>
                      <div className="text-xs text-muted">{job.created_at ?? "queued"}</div>
                    </div>
                    <StatusBadge status={job.status} />
                  </div>
                ))}
                {jobs.data?.length ? null : <EmptyState title="No jobs yet" detail="Run the sample pipeline to show the full portfolio workflow." />}
              </div>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}

function JourneyAnimation({ step }: { step: (typeof journeySteps)[number] }) {
  return (
    <div className="journey-flow-card">
      <div className="journey-packet" />
      <div className="grid h-full min-h-[16rem] grid-cols-3 items-center gap-3">
        <div className="journey-node">
          <div className="text-xs font-bold uppercase tracking-wide text-primary-active">Input</div>
          <div className="mt-2 text-sm font-semibold text-ink">{step.key === "acquisition" ? "CSV / JSON / Crawler" : "Articles + metadata"}</div>
        </div>
        <div className="journey-node border-accent/40">
          <div className="text-xs font-bold uppercase tracking-wide text-warn-text">Transform</div>
          <div className="mt-2 text-sm font-semibold text-ink">{step.label}</div>
          <div className="mt-3 flex gap-1">
            <span className="h-2 flex-1 rounded-full bg-primary" />
            <span className="h-2 flex-1 rounded-full bg-secondary" />
            <span className="h-2 flex-1 rounded-full bg-accent" />
          </div>
        </div>
        <div className="journey-node">
          <div className="text-xs font-bold uppercase tracking-wide text-success-text">Output</div>
          <div className="mt-2 text-sm font-semibold text-ink">{step.output}</div>
        </div>
      </div>
      <div className="pointer-events-none absolute inset-x-8 top-1/2 h-px bg-gradient-to-r from-primary/20 via-primary to-secondary/20" />
    </div>
  );
}

function InfoBlock({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface/90 p-4 shadow-card">
      <div className="flex items-center gap-2 text-sm font-semibold text-ink">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-primary/25 bg-primary-soft text-primary-active">{icon}</span>
        {title}
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{body}</p>
    </div>
  );
}
