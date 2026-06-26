"use client";

import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, GraphChart, HeatmapChart as EChartsHeatmapChart, LineChart, RadarChart, SankeyChart as EChartsSankeyChart, ScatterChart, TreemapChart as EChartsTreemapChart } from "echarts/charts";
import { CalendarComponent, GridComponent, LegendComponent, RadarComponent, TitleComponent, TooltipComponent, TransformComponent, VisualMapComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
import type { ECharts, EChartsOption } from "echarts";
import { Download } from "lucide-react";

import { Button, EmptyState } from "@/components/ui";
import { cssVar, darkChartBase } from "@/components/advanced-charts/chart-theme";

echarts.use([
  BarChart,
  CalendarComponent,
  EChartsHeatmapChart,
  EChartsSankeyChart,
  EChartsTreemapChart,
  GraphChart,
  GridComponent,
  LegendComponent,
  LineChart,
  RadarChart,
  RadarComponent,
  ScatterChart,
  SVGRenderer,
  TitleComponent,
  TooltipComponent,
  TransformComponent,
  VisualMapComponent,
]);

export function EChart({
  option,
  height = 360,
  empty,
  emptyTitle = "No chart data",
  exportName = "chart",
}: {
  option: EChartsOption;
  height?: number;
  empty?: boolean;
  emptyTitle?: string;
  exportName?: string;
}) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ECharts | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!elRef.current) return;
    let cancelled = false;
    let frame = 0;
    chartRef.current = echarts.init(elRef.current, undefined, { renderer: "svg" });
    setReady(true);
    frame = requestAnimationFrame(() => {
      if (!cancelled) chartRef.current?.resize();
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || empty || !ready) return;
    chartRef.current.resize();
    chartRef.current.setOption({ ...darkChartBase(), ...option }, true);
  }, [empty, option, ready]);

  useEffect(() => {
    if (!chartRef.current || !elRef.current) return;
    const resize = () => chartRef.current?.resize();
    const observer = new ResizeObserver(resize);
    observer.observe(elRef.current);
    window.addEventListener("resize", resize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
    };
  }, [ready]);

  if (empty) return <EmptyState title={emptyTitle} detail="Adjust filters, run the related job, or expand the date range." />;

  return (
    <div className="relative min-w-0">
      <div ref={elRef} style={{ height }} className="min-w-0" />
      <div className="absolute right-2 top-2">
        <Button
          type="button"
          variant="secondary"
          className="min-h-8 px-2 py-1 text-xs"
          onClick={() => {
            const url = chartRef.current?.getDataURL({ pixelRatio: 2, backgroundColor: cssVar("--chart-bg", "#0b1626") });
            if (!url) return;
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = `${exportName}.png`;
            anchor.click();
          }}
        >
          <Download className="h-3.5 w-3.5" />
          PNG
        </Button>
      </div>
    </div>
  );
}
