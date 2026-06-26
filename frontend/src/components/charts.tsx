"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/ui";

type ChartRow = Record<string, string | number | boolean | null | undefined>;

const palette = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)", "var(--chart-7)", "var(--chart-8)"];

export function HorizontalBarChart({
  data,
  labelKey,
  valueKey,
  height = 300,
}: {
  data: ChartRow[];
  labelKey: string;
  valueKey: string;
  height?: number;
}) {
  if (!data.length) return <EmptyState title="No chart data" />;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 18, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey={labelKey} type="category" width={110} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={valueKey} radius={[0, 4, 4, 0]}>
            {data.map((_, index) => <Cell key={index} fill={palette[index % palette.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MetricComparisonChart({
  data,
  labelKey,
  metrics,
  height = 300,
}: {
  data: ChartRow[];
  labelKey: string;
  metrics: Array<{ key: string; label: string }>;
  height?: number;
}) {
  if (!data.length) return <EmptyState title="No comparison data" />;
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
          <XAxis dataKey={labelKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          {metrics.map((metric, index) => <Bar key={metric.key} dataKey={metric.key} name={metric.label} fill={palette[index % palette.length]} radius={[3, 3, 0, 0]} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HeatmapMatrix({
  labels,
  matrix,
}: {
  labels: string[];
  matrix: number[][];
}) {
  if (!labels.length || !matrix.length) return <EmptyState title="No heatmap data" />;
  const maxValue = Math.max(1, ...matrix.flat());
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-surface px-2 py-2 text-left font-semibold text-muted">Actual / Pred</th>
            {labels.map((label) => <th key={label} className="max-w-24 px-2 py-2 text-left font-semibold text-muted">{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, rowIndex) => (
            <tr key={labels[rowIndex]}>
              <th className="sticky left-0 z-10 max-w-32 bg-surface px-2 py-2 text-left font-semibold text-ink">{labels[rowIndex]}</th>
              {row.map((value, colIndex) => {
                const intensity = value / maxValue;
                const isCorrect = rowIndex === colIndex;
                return (
                  <td
                    key={`${rowIndex}-${colIndex}`}
                    className="numeric min-w-16 rounded px-2 py-2 text-center font-semibold"
                    style={{
                      backgroundColor: isCorrect ? `rgba(22, 163, 74, ${0.12 + intensity * 0.45})` : `rgba(220, 38, 38, ${0.08 + intensity * 0.32})`,
                      color: isCorrect ? "var(--success-text)" : "var(--danger-text)",
                    }}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
