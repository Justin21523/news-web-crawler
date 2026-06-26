"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Play, RefreshCw } from "lucide-react";

import { PipelineStepper } from "@/components/pipeline-stepper";
import { Button, Card, Input, Select, StatusBadge } from "@/components/ui";
import { useI18n } from "@/i18n";
import { api } from "@/lib/api";

const jobTypes = ["demo", "crawl", "ingest", "nlp", "tfidf", "export", "run_all", "analysis", "train_ml", "train_decision_tree", "export_ml_diagnostics_report"];

export default function JobsPage() {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [type, setType] = useState("demo");
  const [params, setParams] = useState("{\"reset\":true}");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs, refetchInterval: 5000 });
  const pipeline = useQuery({ queryKey: ["pipeline-status"], queryFn: api.pipelineStatus, refetchInterval: 5000 });
  const logs = useQuery({
    queryKey: ["job-logs", selectedId],
    queryFn: () => api.jobLogs(selectedId as number),
    enabled: selectedId !== null,
    refetchInterval: selectedId ? 5000 : false,
  });
  const createJob = useMutation({
    mutationFn: () => api.createJob(type, parseParams(params)),
    onSuccess: async (job) => {
      setSelectedId(job.id);
      await queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  return (
    <div className="page-shell">
      <div className="page-heading" data-tour-id="jobs-overview">
        <h1 className="text-2xl font-semibold text-ink">{t("page.jobs.title")}</h1>
        <p className="mt-1 text-sm text-muted">{t("page.jobs.subtitle")}</p>
      </div>

      <Card data-tour-id="jobs-workflow">
        <div className="mb-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">Workflow</div>
          <h2 className="mt-1 font-semibold text-ink">Processing steps</h2>
        </div>
        {pipeline.data?.steps.length ? <PipelineStepper steps={pipeline.data.steps} /> : null}
      </Card>

      <Card data-tour-id="jobs-runner">
        <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
          <Select value={type} onChange={(event) => setType(event.target.value)}>
            {jobTypes.map((item) => <option key={item} value={item}>{item}</option>)}
          </Select>
          <Input value={params} onChange={(event) => setParams(event.target.value)} placeholder='{"engine":"jieba"}' />
          <Button disabled={createJob.isPending} onClick={() => createJob.mutate()}>
            <Play className="h-4 w-4" />
            Run
          </Button>
        </div>
        <div className="mt-3 text-xs text-muted">
          Examples: demo {"{\"reset\":true}"} · crawl {"{\"spider\":\"cna\",\"days\":3}"} · nlp {"{\"engine\":\"jieba\",\"batch_size\":32}"} · train_ml {"{\"target\":\"source\",\"model\":\"logistic_regression\"}"} · diagnostics report {"{\"target\":\"source\",\"model\":\"logistic_regression\"}"}
        </div>
        {createJob.error ? <div className="mt-3 text-sm text-danger-text">{String(createJob.error.message)}</div> : null}
      </Card>

      <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-ink">Recent Jobs</h2>
            <button className="text-muted hover:text-ink" onClick={() => void jobs.refetch()} title="Refresh">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="space-y-3">
            {jobs.data?.length ? (
              jobs.data.map((job) => (
                <button
                  key={job.id}
                  onClick={() => setSelectedId(job.id)}
                  className="w-full rounded-md border border-line p-3 text-left hover:border-primary"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium text-ink">#{job.id} {job.type}</div>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="numeric mt-2 text-xs text-muted">{job.created_at || "No timestamp"}</div>
                  {job.error ? <div className="mt-2 text-xs text-danger-text">{job.error}</div> : null}
                </button>
              ))
            ) : (
              <div className="rounded-md border border-dashed border-line p-8 text-center text-sm text-muted">
                {jobs.isLoading ? "Loading jobs" : "No jobs yet."}
              </div>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="font-semibold text-ink">Logs</h2>
          <pre className="mt-4 min-h-[420px] overflow-auto rounded-md bg-code-bg p-4 text-xs leading-5 text-code-text shadow-inner">
            {selectedId ? logs.data?.content || "No logs yet." : "Select a job to view logs."}
          </pre>
        </Card>
      </div>
    </div>
  );
}

function parseParams(value: string): Record<string, unknown> {
  if (!value.trim()) {
    return {};
  }
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Params must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}
