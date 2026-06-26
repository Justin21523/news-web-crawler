"use client";

import type { EChartsOption } from "echarts";

import { EChart } from "@/components/advanced-charts/EChart";

type Node = Record<string, string | number | null | undefined>;
type Edge = Record<string, string | number | null | undefined>;

export function ForceGraphChart({ nodes, edges, height = 440, exportName = "force-graph" }: { nodes: Node[]; edges: Edge[]; height?: number; exportName?: string }) {
  const chartNodes = nodes.slice(0, 120).map((node) => ({
    id: String(node.id ?? node.label ?? ""),
    name: String(node.label ?? node.id ?? ""),
    value: Number(node.value ?? node.count ?? node.degree ?? 1),
    category: Number(node.community ?? 0),
    symbolSize: Math.max(16, Math.min(70, Number(node.symbolSize ?? 18))),
  })).filter((node) => node.id);
  const allowed = new Set(chartNodes.map((node) => node.id));
  const chartEdges = edges.slice(0, 220).map((edge) => ({
    source: String(edge.source ?? ""),
    target: String(edge.target ?? ""),
    value: Number(edge.weight ?? edge.value ?? edge.count ?? 1),
  })).filter((edge) => allowed.has(edge.source) && allowed.has(edge.target));
  const categories = Array.from(new Set(chartNodes.map((node) => node.category))).map((id) => ({ name: `Community ${id}` }));
  const option = {
    legend: { bottom: 0, data: categories.map((item) => item.name) },
    series: [{
      type: "graph",
      layout: "force",
      roam: true,
      draggable: true,
      categories,
      data: chartNodes,
      links: chartEdges,
      label: { show: true, color: "var(--color-text)", fontSize: 10, formatter: "{b}" },
      lineStyle: { color: "source", opacity: 0.38, curveness: 0.12 },
      force: { repulsion: 150, edgeLength: [45, 140], gravity: 0.08 },
      emphasis: { focus: "adjacency", lineStyle: { width: 3 } },
    }],
  } as EChartsOption;
  return <EChart option={option} height={height} empty={!chartNodes.length || !chartEdges.length} emptyTitle="No graph data" exportName={exportName} />;
}
