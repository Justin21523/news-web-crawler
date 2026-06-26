"use client";

import { EmptyState } from "@/components/ui";
import { chartPalette } from "@/components/advanced-charts/chart-theme";

type Node = { id: string; label?: string; name?: string; count?: number; degree?: number; value?: number; category?: string; symbolSize?: number };
type Edge = { source: string; target: string; weight?: number; value?: number };

export function NetworkGraphChart({ nodes, edges, height = 420, exportName = "network", onSelect }: { nodes: Node[]; edges: Edge[]; height?: number; exportName?: string; onSelect?: (node: Node) => void }) {
  void exportName;
  if (!nodes.length || !edges.length) return <EmptyState title="No network data" detail="Run NLP/entity extraction or adjust filters." />;
  const maxDegree = Math.max(1, ...nodes.map((node) => Number(node.degree ?? node.count ?? 1)));
  return (
    <div className="relative overflow-hidden rounded-md border border-line bg-surface-muted p-4" style={{ minHeight: height }}>
      <div className="flex flex-wrap content-center justify-center gap-3">
        {nodes.slice(0, 36).map((node, index) => {
          const size = Math.max(36, Math.min(86, 32 + (Number(node.degree ?? node.count ?? 1) / maxDegree) * 54));
          return (
            <button key={node.id} type="button" data-testid={`network-node-${exportName}-${node.label || node.id}`.replace(/\s+/g, "-")} onClick={() => onSelect?.(node)} className="flex items-center justify-center rounded-full text-center text-[0.68rem] font-semibold text-white shadow-sm transition hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary" style={{ width: size, height: size, background: chartPalette[index % chartPalette.length] }} title={`${node.label || node.id}: degree ${node.degree ?? 0}`}>
              <span className="line-clamp-2 px-1">{node.label || node.id}</span>
            </button>
          );
        })}
      </div>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {edges.slice(0, 8).map((edge) => <div key={`${edge.source}-${edge.target}`} className="truncate rounded-md border border-line bg-surface px-2 py-1 text-xs text-muted">{edge.source} → {edge.target} · {edge.value ?? edge.weight}</div>)}
      </div>
    </div>
  );
}
