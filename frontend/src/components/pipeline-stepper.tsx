import { Check, Circle, Loader2, TriangleAlert } from "lucide-react";
import { clsx } from "clsx";

import type { PipelineStep } from "@/lib/types";

export function PipelineStepper({ steps }: { steps: PipelineStep[] }) {
  return (
    <ol className="grid gap-3 md:grid-cols-5">
      {steps.map((step, index) => (
        <li key={step.key} className="relative">
          <div className="rounded-lg border border-line bg-surface-elevated p-4 shadow-card">
            <div className="flex items-start gap-3">
              <StepIcon status={step.status} />
              <div className="min-w-0">
                <div className="text-xs font-semibold uppercase tracking-wide text-muted">Step {index + 1}</div>
                <div className="mt-1 text-sm font-semibold text-ink">{step.label}</div>
                <div className="mt-2 text-xs leading-5 text-muted">{step.detail}</div>
              </div>
            </div>
            <div className="mt-4 h-2 rounded-full bg-surface-muted">
              <div
                className={clsx(
                  "h-2 rounded-full",
                  step.status === "complete" && "bg-success",
                  step.status === "running" && "bg-info",
                  (step.status === "warning" || step.status === "failed") && "bg-warn",
                  !["complete", "running", "warning", "failed"].includes(step.status) && "bg-primary",
                )}
                style={{ width: `${Math.min((step.count / Math.max(step.total, 1)) * 100, 100)}%` }}
              />
            </div>
            <div className="numeric mt-2 text-xs text-muted">{step.count} / {step.total}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function StepIcon({ status }: { status: PipelineStep["status"] }) {
  const base = "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border";
  if (status === "complete") {
    return <span className={`${base} border-success-border bg-success-soft text-success-text`}><Check className="h-4 w-4" /></span>;
  }
  if (status === "running") {
    return <span className={`${base} border-info-border bg-info-soft text-info-text`}><Loader2 className="h-4 w-4 animate-spin" /></span>;
  }
  if (status === "warning" || status === "failed") {
    return <span className={`${base} border-warn-border bg-warn-soft text-warn-text`}><TriangleAlert className="h-4 w-4" /></span>;
  }
  return <span className={`${base} border-line bg-surface-muted text-muted`}><Circle className="h-4 w-4" /></span>;
}
