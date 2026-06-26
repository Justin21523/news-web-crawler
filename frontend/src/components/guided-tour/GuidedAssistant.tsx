"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bot, ChevronLeft, ChevronRight, Compass, LocateFixed, X } from "lucide-react";
import { clsx } from "clsx";

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n";

type TourStep = {
  id: string;
  route: string;
  target: string;
  titleKey: string;
  bodyKey: string;
  visual: "upload" | "pipeline" | "quality" | "network" | "chart" | "ml" | "report";
};

const steps: TourStep[] = [
  { id: "welcome", route: "/journey", target: "journey-overview", titleKey: "tour.welcome.title", bodyKey: "tour.welcome.body", visual: "pipeline" },
  { id: "upload", route: "/journey", target: "journey-upload", titleKey: "tour.upload.title", bodyKey: "tour.upload.body", visual: "upload" },
  { id: "jobs", route: "/jobs", target: "jobs-runner", titleKey: "tour.jobs.title", bodyKey: "tour.jobs.body", visual: "pipeline" },
  { id: "workflow", route: "/", target: "dashboard-pipeline", titleKey: "tour.workflow.title", bodyKey: "tour.workflow.body", visual: "pipeline" },
  { id: "quality", route: "/data-quality", target: "data-quality-overview", titleKey: "tour.quality.title", bodyKey: "tour.quality.body", visual: "quality" },
  { id: "analysis", route: "/analysis?tab=trends", target: "analysis-overview", titleKey: "tour.analysis.title", bodyKey: "tour.analysis.body", visual: "chart" },
  { id: "text", route: "/text-mining?tab=collocations", target: "text-mining-overview", titleKey: "tour.text.title", bodyKey: "tour.text.body", visual: "network" },
  { id: "entities", route: "/text-mining?tab=entities", target: "text-mining-overview", titleKey: "tour.entities.title", bodyKey: "tour.entities.body", visual: "network" },
  { id: "articles", route: "/articles", target: "articles-overview", titleKey: "tour.articles.title", bodyKey: "tour.articles.body", visual: "quality" },
  { id: "ml", route: "/ml", target: "ml-overview", titleKey: "tour.ml.title", bodyKey: "tour.ml.body", visual: "ml" },
  { id: "reports", route: "/ml/diagnostics/reports", target: "reports-overview", titleKey: "tour.reports.title", bodyKey: "tour.reports.body", visual: "report" },
  { id: "finish", route: "/journey", target: "journey-tabs", titleKey: "tour.finish.title", bodyKey: "tour.finish.body", visual: "chart" },
];

type Rect = { top: number; left: number; width: number; height: number };

export function GuidedAssistant() {
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const initialized = useRef(false);
  const [open, setOpen] = useState(true);
  const [active, setActive] = useState(true);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const [targetFound, setTargetFound] = useState(false);
  const step = steps[index];

  const routePath = useMemo(() => step.route.split("?")[0], [step.route]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    setIndex(initialStepIndex(pathname));
  }, [pathname]);

  useEffect(() => {
    if (!active || !step) return;
    const timer = window.setTimeout(() => focusTarget(step.target), pathname === routePath ? 120 : 620);
    return () => window.clearTimeout(timer);
  }, [active, index, pathname, routePath, step]);

  useEffect(() => {
    if (!active || !step) return;
    const handle = () => focusTarget(step.target, false);
    window.addEventListener("resize", handle);
    window.addEventListener("scroll", handle, true);
    return () => {
      window.removeEventListener("resize", handle);
      window.removeEventListener("scroll", handle, true);
    };
  }, [active, step]);

  function startTour() {
    setOpen(true);
    setActive(true);
    setIndex(0);
    router.push(steps[0].route);
  }

  function go(nextIndex: number) {
    const bounded = Math.max(0, Math.min(steps.length - 1, nextIndex));
    setIndex(bounded);
    const nextStep = steps[bounded];
    router.push(nextStep.route);
  }

  function focusTarget(target: string, shouldScroll = true) {
    const element = document.querySelector<HTMLElement>(`[data-tour-id="${target}"]`);
    if (!element) {
      setTargetFound(false);
      setRect(null);
      return;
    }
    if (shouldScroll) {
      element.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
    }
    const box = element.getBoundingClientRect();
    setTargetFound(true);
    setRect({
      top: Math.max(12, box.top - 10),
      left: Math.max(12, box.left - 10),
      width: Math.min(window.innerWidth - 24, box.width + 20),
      height: Math.min(window.innerHeight - 24, box.height + 20),
    });
  }

  if (!open) {
    return (
      <button type="button" className="guided-assistant-launch" onClick={startTour} aria-label={t("assistant.button")}>
        <Bot className="h-5 w-5" />
        <span>{t("assistant.button")}</span>
      </button>
    );
  }

  return (
    <>
      {active ? (
        <div className="guided-tour-layer" aria-hidden="true">
          {rect ? <div className="guided-tour-spotlight" style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }} /> : null}
          <AnimatedDataFlow visual={step.visual} rect={rect} />
        </div>
      ) : null}
      <section className="guided-assistant-panel" aria-live="polite">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="guided-assistant-orb">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                {t("assistant.step")} {index + 1}/{steps.length}
              </div>
              <h2 className="mt-1 text-lg font-semibold text-ink">{t(step.titleKey)}</h2>
            </div>
          </div>
          <button
            type="button"
            className="rounded-md p-2 text-muted transition hover:bg-surface-muted hover:text-ink"
            onClick={() => {
              setOpen(false);
              setActive(false);
            }}
            aria-label={t("common.close")}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-3 text-sm leading-6 text-secondary">{t(step.bodyKey)}</p>
        {!targetFound ? <p className="mt-2 rounded-md border border-warn-border bg-warn-soft px-3 py-2 text-xs font-medium text-warn-text">{t("assistant.missingTarget")}</p> : null}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="secondary" onClick={() => router.push(step.route)}>
            <LocateFixed className="h-4 w-4" />
            {t("common.open")}
          </Button>
          <Button variant="secondary" disabled={index === 0} onClick={() => go(index - 1)}>
            <ChevronLeft className="h-4 w-4" />
            {t("common.prev")}
          </Button>
          <Button onClick={() => go(index + 1)} disabled={index === steps.length - 1}>
            {t("common.next")}
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" onClick={() => setActive((value) => !value)}>
            <Compass className="h-4 w-4" />
            {active ? t("assistant.pause") : t("assistant.start")}
          </Button>
        </div>
      </section>
    </>
  );
}

function initialStepIndex(pathname: string): number {
  if (pathname.startsWith("/ml/diagnostics/reports")) return steps.findIndex((step) => step.id === "reports");
  if (pathname.startsWith("/ml")) return steps.findIndex((step) => step.id === "ml");
  if (pathname.startsWith("/articles")) return steps.findIndex((step) => step.id === "articles");
  if (pathname.startsWith("/text-mining")) return steps.findIndex((step) => step.id === "text");
  if (pathname.startsWith("/analysis")) return steps.findIndex((step) => step.id === "analysis");
  if (pathname.startsWith("/data-quality")) return steps.findIndex((step) => step.id === "quality");
  if (pathname.startsWith("/jobs")) return steps.findIndex((step) => step.id === "jobs");
  if (pathname.startsWith("/journey")) return steps.findIndex((step) => step.id === "welcome");
  if (pathname === "/") return steps.findIndex((step) => step.id === "workflow");
  return 0;
}

function AnimatedDataFlow({ visual, rect }: { visual: TourStep["visual"]; rect: Rect | null }) {
  const style = rect
    ? {
        "--flow-top": `${rect.top + rect.height / 2}px`,
        "--flow-left": `${rect.left + rect.width / 2}px`,
      } as CSSProperties
    : undefined;
  return (
    <div className={clsx("guided-data-flow", `guided-data-flow-${visual}`)} style={style}>
      <span />
      <span />
      <span />
      <span />
      <span />
      <span />
    </div>
  );
}
