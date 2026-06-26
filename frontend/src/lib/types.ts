export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "abandoned";

export type JobRecord = {
  id: number;
  type: string;
  status: JobStatus | string;
  params: Record<string, unknown>;
  progress_done: number;
  progress_total: number;
  log_path?: string | null;
  error?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
};

export type ImportUploadResponse = {
  upload_id: string;
  filename: string;
  detected_format: string;
  input_dir: string;
  saved_path: string;
  article_count_preview: number;
  job_id?: number | null;
  suggested_job: {
    type: string;
    params: Record<string, unknown>;
  };
  notes: string[];
};

export type StatsResponse = {
  total_articles: number;
  cleaned: number;
  enriched: number;
  sources: Record<string, number>;
  date_range: [string | null, string | null];
  latest_jobs: JobRecord[];
};

export type ArticleListItem = {
  article_id: string;
  title: string;
  source: string;
  source_name?: string | null;
  publish_date?: string | null;
  category?: string | null;
  category_name?: string | null;
  status?: string | null;
  snippet: string;
  image_url?: string | null;
  relevance_score?: number | null;
  char_count: number;
  keywords: string[];
  entities: string[];
};

export type ArticleListResponse = {
  items: ArticleListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type ArticleDetail = ArticleListItem & {
  url: string;
  author?: string | null;
  content_clean: string;
  tags: string[];
  crawled_at?: string | null;
  cleaned_at?: string | null;
  char_count: number;
  word_count: number;
  nlp?: {
    tokens: string[];
    entities: Array<[string, string]>;
    keywords: Array<[string, number]>;
    keyword_summary: string;
    model_version: string;
    entity_source?: string;
    entity_run_id?: string;
    enriched_at: string;
  } | null;
  quality_issues: DataQualityIssue[];
  assignments: Array<Record<string, string | number | Array<Record<string, string | number>>>>;
};

export type FacetsResponse = {
  sources: string[];
  categories: string[];
  statuses: string[];
  source_counts: Array<{ value: string; count: number }>;
  category_counts: Array<{ value: string; count: number }>;
  status_counts: Array<{ value: string; count: number }>;
  issue_type_counts: Array<{ value: string; count: number }>;
  keyword_counts: Array<{ value: string; count: number }>;
  entity_counts: Array<{ value: string; count: number }>;
  topic_counts: Array<{ value: string; count: number }>;
  cluster_counts: Array<{ value: string; count: number }>;
  length_buckets: Array<{ value: string; count: number }>;
  date_range: [string | null, string | null];
};

export type RelatedArticle = {
  article_id: string;
  title: string;
  source: string;
  category: string;
  score: number;
  snippet: string;
};

export type SummaryResponse = {
  article_id: string;
  method: string;
  sentences: string[];
  compression_ratio: number;
  provider: string;
  notes: string[];
};

export type HealthResponse = {
  status: string;
  db_path: string;
  data_dir: string;
};

export type DataQualityMetric = {
  key: string;
  label: string;
  value: number;
  total?: number | null;
  percent?: number | null;
  severity: "good" | "warning" | "danger" | "neutral";
};

export type DataQualityIssue = {
  article_id: string;
  title: string;
  source: string;
  category: string;
  category_name: string;
  publish_date?: string | null;
  char_count: number;
  issue_type: string;
  severity: "info" | "warning" | "danger";
  message: string;
  suggested_fix: string;
};

export type DataQualityResponse = {
  total_articles: number;
  completeness_score: number;
  quality_score: number;
  metrics: DataQualityMetric[];
  issues: DataQualityIssue[];
  issue_counts: Record<string, number>;
  severity_counts: Record<string, number>;
  missing_fields: Record<string, number>;
  source_coverage: Record<string, number>;
  category_coverage: Record<string, number>;
  date_coverage: Array<{ date: string; count: number }>;
  length_distribution: Array<{ bucket: string; count: number }>;
  date_range: [string | null, string | null];
  recommendations: string[];
};

export type DataQualityIssueListResponse = {
  items: DataQualityIssue[];
  total: number;
  page: number;
  page_size: number;
};

export type PipelineStep = {
  key: string;
  label: string;
  status: "not_started" | "ready" | "running" | "complete" | "warning" | "failed";
  count: number;
  total: number;
  detail: string;
};

export type PipelineStatusResponse = {
  steps: PipelineStep[];
  current_step: string;
  completion_percent: number;
};

export type AnalysisReport = {
  name: string;
  status: "ready" | "missing" | "insufficient_data" | "error";
  summary: string;
  updated_at?: string | null;
  data: unknown;
};

export type AnalysisOverviewResponse = {
  reports: AnalysisReport[];
  nlp_documents: number;
  analyzed_documents: number;
  recommendations: string[];
};

export type IRHealthResponse = {
  indexed_articles: number;
  total_articles: number;
  index_coverage_percent: number;
  sample_queries: Array<{ query: string; matches: number }>;
};

export type AnalysisDashboardResponse = {
  kpis: Record<string, number | string>;
  source_distribution: Array<{ name: string; count: number }>;
  category_distribution: Array<{ name: string; count: number }>;
  daily_volume: Array<{ date: string; count: number }>;
  top_keywords: Array<{ keyword: string; score: number }>;
  top_entities: Array<{ entity: string; type: string; count: number }>;
  sentiment_summary: Array<{ label: string; count: number }>;
  insights: Array<{ title: string; metric?: string; detail: string }>;
  notes: string[];
};

export type AnalysisTrendResponse = {
  daily_volume: Array<{ date: string; count: number }>;
  category_trend: Array<Record<string, string | number>>;
  source_trend: Array<Record<string, string | number>>;
  keyword_trend: Array<{ date: string; keyword: string; count: number }>;
  notes: string[];
};

export type AnalysisSourceResponse = {
  source_volume: Array<{ name: string; count: number }>;
  source_category_matrix: Array<{ source: string; category: string; count: number }>;
  source_keyword_profile: Array<{ source: string; keyword: string; count: number }>;
  insights: Array<{ title: string; detail: string }>;
};

export type AnalysisCategoryResponse = {
  category_distribution: Array<{ name: string; count: number }>;
  category_source_mix: Array<{ category: string; source: string; count: number }>;
  category_keywords: Array<{ group: string; keyword: string; count: number }>;
  insights: Array<{ title: string; detail: string }>;
};

export type AnalysisKeywordEntityResponse = {
  top_keywords: Array<{ keyword: string; score: number }>;
  keyword_by_source: Array<{ source: string; keyword: string; count: number }>;
  keyword_by_category: Array<{ group: string; keyword: string; count: number }>;
  top_entities: Array<{ entity: string; type: string; count: number }>;
  entity_by_source: Array<{ source: string; entity: string; type: string; count: number }>;
  entity_by_category: Array<{ group: string; entity: string; type: string; count: number }>;
  notes: string[];
};

export type BusinessInsightResponse = {
  cards: Array<{ title: string; metric?: string; detail: string }>;
  recommendations: Array<{ title: string; detail: string }>;
  risks: Array<{ title: string; severity: string; detail: string }>;
  tables: Record<string, Array<Record<string, string | number>>>;
};

export type LiveSummaryResponse = {
  status: "ready" | "insufficient_data" | "error";
  summary: string;
  bullets: string[];
  top_terms: Array<{ keyword: string; score: number }>;
  representative_articles: Array<Record<string, string | number | null>>;
  notes: string[];
  provider: string;
};

export type TextMiningBaseResponse = {
  status: "ready" | "insufficient_data" | "dependency_missing" | "error";
  total_documents: number;
  notes: string[];
};

export type TextMiningOverviewResponse = TextMiningBaseResponse & {
  top_keywords: Array<{ keyword: string; score: number }>;
  top_ngrams: Array<{ ngram: string; count: number }>;
  top_entities: Array<{ entity: string; type: string; count: number }>;
  coverage: Record<string, number>;
};

export type TfidfResponse = TextMiningBaseResponse & {
  vocabulary_size: number;
  top_terms: Array<{ term: string; weight: number }>;
  document_terms: Array<{ article_id: string; terms: Array<{ term: string; weight: number }> }>;
};

export type NgramResponse = TextMiningBaseResponse & {
  n: number;
  ngrams: Array<{ ngram: string; count: number }>;
  by_source: Array<Record<string, string | number>>;
  by_category: Array<Record<string, string | number>>;
};

export type TopicModelResponse = TextMiningBaseResponse & {
  method: string;
  topics: Array<{ topic_id: number; top_terms: Array<{ term: string; weight: number }>; top_docs: Array<{ article_id: string; weight: number }> }>;
};

export type ClusterResponse = TextMiningBaseResponse & {
  method: string;
  metrics: Record<string, string | number>;
  clusters: Array<{
    cluster_id: number;
    size: number;
    top_terms: Array<{ term: string; weight: number }>;
    examples: Array<{ article_id: string; title: string }>;
    points?: Array<{ article_id: string; title: string; cluster_id: number; x: number; y: number; source: string; category: string }>;
  }>;
};

export type SimilarityResponse = TextMiningBaseResponse & {
  query?: string | null;
  article_id?: string | null;
  results: Array<{ article_id: string; title: string; source: string; category: string; score: number }>;
};

export type NetworkResponse = TextMiningBaseResponse & {
  type: "keyword" | "entity";
  nodes: Array<{ id: string; label: string; count: number; degree: number; value?: number; centrality?: number; category?: string; symbolSize?: number }>;
  edges: Array<{ source: string; target: string; weight: number; value?: number }>;
};

export type CollocationResponse = TextMiningBaseResponse & {
  metric: string;
  level: string;
  ngram_type: string;
  window_size: number;
  collocations: Array<Record<string, string | number | null>>;
  heatmap: Array<Record<string, string | number | null>>;
  source_matrix: Array<Record<string, string | number | null>>;
  category_matrix: Array<Record<string, string | number | null>>;
  trend: Array<Record<string, string | number | null>>;
  examples: Array<Record<string, string | number | null>>;
};

export type CooccurrenceResponse = TextMiningBaseResponse & {
  kind: "keyword" | "entity";
  level: string;
  weight_metric: string;
  metrics_degraded: boolean;
  nodes: Array<Record<string, string | number>>;
  edges: Array<Record<string, string | number>>;
  communities: Array<Record<string, string | number>>;
  ego_network: Array<Record<string, string | number>>;
  article_matches: Array<Record<string, string | number | null>>;
};

export type RelationshipMiningResponse = TextMiningBaseResponse & {
  active_entity_source: string;
  entity_frequency: Array<Record<string, string | number>>;
  share_of_voice: Array<Record<string, string | number>>;
  entity_network_nodes: Array<Record<string, string | number>>;
  entity_network_edges: Array<Record<string, string | number>>;
  entity_source_matrix: Array<Record<string, string | number>>;
  entity_category_matrix: Array<Record<string, string | number>>;
  entity_topic_links: Array<Record<string, string | number>>;
  entity_keyword_links: Array<Record<string, string | number>>;
  entity_trend_calendar: Array<{ date: string; count: number }>;
  risk_summary: Array<Record<string, string | number>>;
};

export type BurstTrendResponse = TextMiningBaseResponse & {
  recent_window_days: number;
  baseline_window_days: number;
  rising_terms: Array<Record<string, string | number>>;
  declining_terms: Array<Record<string, string | number>>;
  burst_terms: Array<Record<string, string | number>>;
  anomaly_timeline: Array<Record<string, string | number | boolean>>;
  calendar: Array<{ date: string; count: number }>;
  source_bursts: Array<Record<string, string | number>>;
  lifecycle: Array<Record<string, string | number>>;
};

export type EntityMiningResponse = TextMiningBaseResponse & {
  active_entity_source: string;
  active_run_id?: string | null;
  provider_status: EntityProviderStatus[];
  entity_frequency: Array<{ entity: string; type: string; count: number; source?: string; run_id?: string }>;
  entity_type_distribution: Array<{ type: string; count: number }>;
  entity_trend: Array<{ date: string; entity: string; type: string; count: number }>;
  entity_source_matrix: Array<{ source: string; entity: string; type: string; count: number }>;
  entity_category_matrix: Array<{ category: string; entity: string; type: string; count: number }>;
  cooccurrence_nodes: Array<{ id: string; label: string; count: number; degree: number; value?: number; centrality?: number; category?: string; symbolSize?: number }>;
  cooccurrence_edges: Array<{ source: string; target: string; weight: number; value?: number }>;
  representative_articles: Array<{ article_id: string; title: string; source: string; category: string; publish_date?: string | null; entities: string }>;
};

export type EntityProviderStatus = {
  provider: string;
  available: boolean;
  status: string;
  detail: string;
  model?: string | null;
};

export type EntityExtractionRun = {
  run_id: string;
  provider: string;
  strategy: string;
  status: string;
  params: Record<string, unknown>;
  metrics: Record<string, string | number | boolean | Record<string, number>>;
  error?: string | null;
  created_at?: string | null;
};

export type EntityProviderListResponse = {
  providers: EntityProviderStatus[];
  active_run_id?: string | null;
  active_entity_source: string;
};

export type EntityExtractionRunResponse = {
  status: string;
  run?: EntityExtractionRun | null;
  processed_documents: number;
  activated: boolean;
  outputs_preview: Array<Record<string, unknown>>;
  notes: string[];
};

export type EntityExtractionRunListResponse = {
  runs: EntityExtractionRun[];
};

export type EntityExtractionCompareResponse = {
  status: string;
  left_run?: EntityExtractionRun | null;
  right_run?: EntityExtractionRun | null;
  metrics: Record<string, string | number>;
  type_distribution: Array<Record<string, string | number>>;
  sample_diffs: Array<Record<string, string | number>>;
  notes: string[];
};

export type AssignmentRunResponse = TextMiningBaseResponse & {
  run_id: string;
  assignment_type: string;
  method: string;
  assignment_counts: Record<string, number>;
  labels: Record<string, Array<Record<string, unknown>>>;
  created_at?: string | null;
};

export type AssignmentListResponse = TextMiningBaseResponse & {
  runs: Array<Record<string, unknown>>;
  assignments: Array<Record<string, unknown>>;
};

export type MLStatus = "ready" | "insufficient_data" | "dependency_missing" | "error";
export type MLTarget = "category" | "source" | "sentiment";
export type MLModelName = "logistic_regression" | "linear_svm" | "naive_bayes" | "decision_tree" | "random_forest";

export type MLBaseResponse = {
  status: MLStatus;
  total_documents: number;
  notes: string[];
};

export type MLDatasetResponse = MLBaseResponse & {
  target: MLTarget;
  label_distribution: Record<string, number>;
  prepared_distribution: Record<string, number>;
  sample_rows: Array<Record<string, string | number | null>>;
  preprocessing: Record<string, string | number | boolean>;
};

export type MLOverviewResponse = MLBaseResponse & {
  targets: Record<string, { status: MLStatus; label_distribution: Record<string, number>; prepared_distribution: Record<string, number>; notes: string[] }>;
  recommended_next_steps: string[];
};

export type MLTrainResponse = MLBaseResponse & {
  target: MLTarget;
  model: MLModelName;
  metrics: Record<string, number | string>;
  train_test_split: Record<string, number | boolean>;
  vectorizer: Record<string, string | number | string[]>;
  classification_report: Record<string, unknown>;
  confusion_matrix: number[][];
  labels: string[];
  feature_importance: Array<{ feature: string; weight: number; rank: number }>;
  timings: Record<string, number>;
  class_metrics: Array<Record<string, string | number | boolean | null>>;
  sample_predictions: Array<Record<string, string | number | boolean | null>>;
  confusion_pairs: Array<Record<string, string | number | boolean | null>>;
};

export type MLCompareResponse = MLBaseResponse & {
  target: MLTarget;
  results: MLTrainResponse[];
};

export type MLDiagnosticsResponse = MLBaseResponse & {
  target: MLTarget;
  model: MLModelName;
  metrics: Record<string, number | string>;
  class_metrics: Array<Record<string, string | number | boolean | null>>;
  low_performing_classes: Array<Record<string, string | number | boolean | null>>;
  confusion_matrix: number[][];
  labels: string[];
  confusion_pairs: Array<Record<string, string | number | boolean | null>>;
  error_samples: Array<Record<string, string | number | boolean | null>>;
  sample_predictions: Array<Record<string, string | number | boolean | null>>;
  failure_factors: Array<Record<string, string | number>>;
  recommendations: Array<Record<string, string | number>>;
  feature_diagnostics: {
    vectorizer?: Record<string, string | number | string[]>;
    top_features?: Array<{ feature: string; weight: number; rank: number }>;
    vocabulary_size?: number;
    feature_limit?: number;
    notes?: string[];
  };
  train_test_split: Record<string, number | boolean>;
};

export type ArticlePredictionResponse = MLBaseResponse & {
  article_id: string;
  predictions: Array<Record<string, unknown>>;
};

export type MLErrorSamplesResponse = MLBaseResponse & {
  target: MLTarget;
  model: MLModelName;
  items: Array<Record<string, string | number | boolean | null>>;
  total: number;
  page: number;
  page_size: number;
  filters: Record<string, unknown>;
};

export type MLArtifactDiagnosticsCompareResponse = {
  status: MLStatus;
  target?: MLTarget | null;
  items: Array<Record<string, unknown>>;
  metric_deltas: Array<Record<string, string | number | null>>;
  class_deltas: Array<Record<string, string | number | null>>;
  confusion_deltas: Array<Record<string, string | number | boolean | null>>;
  best_artifact?: Record<string, unknown> | null;
  notes: string[];
};

export type ArticleExplanationResponse = MLBaseResponse & {
  article_id: string;
  target: MLTarget;
  mode: "tree_path" | "linear_coefficients" | "top_terms";
  prediction?: string | null;
  confidence?: number | null;
  actual_label?: string | null;
  model?: string | null;
  model_source: string;
  artifact_id?: string | null;
  explanation: string;
  path: Array<Record<string, string | number>>;
  contributions: Array<Record<string, string | number>>;
  probabilities: Array<Record<string, string | number>>;
};

export type MLDiagnosticsReportRecord = {
  report_id: string;
  job_id?: number | null;
  created_at?: string | null;
  template: string;
  sections: string[];
  section_status: Record<string, string>;
  report_title: string;
  prepared_for?: string | null;
  preview_url?: string | null;
  print_url?: string | null;
  pdf_url?: string | null;
  pdf_status: "not_generated" | "ready" | "fallback_html" | "error";
  pdf_fallback_reason?: string | null;
  pdf_generated_at?: string | null;
  status: "active" | "archived" | "trashed";
  tags: string[];
  archived_at?: string | null;
  trashed_at?: string | null;
  metadata_updated_at?: string | null;
  params: Record<string, unknown>;
  files: string[];
  summary_metrics: Record<string, string | number>;
  row_counts: Record<string, number>;
  notes: string[];
};

export type MLDiagnosticsReportListResponse = {
  items: MLDiagnosticsReportRecord[];
  total: number;
};

export type MLDiagnosticsReportDetailResponse = MLDiagnosticsReportRecord & {
  artifact_comparison?: Record<string, unknown> | null;
  diagnostics?: Record<string, unknown> | null;
};

export type MLDiagnosticsReportCompareResponse = {
  baseline_report_id?: string | null;
  items: MLDiagnosticsReportRecord[];
  metrics: Array<Record<string, string | number | null>>;
  metric_deltas: Array<Record<string, string | number | null>>;
  row_count_deltas: Array<Record<string, string | number | null>>;
  section_matrix: Array<Record<string, string | number | null>>;
  failure_summary: Array<Record<string, string | number | null>>;
  notes: string[];
};

export type MLDiagnosticsReportBulkResponse = {
  action: string;
  updated: number;
  missing: string[];
  items: MLDiagnosticsReportRecord[];
};

export type DecisionTreeResponse = MLTrainResponse & {
  tree: Record<string, number | string>;
};

export type DecisionPathResponse = MLBaseResponse & {
  article_id: string;
  target: MLTarget;
  prediction?: string | null;
  actual_label?: string | null;
  confidence?: number | null;
  path: Array<Record<string, string | number>>;
  explanation: string;
};

export type MLArtifactRecord = {
  artifact_id: string;
  job_id?: number | null;
  target: MLTarget;
  model: MLModelName;
  status: string;
  params: Record<string, unknown>;
  metrics: Record<string, number | string>;
  artifact_dir: string;
  error?: string | null;
  created_at?: string | null;
  files: string[];
};

export type MLArtifactListResponse = {
  items: MLArtifactRecord[];
  total: number;
};

export type MLArtifactDetail = MLArtifactRecord & {
  manifest: Record<string, unknown>;
};

export type MLArtifactCompareResponse = {
  items: Array<Record<string, string | number | null | undefined>>;
  notes: string[];
};
