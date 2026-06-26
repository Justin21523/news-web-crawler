import { FileWarning, Sparkles } from "lucide-react";

import { Card, CardHeader, ChartNote, EmptyState, StatusBadge } from "@/components/ui";
import type { AnalysisReport } from "@/lib/types";

export function AnalysisStatusCard({ report }: { report: AnalysisReport }) {
  return (
    <Card>
      <CardHeader
        eyebrow="Analysis"
        title={report.name.replaceAll("_", " ")}
        action={<StatusBadge status={report.status} />}
      />
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-primary-soft p-2 text-primary-active">
          {report.status === "ready" ? <Sparkles className="h-4 w-4" /> : <FileWarning className="h-4 w-4" />}
        </div>
        <div>
          <p className="text-sm leading-6 text-muted">{report.summary}</p>
          {report.updated_at ? <p className="numeric mt-2 text-xs text-muted">Updated {report.updated_at}</p> : null}
        </div>
      </div>
    </Card>
  );
}

export function JsonPreview({ value }: { value: unknown }) {
  if (!value) {
    return <EmptyState title="No report data" detail="Run the analysis job after NLP enrichment." />;
  }
  return (
    <pre className="max-h-[360px] overflow-auto rounded-md bg-code-bg p-4 text-xs leading-5 text-code-text shadow-inner">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function InsightCard({ title, metric, detail }: { title: string; metric: string; detail: string }) {
  return (
    <Card tone="primary">
      <div className="text-sm font-medium text-muted">{title}</div>
      <div className="numeric mt-2 text-3xl font-semibold text-ink">{metric}</div>
      <ChartNote>{detail}</ChartNote>
    </Card>
  );
}
