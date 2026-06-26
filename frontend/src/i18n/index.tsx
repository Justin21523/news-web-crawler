"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Locale = "zh-TW" | "en-US";

type Dictionary = Record<string, string>;

const dictionaries: Record<Locale, Dictionary> = {
  "zh-TW": {
    "nav.dashboard": "總覽",
    "nav.dataQuality": "資料品質",
    "nav.analysis": "分析儀表板",
    "nav.textMining": "Text Mining",
    "nav.ml": "ML Models",
    "nav.articles": "文章資料庫",
    "nav.jobs": "Pipeline Jobs",
    "nav.journey": "導覽 Journey",
    "nav.settings": "設定",
    "shell.workspace": "工作區",
    "shell.console": "分析控制台",
    "shell.status": "Portfolio Demo",
    "shell.language": "語言",
    "common.loading": "載入中",
    "common.export": "匯出",
    "common.start": "開始",
    "common.next": "下一步",
    "common.prev": "上一步",
    "common.close": "關閉",
    "common.open": "前往",
    "common.sample": "使用 sample data",
    "common.upload": "上傳資料",
    "assistant.button": "導覽小幫手",
    "assistant.start": "開始作品集導覽",
    "assistant.pause": "收合導覽",
    "assistant.step": "步驟",
    "assistant.missingTarget": "此區塊尚未出現在目前畫面，請按前往切換到對應頁面。",
    "journey.title": "Pipeline Journey 導覽中心",
    "journey.subtitle": "用視覺化步驟帶面試官從原始新聞資料一路看到清理、文字探勘、ML 分析與報表輸出。",
    "journey.badge": "Interactive Demo",
    "journey.uploadTitle": "資料上傳與 Sample Demo",
    "journey.uploadDetail": "上傳 CSV / JSON / JSONL 後會轉成 pipeline JSONL；如果沒有資料，可以直接跑內建 sample dataset。",
    "journey.uploadCta": "上傳並建立 ingest job",
    "journey.sampleCta": "啟動 sample pipeline",
    "journey.currentUpload": "目前匯入",
    "journey.noUpload": "尚未上傳資料，導覽會使用 sample data 說明完整流程。",
    "journey.tabsTitle": "資料生命週期",
    "journey.pipelineTitle": "Workflow 狀態",
    "journey.pipelineDetail": "這裡對應 Jobs 頁面的真實 pipeline status，方便展示每一步是否完成。",
    "journey.openPage": "開啟相關頁面",
    "journey.meaning": "這一步的意義",
    "journey.output": "產出內容",
    "journey.interaction": "互動方式",
    "page.dashboard.title": "執行總覽",
    "page.dashboard.subtitle": "集中查看資料完整度、處理流程與分析準備度。",
    "page.quality.title": "資料品質",
    "page.quality.subtitle": "在分析前檢查完整度、覆蓋率與資料可用性。",
    "page.analysis.title": "分析儀表板",
    "page.analysis.subtitle": "EDA、趨勢分析、來源/分類 intelligence、keywords、entities 與 business insights。",
    "page.textMining.title": "Text Mining 工作台",
    "page.textMining.subtitle": "TF-IDF、n-grams、topic modeling、clustering、similarity search 與 co-occurrence networks。",
    "page.articles.title": "文章資料庫",
    "page.articles.subtitle": "Facet search、ranking、drill-down 與 article-level intelligence。",
    "page.ml.title": "Machine Learning",
    "page.ml.subtitle": "新聞 intelligence 的 baseline classification、model comparison 與可解釋 Decision Tree 分析。",
    "page.jobs.title": "Pipeline Jobs",
    "page.jobs.subtitle": "執行 crawler、ingest、NLP、export、analysis 與 ML tasks。",
    "page.reports.title": "Diagnostics Report Library",
    "page.reports.subtitle": "搜尋、比較、預覽與下載 ML diagnostics report artifacts。",
    "tour.welcome.title": "歡迎來到 News Data Intelligence Platform",
    "tour.welcome.body": "這個導覽會帶你展示作品集重點：資料上傳、pipeline、資料品質、Text Mining、ML Diagnostics、文章探索與報表。",
    "tour.upload.title": "從資料開始",
    "tour.upload.body": "可上傳 CSV / JSON / JSONL；若沒有真實資料，直接啟動 sample pipeline，面試展示不會卡在資料準備。",
    "tour.jobs.title": "執行 Pipeline Jobs",
    "tour.jobs.body": "Jobs 頁面負責啟動 demo、ingest、NLP、analysis、ML training 與 reports，並追蹤 logs。",
    "tour.workflow.title": "Workflow 不是裝飾",
    "tour.workflow.body": "每個 step 會反映後端資料狀態，讓使用者理解資料處理進度。",
    "tour.quality.title": "資料品質分析",
    "tour.quality.body": "檢查 missing fields、invalid URL、duplicate、length、source/category/date coverage，並能 drill down 到文章。",
    "tour.analysis.title": "EDA / Business Analysis",
    "tour.analysis.body": "用分頁式儀表板呈現 trend、source/category intelligence、topic intelligence 與 business insights。",
    "tour.text.title": "Text Mining 工作台",
    "tour.text.body": "包含 TF-IDF、n-gram、collocation、co-occurrence、topic modeling、clustering、similarity search 與 network graph。",
    "tour.entities.title": "Entity Intelligence",
    "tour.entities.body": "用 fallback/model NER 產生 entity preview、共現關係與 media monitoring 觀察角度。",
    "tour.articles.title": "可探索文章資料庫",
    "tour.articles.body": "Articles 支援 facets、搜尋、topic/cluster 篩選與 detail panel，能快速找到對應新聞與內文。",
    "tour.ml.title": "ML Models 與 Diagnostics",
    "tour.ml.body": "呈現 baseline classification、confusion heatmap、error analysis、feature importance 與 model recommendation narrative。",
    "tour.reports.title": "報表與作品集輸出",
    "tour.reports.body": "Diagnostics reports 可匯出 HTML / Markdown / Excel / PDF fallback，方便展示模型表現與失敗因素。",
    "tour.finish.title": "導覽完成",
    "tour.finish.body": "你可以回到 Journey 頁重新展示資料生命週期，或直接切換到任一模組做深度 demo。",
  },
  "en-US": {
    "nav.dashboard": "Dashboard",
    "nav.dataQuality": "Data Quality",
    "nav.analysis": "Analysis",
    "nav.textMining": "Text Mining",
    "nav.ml": "ML Models",
    "nav.articles": "Articles",
    "nav.jobs": "Jobs",
    "nav.journey": "Journey",
    "nav.settings": "Settings",
    "shell.workspace": "Workspace",
    "shell.console": "Analytics Console",
    "shell.status": "Portfolio Demo",
    "shell.language": "Language",
    "common.loading": "Loading",
    "common.export": "Export",
    "common.start": "Start",
    "common.next": "Next",
    "common.prev": "Back",
    "common.close": "Close",
    "common.open": "Open",
    "common.sample": "Use sample data",
    "common.upload": "Upload data",
    "assistant.button": "Guided Assistant",
    "assistant.start": "Start portfolio tour",
    "assistant.pause": "Collapse tour",
    "assistant.step": "Step",
    "assistant.missingTarget": "This section is not visible on the current screen. Use Open to jump to the matching page.",
    "journey.title": "Pipeline Journey Center",
    "journey.subtitle": "Walk interviewers from raw news data through cleaning, text mining, ML diagnostics, and report export.",
    "journey.badge": "Interactive Demo",
    "journey.uploadTitle": "Upload Data or Use Sample Demo",
    "journey.uploadDetail": "CSV / JSON / JSONL uploads are normalized into pipeline JSONL. Without a file, use the built-in sample dataset.",
    "journey.uploadCta": "Upload and create ingest job",
    "journey.sampleCta": "Run sample pipeline",
    "journey.currentUpload": "Current upload",
    "journey.noUpload": "No upload yet. The tour will use sample data to explain the complete workflow.",
    "journey.tabsTitle": "Data Lifecycle",
    "journey.pipelineTitle": "Workflow Status",
    "journey.pipelineDetail": "This mirrors the real pipeline status used by the Jobs page.",
    "journey.openPage": "Open related page",
    "journey.meaning": "Why it matters",
    "journey.output": "Output",
    "journey.interaction": "Interaction",
    "page.dashboard.title": "Executive Dashboard",
    "page.dashboard.subtitle": "Data completeness, processing flow, and analysis readiness.",
    "page.quality.title": "Data Quality",
    "page.quality.subtitle": "Completeness, coverage, and readiness checks before analysis.",
    "page.analysis.title": "Analysis Dashboard",
    "page.analysis.subtitle": "EDA, trend analysis, source/category intelligence, keywords, entities, and business insights.",
    "page.textMining.title": "Text Mining Workbench",
    "page.textMining.subtitle": "TF-IDF, n-grams, topic modeling, clustering, similarity search, and co-occurrence networks.",
    "page.articles.title": "Articles",
    "page.articles.subtitle": "Facet search, ranking, drill-down, and article-level intelligence.",
    "page.ml.title": "Machine Learning",
    "page.ml.subtitle": "Baseline classification, model comparison, and interpretable Decision Tree analysis for news intelligence.",
    "page.jobs.title": "Pipeline Jobs",
    "page.jobs.subtitle": "Run crawler, ingest, NLP, export, analysis, and ML tasks.",
    "page.reports.title": "Diagnostics Report Library",
    "page.reports.subtitle": "Search, compare, preview, and download ML diagnostics report artifacts.",
    "tour.welcome.title": "Welcome to News Data Intelligence Platform",
    "tour.welcome.body": "This tour highlights the portfolio story: upload, pipeline, data quality, text mining, ML diagnostics, article exploration, and reports.",
    "tour.upload.title": "Start with Data",
    "tour.upload.body": "Upload CSV / JSON / JSONL, or run the sample pipeline when no real dataset is available.",
    "tour.jobs.title": "Run Pipeline Jobs",
    "tour.jobs.body": "Jobs starts demo, ingest, NLP, analysis, ML training, and reports while tracking logs.",
    "tour.workflow.title": "Workflow Reflects Real State",
    "tour.workflow.body": "Each step is tied to backend data state so users can understand pipeline progress.",
    "tour.quality.title": "Data Quality Analysis",
    "tour.quality.body": "Check missing fields, invalid URLs, duplicates, length, source/category/date coverage, and drill down to articles.",
    "tour.analysis.title": "EDA / Business Analysis",
    "tour.analysis.body": "Tabbed dashboards cover trend, source/category intelligence, topic intelligence, and business insights.",
    "tour.text.title": "Text Mining Workbench",
    "tour.text.body": "TF-IDF, n-grams, collocation, co-occurrence, topic modeling, clustering, similarity search, and network graphs.",
    "tour.entities.title": "Entity Intelligence",
    "tour.entities.body": "Fallback/model NER powers entity previews, co-occurrence relations, and media monitoring views.",
    "tour.articles.title": "Explorable Article Database",
    "tour.articles.body": "Articles supports facets, search, topic/cluster filters, and detail panels for full content review.",
    "tour.ml.title": "ML Models and Diagnostics",
    "tour.ml.body": "Baseline classifiers, confusion heatmaps, error analysis, feature importance, and model recommendation narrative.",
    "tour.reports.title": "Reports and Portfolio Output",
    "tour.reports.body": "Diagnostics reports export to HTML / Markdown / Excel / PDF fallback for model performance storytelling.",
    "tour.finish.title": "Tour Complete",
    "tour.finish.body": "Return to Journey for the lifecycle story, or jump into any module for a deeper demo.",
  },
};

const I18nContext = createContext<{
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
} | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("zh-TW");

  useEffect(() => {
    const saved = window.localStorage.getItem("news-intel-locale") as Locale | null;
    if (saved === "zh-TW" || saved === "en-US") {
      setLocaleState(saved);
    }
  }, []);

  const setLocale = (value: Locale) => {
    setLocaleState(value);
    window.localStorage.setItem("news-intel-locale", value);
    document.documentElement.lang = value === "zh-TW" ? "zh-Hant" : "en";
  };

  useEffect(() => {
    document.documentElement.lang = locale === "zh-TW" ? "zh-Hant" : "en";
  }, [locale]);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t: (key: string) => dictionaries[locale][key] ?? dictionaries["en-US"][key] ?? key,
    }),
    [locale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider");
  }
  return context;
}
