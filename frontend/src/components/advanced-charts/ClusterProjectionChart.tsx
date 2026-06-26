"use client";

import { EmptyState } from "@/components/ui";
import { chartPalette } from "@/components/advanced-charts/chart-theme";

type Point = { article_id: string; title?: string; cluster_id: string | number; x: number; y: number; source?: string; category?: string };

export function ClusterProjectionChart({ points, height = 400, exportName = "cluster-projection", onSelect }: { points: Point[]; height?: number; exportName?: string; onSelect?: (point: Point) => void }) {
  void exportName;
  if (!points.length) return <EmptyState title="No projection data" detail="Run clustering with enough NLP documents." />;
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const scale = (value: number, min: number, max: number) => (max === min ? 50 : 8 + ((value - min) / (max - min)) * 84);
  return (
    <svg viewBox="0 0 100 100" className="w-full rounded-md border border-line bg-surface-muted" style={{ minHeight: height }} role="img" aria-label="Cluster projection">
      {[20, 40, 60, 80].map((tick) => <line key={`x-${tick}`} x1={tick} x2={tick} y1={6} y2={94} stroke="rgba(148,163,184,.24)" strokeWidth=".35" />)}
      {[20, 40, 60, 80].map((tick) => <line key={`y-${tick}`} x1={6} x2={94} y1={tick} y2={tick} stroke="rgba(148,163,184,.24)" strokeWidth=".35" />)}
      {points.map((point, index) => (
        <circle key={`${point.article_id}-${index}`} cx={scale(point.x, minX, maxX)} cy={100 - scale(point.y, minY, maxY)} r="1.8" fill={chartPalette[Number(point.cluster_id) % chartPalette.length]} opacity="0.86" className="cursor-pointer" onClick={() => onSelect?.(point)}>
          <title>{point.title || point.article_id}</title>
        </circle>
      ))}
    </svg>
  );
}
