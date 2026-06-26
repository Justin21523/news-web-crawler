from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


MLStatus = Literal["ready", "insufficient_data", "dependency_missing", "error"]
MLTarget = Literal["category", "source", "sentiment"]
MLModelName = Literal["logistic_regression", "linear_svm", "naive_bayes", "decision_tree", "random_forest"]


class MLBaseResponse(BaseModel):
    status: MLStatus = "ready"
    total_documents: int = 0
    notes: list[str] = Field(default_factory=list)


class MLDatasetResponse(MLBaseResponse):
    target: MLTarget = "category"
    label_distribution: dict[str, int] = Field(default_factory=dict)
    prepared_distribution: dict[str, int] = Field(default_factory=dict)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    preprocessing: dict[str, Any] = Field(default_factory=dict)


class MLOverviewResponse(MLBaseResponse):
    targets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recommended_next_steps: list[str] = Field(default_factory=list)


class MLTrainResponse(MLBaseResponse):
    target: MLTarget = "category"
    model: MLModelName = "logistic_regression"
    metrics: dict[str, Any] = Field(default_factory=dict)
    train_test_split: dict[str, Any] = Field(default_factory=dict)
    vectorizer: dict[str, Any] = Field(default_factory=dict)
    classification_report: dict[str, Any] = Field(default_factory=dict)
    confusion_matrix: list[list[int]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    feature_importance: list[dict[str, Any]] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
    class_metrics: list[dict[str, Any]] = Field(default_factory=list)
    sample_predictions: list[dict[str, Any]] = Field(default_factory=list)
    confusion_pairs: list[dict[str, Any]] = Field(default_factory=list)


class MLCompareResponse(MLBaseResponse):
    target: MLTarget = "category"
    results: list[MLTrainResponse] = Field(default_factory=list)


class DecisionTreeResponse(MLTrainResponse):
    tree: dict[str, Any] = Field(default_factory=dict)


class DecisionPathResponse(MLBaseResponse):
    article_id: str
    target: MLTarget = "category"
    prediction: str | None = None
    actual_label: str | None = None
    confidence: float | None = None
    path: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""


class MLArtifactRecord(BaseModel):
    artifact_id: str
    job_id: int | None = None
    target: MLTarget
    model: MLModelName
    status: str
    params: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    artifact_dir: str
    error: str | None = None
    created_at: str | None = None
    files: list[str] = Field(default_factory=list)


class MLArtifactListResponse(BaseModel):
    items: list[MLArtifactRecord] = Field(default_factory=list)
    total: int = 0


class MLArtifactDetail(MLArtifactRecord):
    manifest: dict[str, Any] = Field(default_factory=dict)


class MLArtifactCompareResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MLDiagnosticsResponse(MLBaseResponse):
    target: MLTarget = "category"
    model: MLModelName = "logistic_regression"
    metrics: dict[str, Any] = Field(default_factory=dict)
    class_metrics: list[dict[str, Any]] = Field(default_factory=list)
    low_performing_classes: list[dict[str, Any]] = Field(default_factory=list)
    confusion_matrix: list[list[int]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    confusion_pairs: list[dict[str, Any]] = Field(default_factory=list)
    error_samples: list[dict[str, Any]] = Field(default_factory=list)
    sample_predictions: list[dict[str, Any]] = Field(default_factory=list)
    failure_factors: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    feature_diagnostics: dict[str, Any] = Field(default_factory=dict)
    train_test_split: dict[str, Any] = Field(default_factory=dict)


class ArticlePredictionResponse(MLBaseResponse):
    article_id: str
    predictions: list[dict[str, Any]] = Field(default_factory=list)


class MLErrorSamplesResponse(MLBaseResponse):
    target: MLTarget = "category"
    model: MLModelName = "logistic_regression"
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    filters: dict[str, Any] = Field(default_factory=dict)


class MLArtifactDiagnosticsCompareResponse(BaseModel):
    status: MLStatus = "ready"
    target: MLTarget | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    metric_deltas: list[dict[str, Any]] = Field(default_factory=list)
    class_deltas: list[dict[str, Any]] = Field(default_factory=list)
    confusion_deltas: list[dict[str, Any]] = Field(default_factory=list)
    best_artifact: dict[str, Any] | None = None
    notes: list[str] = Field(default_factory=list)


class ArticleExplanationResponse(MLBaseResponse):
    article_id: str
    target: MLTarget = "category"
    mode: Literal["tree_path", "linear_coefficients", "top_terms"] = "top_terms"
    prediction: str | None = None
    confidence: float | None = None
    actual_label: str | None = None
    model: str | None = None
    model_source: str = "on_demand"
    artifact_id: str | None = None
    explanation: str = ""
    path: list[dict[str, Any]] = Field(default_factory=list)
    contributions: list[dict[str, Any]] = Field(default_factory=list)
    probabilities: list[dict[str, Any]] = Field(default_factory=list)


class MLDiagnosticsReportRecord(BaseModel):
    report_id: str
    job_id: int | None = None
    created_at: str | None = None
    template: str = "portfolio"
    sections: list[str] = Field(default_factory=list)
    section_status: dict[str, str] = Field(default_factory=dict)
    report_title: str = "ML Diagnostics Report"
    prepared_for: str | None = None
    preview_url: str | None = None
    print_url: str | None = None
    pdf_url: str | None = None
    pdf_status: Literal["not_generated", "ready", "fallback_html", "error"] = "not_generated"
    pdf_fallback_reason: str | None = None
    pdf_generated_at: str | None = None
    status: Literal["active", "archived", "trashed"] = "active"
    tags: list[str] = Field(default_factory=list)
    archived_at: str | None = None
    trashed_at: str | None = None
    metadata_updated_at: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    files: list[str] = Field(default_factory=list)
    summary_metrics: dict[str, Any] = Field(default_factory=dict)
    row_counts: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class MLDiagnosticsReportListResponse(BaseModel):
    items: list[MLDiagnosticsReportRecord] = Field(default_factory=list)
    total: int = 0


class MLDiagnosticsReportDetailResponse(MLDiagnosticsReportRecord):
    artifact_comparison: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None


class MLDiagnosticsReportCompareResponse(BaseModel):
    baseline_report_id: str | None = None
    items: list[MLDiagnosticsReportRecord] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    metric_deltas: list[dict[str, Any]] = Field(default_factory=list)
    row_count_deltas: list[dict[str, Any]] = Field(default_factory=list)
    section_matrix: list[dict[str, Any]] = Field(default_factory=list)
    failure_summary: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MLDiagnosticsReportMetadataUpdate(BaseModel):
    status: Literal["active", "archived", "trashed"] | None = None
    tags: list[str] | None = None


class MLDiagnosticsReportBulkRequest(BaseModel):
    action: Literal["archive", "trash", "restore", "add_tags", "remove_tags", "set_tags"]
    ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class MLDiagnosticsReportBulkResponse(BaseModel):
    action: str
    updated: int = 0
    missing: list[str] = Field(default_factory=list)
    items: list[MLDiagnosticsReportRecord] = Field(default_factory=list)


class MLDiagnosticsReportBulkExportRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)
    formats: list[Literal["html", "pdf", "xlsx", "json", "markdown", "manifest"]] = Field(default_factory=lambda: ["html", "pdf", "xlsx", "json", "manifest"])
