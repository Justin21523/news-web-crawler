"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, BrainCircuit, ClipboardCheck, Compass, FileText, Languages, Network, Settings, Sparkles, Workflow } from "lucide-react";
import { clsx } from "clsx";

import { GuidedAssistant } from "@/components/guided-tour/GuidedAssistant";
import { useI18n } from "@/i18n";

const nav = [
  { href: "/", labelKey: "nav.dashboard", icon: BarChart3, module: "dashboard" },
  { href: "/data-quality", labelKey: "nav.dataQuality", icon: ClipboardCheck, module: "data-quality" },
  { href: "/analysis", labelKey: "nav.analysis", icon: Sparkles, module: "analysis" },
  { href: "/text-mining", labelKey: "nav.textMining", icon: Network, module: "text-mining" },
  { href: "/ml", labelKey: "nav.ml", icon: BrainCircuit, module: "ml" },
  { href: "/articles", labelKey: "nav.articles", icon: FileText, module: "articles" },
  { href: "/jobs", labelKey: "nav.jobs", icon: Workflow, module: "jobs" },
  { href: "/journey", labelKey: "nav.journey", icon: Compass, module: "analysis" },
  { href: "/settings", labelKey: "nav.settings", icon: Settings, module: "settings" },
] as const;

const moduleVars: Record<(typeof nav)[number]["module"], { color: string; soft: string }> = {
  dashboard: { color: "var(--module-dashboard)", soft: "var(--module-dashboard-soft)" },
  "data-quality": { color: "var(--module-data-quality)", soft: "var(--module-data-quality-soft)" },
  analysis: { color: "var(--module-analysis)", soft: "var(--module-analysis-soft)" },
  "text-mining": { color: "var(--module-text-mining)", soft: "var(--module-text-mining-soft)" },
  ml: { color: "var(--module-ml)", soft: "var(--module-ml-soft)" },
  articles: { color: "var(--module-articles)", soft: "var(--module-articles-soft)" },
  jobs: { color: "var(--module-jobs)", soft: "var(--module-jobs-soft)" },
  settings: { color: "var(--module-settings)", soft: "var(--module-settings-soft)" },
};

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { locale, setLocale, t } = useI18n();
  const nextLocale = locale === "zh-TW" ? "en-US" : "zh-TW";
  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-surface-elevated/95 px-4 py-5 shadow-[var(--shadow-inset)] backdrop-blur md:block">
        <Link href="/" className="block rounded-lg border border-line bg-surface px-3 py-3 shadow-card">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-soft text-primary-active shadow-[0_0_28px_rgb(34_211_238_/_0.25)]">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-semibold text-ink">News Intelligence</div>
              <div className="mt-0.5 text-xs font-medium text-muted">{t("shell.console")}</div>
            </div>
          </div>
          <div className="mt-3 inline-flex rounded-full border border-primary/25 bg-primary-soft px-2 py-1 text-[0.68rem] font-bold text-primary-active">
            {t("shell.status")}
          </div>
        </Link>
        <div className="mt-7 px-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-muted">{t("shell.workspace")}</div>
        <nav className="mt-3 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const vars = moduleVars[item.module];
            return (
              <Link
                key={item.href}
                href={item.href}
                style={active ? { backgroundColor: vars.soft, color: vars.color, borderColor: vars.color } : undefined}
                className={clsx(
                  "group relative flex items-center gap-3 rounded-md border border-transparent px-3 py-2.5 text-sm font-semibold transition",
                  active ? "shadow-sm shadow-black/20" : "text-muted hover:border-line hover:bg-surface hover:text-ink",
                )}
              >
                <span style={{ backgroundColor: active ? vars.color : vars.soft, color: active ? "var(--color-inverse)" : vars.color }} className="flex h-7 w-7 items-center justify-center rounded-md transition">
                  <Icon className="h-4 w-4" />
                </span>
                {t(item.labelKey)}
                {active ? <span style={{ backgroundColor: vars.color }} className="absolute inset-y-2 left-0 w-1 rounded-r-full" /> : null}
              </Link>
            );
          })}
        </nav>
        <button
          type="button"
          onClick={() => setLocale(nextLocale)}
          className="mt-5 flex w-full items-center justify-between rounded-md border border-line bg-surface px-3 py-2 text-sm font-semibold text-muted transition hover:border-primary/40 hover:text-ink"
        >
          <span className="inline-flex items-center gap-2">
            <Languages className="h-4 w-4" />
            {t("shell.language")}
          </span>
          <span>{locale === "zh-TW" ? "EN" : "中文"}</span>
        </button>
      </aside>
      <div className="md:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-surface/95 px-4 py-3 shadow-sm backdrop-blur md:hidden">
          <div className="flex items-center justify-between gap-3">
            <div className="font-semibold text-ink">News Intelligence</div>
            <button
              type="button"
              onClick={() => setLocale(nextLocale)}
              className="inline-flex items-center gap-2 rounded-md border border-line bg-surface-elevated px-3 py-2 text-xs font-semibold text-muted"
            >
              <Languages className="h-4 w-4" />
              {locale === "zh-TW" ? "EN" : "中文"}
            </button>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto">
            {nav.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              const vars = moduleVars[item.module];
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={active ? { backgroundColor: vars.soft, color: vars.color, borderColor: vars.color } : undefined}
                  className="whitespace-nowrap rounded-md border border-line bg-surface-elevated px-3 py-2 text-sm font-semibold text-muted"
                >
                  {t(item.labelKey)}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8">{children}</main>
      </div>
      <GuidedAssistant />
    </div>
  );
}
