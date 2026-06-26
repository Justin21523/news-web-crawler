from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse

from app.schemas.ml import (
    ArticleExplanationResponse,
    ArticlePredictionResponse,
    DecisionPathResponse,
    DecisionTreeResponse,
    MLArtifactCompareResponse,
    MLArtifactDiagnosticsCompareResponse,
    MLArtifactDetail,
    MLArtifactListResponse,
    MLCompareResponse,
    MLDatasetResponse,
    MLDiagnosticsResponse,
    MLDiagnosticsReportBulkRequest,
    MLDiagnosticsReportBulkExportRequest,
    MLDiagnosticsReportBulkResponse,
    MLDiagnosticsReportCompareResponse,
    MLDiagnosticsReportDetailResponse,
    MLDiagnosticsReportListResponse,
    MLDiagnosticsReportMetadataUpdate,
    MLDiagnosticsReportRecord,
    MLErrorSamplesResponse,
    MLModelName,
    MLOverviewResponse,
    MLTarget,
    MLTrainResponse,
)
from app.services.ml import MLService
from app.services.ml_diagnostics_report import MLDiagnosticsReportService

router = APIRouter(tags=["ml"])


def _service() -> MLService:
    return MLService()


def _report_service() -> MLDiagnosticsReportService:
    return MLDiagnosticsReportService()


@router.get("/ml/overview", response_model=MLOverviewResponse)
def overview(limit: int = Query(2000, ge=1, le=2000)):
    return _service().overview(limit)


@router.get("/ml/dataset", response_model=MLDatasetResponse)
def dataset(target: MLTarget = "category", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, limit: int = Query(2000, ge=1, le=2000)):
    return _service().dataset(target, source, category, date_from, date_to, min_class_count, collapse_rare, limit)


@router.get("/ml/train", response_model=MLTrainResponse)
def train(target: MLTarget = "category", model: MLModelName = "logistic_regression", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(5000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(None, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)):
    return _service().train(target, model, source, category, date_from, date_to, test_size, feature_limit, min_class_count, collapse_rare, max_depth, min_samples_split, min_samples_leaf, criterion, limit)


@router.get("/ml/compare", response_model=MLCompareResponse)
def compare(target: MLTarget = "category", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(5000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, limit: int = Query(2000, ge=1, le=2000)):
    return _service().compare(target, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, limit=limit)


@router.get("/ml/diagnostics", response_model=MLDiagnosticsResponse)
def diagnostics(target: MLTarget = "category", model: MLModelName = "logistic_regression", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(5000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(None, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)):
    return _service().diagnostics(target=target, model=model, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, limit=limit)


@router.get("/ml/diagnostics/errors", response_model=MLErrorSamplesResponse)
def diagnostics_errors(target: MLTarget = "category", model: MLModelName = "logistic_regression", artifact_id: str | None = None, actual: str | None = None, predicted: str | None = None, class_label: str | None = None, correct: bool | None = None, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(5000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(None, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return _service().error_samples(target=target, model=model, artifact_id=artifact_id, actual=actual, predicted=predicted, class_label=class_label, correct=correct, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, limit=limit, page=page, page_size=page_size)


@router.get("/ml/diagnostics/reports", response_model=MLDiagnosticsReportListResponse)
def diagnostics_reports(
    limit: int = Query(50, ge=1, le=100),
    q: str | None = None,
    target: MLTarget | None = None,
    model: MLModelName | None = None,
    template: str | None = None,
    pdf_status: str | None = Query(None, pattern="^(not_generated|ready|fallback_html|error)$"),
    status: str | None = Query("active", pattern="^(active|archived|trashed)$"),
    tag: str | None = None,
    include_trashed: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = Query("created_at", pattern="^(created_at|report_title|accuracy|f1_macro|error_samples)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=100),
):
    return _report_service().list_reports(limit, q, target, model, template, pdf_status, status, tag, include_trashed, date_from, date_to, sort_by, sort_order, page, page_size)


@router.post("/ml/diagnostics/reports/bulk", response_model=MLDiagnosticsReportBulkResponse)
def diagnostics_reports_bulk(request: MLDiagnosticsReportBulkRequest):
    try:
        return _report_service().bulk_update(request.action, request.ids, request.tags)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ml/diagnostics/reports/bulk/export")
def diagnostics_reports_bulk_export(request: MLDiagnosticsReportBulkExportRequest) -> FileResponse:
    try:
        path, media_type, filename, headers = _report_service().bulk_export(request.ids, request.formats)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(path, media_type=media_type, filename=filename, headers=headers)


@router.get("/ml/diagnostics/reports/compare", response_model=MLDiagnosticsReportCompareResponse)
def diagnostics_reports_compare(ids: str = Query("")):
    report_ids = [item.strip() for item in ids.split(",") if item.strip()]
    return _report_service().compare_reports(report_ids)


@router.get("/ml/diagnostics/reports/compare/download")
def diagnostics_reports_compare_download(ids: str = Query(""), format: str = Query("html", pattern="^(html|pdf)$")) -> FileResponse:
    report_ids = [item.strip() for item in ids.split(",") if item.strip()]
    try:
        path, media_type, filename, headers = _report_service().compare_download(report_ids, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=media_type, filename=filename, headers=headers)


@router.get("/ml/diagnostics/reports/{report_id}", response_model=MLDiagnosticsReportDetailResponse)
def diagnostics_report(report_id: str):
    detail = _report_service().detail(report_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Diagnostics report not found")
    return detail


@router.patch("/ml/diagnostics/reports/{report_id}/metadata", response_model=MLDiagnosticsReportRecord)
def diagnostics_report_metadata(report_id: str, request: MLDiagnosticsReportMetadataUpdate):
    record = _report_service().update_metadata(report_id, request)
    if not record:
        raise HTTPException(status_code=404, detail="Diagnostics report not found")
    return record


@router.get("/ml/diagnostics/reports/{report_id}/download")
def diagnostics_report_download(report_id: str, format: str = Query("html", pattern="^(html|markdown|xlsx|json|pdf)$")) -> FileResponse:
    try:
        path, media_type, filename, headers = _report_service().download(report_id, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=media_type, filename=filename, headers=headers)


@router.get("/ml/predict/article/{article_id}", response_model=ArticlePredictionResponse)
def predict_article(article_id: str, targets: str = Query("category,source,sentiment"), prefer_artifact: bool = True, limit: int = Query(2000, ge=1, le=2000)):
    parsed = [item.strip() for item in targets.split(",") if item.strip() in {"category", "source", "sentiment"}]
    return _service().predict_article(article_id, parsed or None, prefer_artifact, limit)


@router.get("/ml/predict/article/{article_id}/explanation", response_model=ArticleExplanationResponse)
def article_explanation(article_id: str, target: MLTarget = "category", mode: str = Query("top_terms", pattern="^(tree_path|linear_coefficients|top_terms)$"), artifact_id: str | None = None, limit: int = Query(2000, ge=1, le=2000), feature_limit: int = Query(1000, ge=100, le=30000), max_depth: int | None = Query(4, ge=1, le=30), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True):
    return _service().article_explanation(article_id=article_id, target=target, mode=mode, artifact_id=artifact_id, limit=limit, feature_limit=feature_limit, max_depth=max_depth, min_class_count=min_class_count, collapse_rare=collapse_rare)


@router.get("/ml/decision-tree", response_model=DecisionTreeResponse)
def decision_tree(target: MLTarget = "category", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(1000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(4, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)):
    return _service().train(target, "decision_tree", source, category, date_from, date_to, test_size, feature_limit, min_class_count, collapse_rare, max_depth, min_samples_split, min_samples_leaf, criterion, limit)


@router.get("/ml/decision-tree/image")
def decision_tree_image(format: str = Query("svg", pattern="^(svg|png)$"), target: MLTarget = "category", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(1000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(4, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)) -> Response:
    content, media_type, filename = _service().decision_tree_image(fmt=format, target=target, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, limit=limit)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/ml/decision-tree/path", response_model=DecisionPathResponse)
def decision_path(article_id: str, target: MLTarget = "category", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(1000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(4, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)):
    return _service().decision_path(article_id=article_id, target=target, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, limit=limit)


@router.get("/ml/export")
def export(section: str = Query("metrics", pattern="^(metrics|classification_report|feature_importance|tree_image)$"), format: str = Query("json", pattern="^(json|csv|svg|png)$"), target: MLTarget = "category", model: MLModelName = "logistic_regression", source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = Query(0.3, ge=0.2, le=0.5), feature_limit: int = Query(5000, ge=100, le=30000), min_class_count: int = Query(2, ge=1, le=20), collapse_rare: bool = True, max_depth: int | None = Query(4, ge=1, le=30), min_samples_split: int = Query(2, ge=2, le=100), min_samples_leaf: int = Query(1, ge=1, le=100), criterion: str = Query("gini", pattern="^(gini|entropy|log_loss)$"), limit: int = Query(2000, ge=1, le=2000)) -> Response:
    content, media_type, filename = _service().export(section, format, target=target, model="decision_tree" if section == "tree_image" else model, source=source, category=category, date_from=date_from, date_to=date_to, test_size=test_size, feature_limit=feature_limit, min_class_count=min_class_count, collapse_rare=collapse_rare, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, limit=limit)
    return Response(content=content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/ml/artifacts", response_model=MLArtifactListResponse)
def artifacts(target: MLTarget | None = None, model: MLModelName | None = None, limit: int = Query(50, ge=1, le=100)):
    return _service().artifacts(target=target, model=model, limit=limit)


@router.get("/ml/artifacts/compare", response_model=MLArtifactCompareResponse)
def compare_artifacts(ids: str = Query("")):
    artifact_ids = [item.strip() for item in ids.split(",") if item.strip()]
    return _service().compare_artifacts(artifact_ids)


@router.get("/ml/artifacts/diagnostics/compare", response_model=MLArtifactDiagnosticsCompareResponse)
def compare_artifact_diagnostics(target: MLTarget, ids: str = Query("")):
    artifact_ids = [item.strip() for item in ids.split(",") if item.strip()]
    return _service().compare_artifact_diagnostics(target, artifact_ids)


@router.get("/ml/artifacts/{artifact_id}", response_model=MLArtifactDetail)
def artifact(artifact_id: str):
    detail = _service().artifact(artifact_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return detail


@router.get("/ml/artifacts/{artifact_id}/download")
def artifact_download(artifact_id: str, file: str = Query("manifest")) -> FileResponse:
    try:
        path, media_type, filename = _service().artifact_download(artifact_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=media_type, filename=filename)
