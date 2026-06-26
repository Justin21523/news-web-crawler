import { clsx } from "clsx";

import type { DataQualityMetric } from "@/lib/types";

export function QualityList({ metrics }: { metrics: DataQualityMetric[] }) {
  return (
    <div className="space-y-4">
      {metrics.map((metric) => (
        <div key={metric.key}>
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-medium text-ink">{metric.label}</div>
            <div className="numeric text-sm text-muted">{metric.percent ?? 0}%</div>
          </div>
          <div className="mt-2 h-2 rounded-full bg-surface-muted">
            <div
              className={clsx(
                "h-2 rounded-full",
                metric.severity === "good" && "bg-success",
                metric.severity === "warning" && "bg-warn",
                metric.severity === "danger" && "bg-danger",
                metric.severity === "neutral" && "bg-primary",
              )}
              style={{ width: `${Math.min(metric.percent ?? 0, 100)}%` }}
            />
          </div>
          <div className="numeric mt-1 text-xs text-muted">{metric.value} / {metric.total ?? "-"}</div>
        </div>
      ))}
    </div>
  );
}
