import type {
  ArticleDetail,
  ArticleListResponse,
  FacetsResponse,
  HealthResponse,
  ImportUploadResponse,
  LiveSummaryResponse,
  RelatedArticle,
  SummaryResponse,
  AnalysisCategoryResponse,
  AnalysisDashboardResponse,
  AnalysisKeywordEntityResponse,
  AnalysisOverviewResponse,
  AnalysisReport,
  ArticleExplanationResponse,
  ArticlePredictionResponse,
  AssignmentListResponse,
  AssignmentRunResponse,
  AnalysisSourceResponse,
  AnalysisTrendResponse,
  BurstTrendResponse,
  BusinessInsightResponse,
  ClusterResponse,
  CollocationResponse,
  CooccurrenceResponse,
  DataQualityIssueListResponse,
  DataQualityResponse,
  IRHealthResponse,
  JobRecord,
  DecisionPathResponse,
  DecisionTreeResponse,
  EntityExtractionCompareResponse,
  EntityExtractionRunListResponse,
  EntityExtractionRunResponse,
  EntityMiningResponse,
  EntityProviderListResponse,
  MLCompareResponse,
  MLDiagnosticsResponse,
  MLDiagnosticsReportBulkResponse,
  MLDiagnosticsReportCompareResponse,
  MLDiagnosticsReportDetailResponse,
  MLDiagnosticsReportListResponse,
  MLArtifactCompareResponse,
  MLArtifactDiagnosticsCompareResponse,
  MLArtifactDetail,
  MLArtifactListResponse,
  MLDatasetResponse,
  MLErrorSamplesResponse,
  MLOverviewResponse,
  MLTrainResponse,
  NetworkResponse,
  NgramResponse,
  PipelineStatusResponse,
  RelationshipMiningResponse,
  SimilarityResponse,
  StatsResponse,
  TextMiningOverviewResponse,
  TfidfResponse,
  TopicModelResponse,
} from "@/lib/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8011/api/v1";

type QueryValue = string | number | boolean | null | undefined;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function requestText(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.text();
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.blob();
}

async function requestForm<T>(path: string, formData: FormData, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    method: init?.method ?? "POST",
    body: formData,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function qs(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  stats: () => request<StatsResponse>("/stats"),
  facets: () => request<FacetsResponse>("/facets"),
  dataQuality: () => request<DataQualityResponse>("/data-quality"),
  dataQualityIssues: (params: Record<string, QueryValue>) =>
    request<DataQualityIssueListResponse>(`/data-quality/issues${qs(params)}`),
  dataQualityExportUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/data-quality/export${qs(params)}`,
  pipelineStatus: () => request<PipelineStatusResponse>("/pipeline/status"),
  analysisOverview: () => request<AnalysisOverviewResponse>("/analysis/overview"),
  analysisDashboard: (params: Record<string, QueryValue>) =>
    request<AnalysisDashboardResponse>(`/analysis/dashboard${qs(params)}`),
  analysisTrends: (params: Record<string, QueryValue>) =>
    request<AnalysisTrendResponse>(`/analysis/trends${qs(params)}`),
  analysisSources: (params: Record<string, QueryValue>) =>
    request<AnalysisSourceResponse>(`/analysis/sources${qs(params)}`),
  analysisCategories: (params: Record<string, QueryValue>) =>
    request<AnalysisCategoryResponse>(`/analysis/categories${qs(params)}`),
  analysisKeywordsEntities: (params: Record<string, QueryValue>) =>
    request<AnalysisKeywordEntityResponse>(`/analysis/keywords-entities${qs(params)}`),
  analysisBusinessInsights: (params: Record<string, QueryValue>) =>
    request<BusinessInsightResponse>(`/analysis/business-insights${qs(params)}`),
  analysisLiveSummary: (params: Record<string, QueryValue>) =>
    request<LiveSummaryResponse>(`/analysis/live-summary${qs(params)}`),
  analysisExportUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/analysis/export${qs(params)}`,
  textMiningOverview: (params: Record<string, QueryValue>) =>
    request<TextMiningOverviewResponse>(`/text-mining/overview${qs(params)}`),
  textMiningTfidf: (params: Record<string, QueryValue>) =>
    request<TfidfResponse>(`/text-mining/tfidf${qs(params)}`),
  textMiningNgrams: (params: Record<string, QueryValue>) =>
    request<NgramResponse>(`/text-mining/ngrams${qs(params)}`),
  textMiningTopics: (params: Record<string, QueryValue>) =>
    request<TopicModelResponse>(`/text-mining/topics${qs(params)}`),
  textMiningClusters: (params: Record<string, QueryValue>) =>
    request<ClusterResponse>(`/text-mining/clusters${qs(params)}`),
  textMiningSimilarity: (params: Record<string, QueryValue>) =>
    request<SimilarityResponse>(`/text-mining/similarity${qs(params)}`),
  textMiningNetwork: (params: Record<string, QueryValue>) =>
    request<NetworkResponse>(`/text-mining/network${qs(params)}`),
  textMiningCollocations: (params: Record<string, QueryValue>) =>
    request<CollocationResponse>(`/text-mining/collocations${qs(params)}`),
  textMiningCooccurrence: (params: Record<string, QueryValue>) =>
    request<CooccurrenceResponse>(`/text-mining/co-occurrence${qs(params)}`),
  textMiningRelationships: (params: Record<string, QueryValue>) =>
    request<RelationshipMiningResponse>(`/text-mining/relationships${qs(params)}`),
  textMiningBursts: (params: Record<string, QueryValue>) =>
    request<BurstTrendResponse>(`/text-mining/bursts${qs(params)}`),
  textMiningEntities: (params: Record<string, QueryValue>) =>
    request<EntityMiningResponse>(`/text-mining/entities${qs(params)}`),
  entityProviders: () => request<EntityProviderListResponse>("/entity-extraction/providers"),
  entityExtractionRuns: (params: Record<string, QueryValue>) =>
    request<EntityExtractionRunListResponse>(`/entity-extraction/runs${qs(params)}`),
  runEntityExtraction: (params: Record<string, QueryValue>) =>
    request<EntityExtractionRunResponse>(`/entity-extraction/run${qs(params)}`, { method: "POST" }),
  compareEntityExtraction: (params: Record<string, QueryValue>) =>
    request<EntityExtractionCompareResponse>(`/entity-extraction/compare${qs(params)}`),
  textMiningPersistAssignments: (params: Record<string, QueryValue>) =>
    request<AssignmentRunResponse>(`/text-mining/assignments${qs(params)}`, { method: "POST" }),
  textMiningAssignmentsLatest: (params: Record<string, QueryValue>) =>
    request<AssignmentListResponse>(`/text-mining/assignments/latest${qs(params)}`),
  textMiningArticleAssignments: (id: string) =>
    request<AssignmentListResponse>(`/text-mining/assignments/articles/${encodeURIComponent(id)}`),
  textMiningExportUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/text-mining/export${qs(params)}`,
  mlOverview: (params: Record<string, QueryValue>) =>
    request<MLOverviewResponse>(`/ml/overview${qs(params)}`),
  mlDataset: (params: Record<string, QueryValue>) =>
    request<MLDatasetResponse>(`/ml/dataset${qs(params)}`),
  mlTrain: (params: Record<string, QueryValue>) =>
    request<MLTrainResponse>(`/ml/train${qs(params)}`),
  mlCompare: (params: Record<string, QueryValue>) =>
    request<MLCompareResponse>(`/ml/compare${qs(params)}`),
  mlDiagnostics: (params: Record<string, QueryValue>) =>
    request<MLDiagnosticsResponse>(`/ml/diagnostics${qs(params)}`),
  mlDiagnosticsErrors: (params: Record<string, QueryValue>) =>
    request<MLErrorSamplesResponse>(`/ml/diagnostics/errors${qs(params)}`),
  mlDiagnosticsReports: (params: Record<string, QueryValue>) =>
    request<MLDiagnosticsReportListResponse>(`/ml/diagnostics/reports${qs(params)}`),
  mlDiagnosticsReport: (id: string) =>
    request<MLDiagnosticsReportDetailResponse>(`/ml/diagnostics/reports/${encodeURIComponent(id)}`),
  mlDiagnosticsReportsCompare: (params: Record<string, QueryValue>) =>
    request<MLDiagnosticsReportCompareResponse>(`/ml/diagnostics/reports/compare${qs(params)}`),
  mlDiagnosticsReportsBulk: (body: Record<string, unknown>) =>
    request<MLDiagnosticsReportBulkResponse>("/ml/diagnostics/reports/bulk", { method: "POST", body: JSON.stringify(body) }),
  mlDiagnosticsReportsBulkExport: (body: Record<string, unknown>) =>
    requestBlob("/ml/diagnostics/reports/bulk/export", { method: "POST", body: JSON.stringify(body) }),
  mlDiagnosticsReportsCompareDownloadUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/ml/diagnostics/reports/compare/download${qs(params)}`,
  mlDiagnosticsReportDownloadUrl: (id: string, format: string) =>
    `${API_BASE}/ml/diagnostics/reports/${encodeURIComponent(id)}/download${qs({ format })}`,
  mlDiagnosticsReportDetailUrl: (id: string) =>
    `/ml/diagnostics/reports/${encodeURIComponent(id)}`,
  mlDiagnosticsReportPreviewUrl: (id: string) =>
    `${API_BASE}/ml/diagnostics/reports/${encodeURIComponent(id)}/download${qs({ format: "html" })}`,
  mlDiagnosticsReportPreviewHtml: (id: string) =>
    requestText(`${API_BASE}/ml/diagnostics/reports/${encodeURIComponent(id)}/download${qs({ format: "html" })}`),
  mlPredictArticle: (id: string, params: Record<string, QueryValue>) =>
    request<ArticlePredictionResponse>(`/ml/predict/article/${encodeURIComponent(id)}${qs(params)}`),
  mlArticleExplanation: (id: string, params: Record<string, QueryValue>) =>
    request<ArticleExplanationResponse>(`/ml/predict/article/${encodeURIComponent(id)}/explanation${qs(params)}`),
  mlDecisionTree: (params: Record<string, QueryValue>) =>
    request<DecisionTreeResponse>(`/ml/decision-tree${qs(params)}`),
  mlDecisionPath: (params: Record<string, QueryValue>) =>
    request<DecisionPathResponse>(`/ml/decision-tree/path${qs(params)}`),
  mlDecisionTreeImageUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/ml/decision-tree/image${qs(params)}`,
  mlExportUrl: (params: Record<string, QueryValue>) =>
    `${API_BASE}/ml/export${qs(params)}`,
  mlArtifacts: (params: Record<string, QueryValue>) =>
    request<MLArtifactListResponse>(`/ml/artifacts${qs(params)}`),
  mlArtifact: (id: string) => request<MLArtifactDetail>(`/ml/artifacts/${encodeURIComponent(id)}`),
  mlArtifactCompare: (params: Record<string, QueryValue>) =>
    request<MLArtifactCompareResponse>(`/ml/artifacts/compare${qs(params)}`),
  mlArtifactDiagnosticsCompare: (params: Record<string, QueryValue>) =>
    request<MLArtifactDiagnosticsCompareResponse>(`/ml/artifacts/diagnostics/compare${qs(params)}`),
  mlArtifactDownloadUrl: (id: string, file: string) =>
    `${API_BASE}/ml/artifacts/${encodeURIComponent(id)}/download${qs({ file })}`,
  analysisReport: (name: string) => request<AnalysisReport>(`/analysis/${encodeURIComponent(name)}`),
  collocations: () => request<AnalysisReport>("/analysis/collocations"),
  irHealth: () => request<IRHealthResponse>("/analysis/ir"),
  articles: (params: Record<string, QueryValue>) =>
    request<ArticleListResponse>(`/articles${qs(params)}`),
  article: (id: string) => request<ArticleDetail>(`/articles/${encodeURIComponent(id)}`),
  articleSummary: (id: string, params: Record<string, QueryValue>) =>
    request<SummaryResponse>(`/articles/${encodeURIComponent(id)}/summary${qs(params)}`),
  relatedArticles: (id: string, params: Record<string, QueryValue>) =>
    request<RelatedArticle[]>(`/articles/${encodeURIComponent(id)}/related${qs(params)}`),
  jobs: () => request<JobRecord[]>("/jobs"),
  job: (id: number) => request<JobRecord>(`/jobs/${id}`),
  jobLogs: (id: number) => request<{ id: number; content: string }>(`/jobs/${id}/logs`),
  createJob: (type: string, params: Record<string, unknown>) =>
    request<JobRecord>("/jobs", {
      method: "POST",
      body: JSON.stringify({ type, params }),
    }),
  importUpload: (file: File, run = false) => {
    const formData = new FormData();
    formData.set("file", file);
    return requestForm<ImportUploadResponse>(`/import/upload${qs({ run })}`, formData);
  },
};
