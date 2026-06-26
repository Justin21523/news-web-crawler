from __future__ import annotations

import csv
import json
import time
import uuid
from collections import Counter
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

import numpy as np

from analysis.classification import SentimentAnalyzer
from app.core.config import Settings, get_settings
from app.schemas.ml import (
    ArticleExplanationResponse,
    ArticlePredictionResponse,
    DecisionPathResponse,
    DecisionTreeResponse,
    MLArtifactCompareResponse,
    MLArtifactDiagnosticsCompareResponse,
    MLArtifactDetail,
    MLArtifactListResponse,
    MLArtifactRecord,
    MLCompareResponse,
    MLDatasetResponse,
    MLDiagnosticsResponse,
    MLErrorSamplesResponse,
    MLModelName,
    MLOverviewResponse,
    MLTarget,
    MLTrainResponse,
)
from app.services.database import Database


class MLService:
    artifact_files = {
        "model": ("model.joblib", "application/octet-stream"),
        "vectorizer": ("vectorizer.joblib", "application/octet-stream"),
        "manifest": ("manifest.json", "application/json; charset=utf-8"),
        "metrics": ("metrics.json", "application/json; charset=utf-8"),
        "classification_report": ("classification_report.json", "application/json; charset=utf-8"),
        "confusion_matrix": ("confusion_matrix.csv", "text/csv; charset=utf-8"),
        "feature_importance": ("feature_importance.csv", "text/csv; charset=utf-8"),
        "tree_svg": ("decision_tree.svg", "image/svg+xml; charset=utf-8"),
        "tree_png": ("decision_tree.png", "image/png"),
    }

    def __init__(self, db: Database | None = None, settings: Settings | None = None, models_dir: str | Path | None = None):
        self.db = db or Database()
        self.settings = settings or get_settings()
        self.models_dir = Path(models_dir or self.settings.resolved_models_dir)

    def overview(self, limit: int = 2000) -> MLOverviewResponse:
        rows = self._rows(limit=limit)
        targets: dict[str, dict[str, Any]] = {}
        for target in ("category", "source", "sentiment"):
            dataset = self.dataset(target=target, limit=limit)
            targets[target] = {
                "status": dataset.status,
                "label_distribution": dataset.label_distribution,
                "prepared_distribution": dataset.prepared_distribution,
                "notes": dataset.notes,
            }
        notes = [] if rows else ["Run demo or ingestion jobs before training ML baselines."]
        return MLOverviewResponse(
            status="ready" if rows else "insufficient_data",
            total_documents=len(rows),
            targets=targets,
            recommended_next_steps=[
                "Use source classification first because demo data has balanced source labels.",
                "Treat sentiment as weak-label baseline until manually labeled sentiment data exists.",
                "Use Decision Tree for interpretability, not as the best accuracy baseline.",
            ],
            notes=notes,
        )

    def dataset(
        self,
        target: MLTarget,
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        min_class_count: int = 2,
        collapse_rare: bool = True,
        limit: int = 2000,
    ) -> MLDatasetResponse:
        rows = self._rows(source, category, date_from, date_to, limit)
        prepared = self._prepare_dataset(rows, target, min_class_count, collapse_rare)
        status = "ready" if prepared["usable"] else "insufficient_data"
        return MLDatasetResponse(
            status=status,
            target=target,
            total_documents=len(rows),
            label_distribution=prepared["raw_distribution"],
            prepared_distribution=prepared["prepared_distribution"],
            sample_rows=[
                {
                    "article_id": row["article_id"],
                    "title": row["title"],
                    "source": row["source"],
                    "category": row["category_label"],
                    "label": prepared["label_by_id"].get(row["article_id"]),
                    "text_length": len(row["text"]),
                }
                for row in rows[:20]
            ],
            preprocessing=prepared["preprocessing"],
            notes=prepared["notes"],
        )

    def train(
        self,
        target: MLTarget,
        model: MLModelName = "logistic_regression",
        source: str | None = None,
        category: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        test_size: float = 0.3,
        feature_limit: int = 5000,
        min_class_count: int = 2,
        collapse_rare: bool = True,
        max_depth: int | None = None,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        criterion: str = "gini",
        limit: int = 2000,
    ) -> MLTrainResponse:
        fitted = self._fit(
            target=target,
            model=model,
            source=source,
            category=category,
            date_from=date_from,
            date_to=date_to,
            test_size=test_size,
            feature_limit=feature_limit,
            min_class_count=min_class_count,
            collapse_rare=collapse_rare,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            criterion=criterion,
            limit=limit,
        )
        if fitted["status"] != "ready":
            return MLTrainResponse(status=fitted["status"], target=target, model=model, total_documents=fitted["total_documents"], notes=fitted["notes"])
        response = self._train_response(fitted)
        if model == "decision_tree":
            response = DecisionTreeResponse(**response.model_dump(), tree=self._tree_summary(fitted))
        return response

    def compare(self, target: MLTarget, **kwargs: Any) -> MLCompareResponse:
        models: list[MLModelName] = ["logistic_regression", "linear_svm", "naive_bayes", "decision_tree", "random_forest"]
        results = [self.train(target=target, model=model, **kwargs) for model in models]
        ready = [result for result in results if result.status == "ready"]
        return MLCompareResponse(
            status="ready" if ready else "insufficient_data",
            target=target,
            total_documents=max((result.total_documents for result in results), default=0),
            results=results,
            notes=[] if ready else ["No baseline model could be trained with the current labels."],
        )

    def diagnostics(
        self,
        target: MLTarget,
        model: MLModelName = "logistic_regression",
        **kwargs: Any,
    ) -> MLDiagnosticsResponse:
        fitted = self._fit(target=target, model=model, **kwargs)
        if fitted["status"] != "ready":
            return MLDiagnosticsResponse(status=fitted["status"], target=target, model=model, total_documents=fitted["total_documents"], notes=fitted["notes"])

        class_metrics = fitted.get("class_metrics", [])
        low_classes = [
            {**item, "reason": self._class_issue_reason(item)}
            for item in class_metrics
            if float(item.get("f1", 0)) < 0.6 or float(item.get("recall", 0)) < 0.6 or float(item.get("precision", 0)) < 0.6
        ]
        error_samples = [item for item in fitted.get("sample_predictions", []) if not item.get("correct")][:30]
        factors = self._failure_factors(fitted, target, low_classes)
        return MLDiagnosticsResponse(
            status="ready",
            target=target,
            model=model,
            total_documents=fitted["total_documents"],
            metrics=fitted["metrics"],
            class_metrics=class_metrics,
            low_performing_classes=low_classes,
            confusion_matrix=fitted["confusion_matrix"],
            labels=fitted["labels"],
            confusion_pairs=fitted["confusion_pairs"],
            error_samples=error_samples,
            sample_predictions=fitted.get("sample_predictions", []),
            failure_factors=factors,
            recommendations=self._recommendations(factors, target, model),
            feature_diagnostics={
                "vectorizer": fitted["vectorizer"],
                "top_features": fitted["feature_importance"][:20],
                "vocabulary_size": fitted["vectorizer"].get("vocabulary_size", 0),
                "feature_limit": fitted["vectorizer"].get("max_features", 0),
                "notes": self._feature_notes(fitted),
            },
            train_test_split={"train_documents": fitted["train_documents"], "test_documents": fitted["test_documents"], "test_size": fitted["test_size"], "stratified": fitted["stratified"]},
            notes=fitted["notes"],
        )

    def predict_article(self, article_id: str, targets: list[MLTarget] | None = None, prefer_artifact: bool = True, limit: int = 2000) -> ArticlePredictionResponse:
        article = self.db.fetch_one(
            """
            SELECT article_id, title, source, category, category_name, content_clean
            FROM articles
            WHERE article_id = ?
            """,
            (article_id,),
        )
        if not article:
            return ArticlePredictionResponse(status="insufficient_data", article_id=article_id, notes=["Article not found."])
        text = f"{article['title'] or ''}\n{article['content_clean'] or ''}".strip()
        targets = targets or ["category", "source", "sentiment"]
        predictions = []
        notes = []
        for target in targets:
            prediction = self._predict_from_artifact(article_id, text, target) if prefer_artifact else None
            if not prediction:
                prediction = self._predict_on_demand(article_id, text, target, limit)
            if prediction:
                predictions.append(prediction)
            else:
                notes.append(f"No ready model could produce {target} prediction.")
        return ArticlePredictionResponse(
            status="ready" if predictions else "insufficient_data",
            total_documents=len(predictions),
            article_id=article_id,
            predictions=predictions,
            notes=notes,
        )

    def decision_tree_image(self, fmt: str = "svg", **kwargs: Any) -> tuple[bytes, str, str]:
        kwargs.pop("model", None)
        fitted = self._fit(model="decision_tree", **kwargs)
        if fitted["status"] != "ready":
            payload = json.dumps({"status": fitted["status"], "notes": fitted["notes"]}, ensure_ascii=False, indent=2).encode("utf-8")
            return payload, "application/json; charset=utf-8", "decision-tree-error.json"
        return self._tree_image_from_fitted(fitted, fmt, kwargs.get("max_depth"))

    def _tree_image_from_fitted(self, fitted: dict[str, Any], fmt: str = "svg", max_depth: int | None = None) -> tuple[bytes, str, str]:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from sklearn.tree import plot_tree
        except ImportError:
            payload = json.dumps({"status": "dependency_missing", "notes": ["matplotlib is required for Decision Tree image export."]}, ensure_ascii=False, indent=2).encode("utf-8")
            return payload, "application/json; charset=utf-8", "decision-tree-error.json"

        fig_width = max(12, min(28, int(fitted["model_object"].get_depth() * 3 + 8)))
        fig, ax = plt.subplots(figsize=(fig_width, 8), dpi=140)
        plot_tree(
            fitted["model_object"],
            feature_names=fitted["feature_names"],
            class_names=fitted["labels"],
            filled=True,
            rounded=True,
            max_depth=max_depth,
            fontsize=7,
            ax=ax,
        )
        out = BytesIO()
        if fmt == "png":
            fig.savefig(out, format="png", bbox_inches="tight")
            media_type, filename = "image/png", "decision-tree.png"
        else:
            fig.savefig(out, format="svg", bbox_inches="tight")
            media_type, filename = "image/svg+xml; charset=utf-8", "decision-tree.svg"
        plt.close(fig)
        return out.getvalue(), media_type, filename

    def train_and_persist(
        self,
        target: MLTarget,
        model: MLModelName = "logistic_regression",
        job_id: int | None = None,
        **kwargs: Any,
    ) -> MLArtifactRecord:
        artifact_id = f"{target}-{model}-{uuid.uuid4().hex[:10]}"
        artifact_dir = self.models_dir / "ml" / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        params = {"target": target, "model": model, **kwargs}
        fitted = self._fit(target=target, model=model, **kwargs)
        if fitted["status"] != "ready":
            manifest = {
                "artifact_id": artifact_id,
                "status": fitted["status"],
                "params": params,
                "notes": fitted.get("notes", []),
                "error": "; ".join(fitted.get("notes", [])),
            }
            self._write_json(artifact_dir / "manifest.json", manifest)
            self._insert_artifact(
                artifact_id=artifact_id,
                job_id=job_id,
                target=target,
                model=model,
                status="failed",
                params=params,
                metrics={},
                artifact_dir=artifact_dir,
                error=manifest["error"],
            )
            raise RuntimeError(manifest["error"] or "ML training did not produce a ready model.")

        try:
            import joblib
        except ImportError as exc:
            self._insert_artifact(
                artifact_id=artifact_id,
                job_id=job_id,
                target=target,
                model=model,
                status="failed",
                params=params,
                metrics={},
                artifact_dir=artifact_dir,
                error="joblib is required for model artifact persistence.",
            )
            raise RuntimeError("joblib is required for model artifact persistence.") from exc

        response = self._train_response(fitted)
        manifest = {
            "artifact_id": artifact_id,
            "job_id": job_id,
            "status": "ready",
            "target": target,
            "model": model,
            "params": params,
            "metrics": response.metrics,
            "train_test_split": response.train_test_split,
            "vectorizer": response.vectorizer,
            "labels": response.labels,
            "timings": response.timings,
            "notes": response.notes,
            "files": [],
        }
        if model == "decision_tree":
            manifest["tree"] = self._tree_summary(fitted)
        diagnostics_payload = self._diagnostics_payload_from_fitted(fitted, target, model)

        joblib.dump(fitted["model_object"], artifact_dir / "model.joblib")
        joblib.dump(fitted["vectorizer_object"], artifact_dir / "vectorizer.joblib")
        self._write_json(artifact_dir / "metrics.json", response.metrics)
        self._write_json(artifact_dir / "classification_report.json", response.classification_report)
        self._write_json(artifact_dir / "diagnostics.json", diagnostics_payload.model_dump())
        self._write_json(artifact_dir / "sample_predictions.json", response.sample_predictions)
        self._write_json(artifact_dir / "class_metrics.json", response.class_metrics)
        self._write_csv(artifact_dir / "confusion_matrix.csv", self._matrix_rows(response.labels, response.confusion_matrix))
        self._write_csv(artifact_dir / "feature_importance.csv", response.feature_importance)

        if model == "decision_tree":
            svg, _, _ = self._tree_image_from_fitted(fitted, "svg", kwargs.get("max_depth"))
            png, _, _ = self._tree_image_from_fitted(fitted, "png", kwargs.get("max_depth"))
            (artifact_dir / "decision_tree.svg").write_bytes(svg)
            (artifact_dir / "decision_tree.png").write_bytes(png)

        manifest["files"] = sorted(path.name for path in artifact_dir.iterdir() if path.is_file())
        manifest["diagnostics_files"] = [name for name in ("diagnostics.json", "sample_predictions.json", "class_metrics.json") if name in manifest["files"]]
        manifest["diagnostics_version"] = "1"
        manifest["dataset_signature"] = {
            "total_documents": fitted["total_documents"],
            "labels": fitted["labels"],
            "prepared_distribution": fitted["prepared_distribution"],
            "params": params,
        }
        self._write_json(artifact_dir / "manifest.json", manifest)
        record = self._insert_artifact(
            artifact_id=artifact_id,
            job_id=job_id,
            target=target,
            model=model,
            status="ready",
            params=params,
            metrics=response.metrics,
            artifact_dir=artifact_dir,
        )
        return record

    def artifacts(self, target: str | None = None, model: str | None = None, limit: int = 50) -> MLArtifactListResponse:
        clauses = ["1=1"]
        params: list[Any] = []
        if target:
            clauses.append("target = ?")
            params.append(target)
        if model:
            clauses.append("model = ?")
            params.append(model)
        params.append(min(max(limit, 1), 100))
        rows = self.db.fetch_all(
            f"""
            SELECT * FROM model_artifacts
            WHERE {' AND '.join(clauses)}
            ORDER BY datetime(created_at) DESC, artifact_id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        records = [self._artifact_record(dict(row)) for row in rows]
        return MLArtifactListResponse(items=records, total=len(records))

    def artifact(self, artifact_id: str) -> MLArtifactDetail | None:
        row = self.db.fetch_one("SELECT * FROM model_artifacts WHERE artifact_id = ?", (artifact_id,))
        if not row:
            return None
        record = self._artifact_record(dict(row))
        manifest_path = Path(record.artifact_dir) / "manifest.json"
        manifest = self._read_json(manifest_path, {})
        return MLArtifactDetail(**record.model_dump(), manifest=manifest)

    def compare_artifacts(self, ids: list[str]) -> MLArtifactCompareResponse:
        items = []
        notes = []
        for artifact_id in ids:
            detail = self.artifact(artifact_id)
            if not detail:
                notes.append(f"Artifact not found: {artifact_id}")
                continue
            metrics = detail.metrics
            items.append(
                {
                    "artifact_id": detail.artifact_id,
                    "job_id": detail.job_id,
                    "target": detail.target,
                    "model": detail.model,
                    "status": detail.status,
                    "accuracy": metrics.get("accuracy"),
                    "precision_macro": metrics.get("precision_macro"),
                    "recall_macro": metrics.get("recall_macro"),
                    "f1_macro": metrics.get("f1_macro"),
                    "created_at": detail.created_at,
                }
            )
        return MLArtifactCompareResponse(items=items, notes=notes)

    def compare_artifact_diagnostics(self, target: MLTarget, ids: list[str]) -> MLArtifactDiagnosticsCompareResponse:
        details = [self.artifact(artifact_id) for artifact_id in ids if artifact_id]
        found = [detail for detail in details if detail is not None]
        notes = [f"Artifact not found: {ids[idx]}" for idx, detail in enumerate(details) if detail is None]
        wrong_target = [detail.artifact_id for detail in found if detail.target != target]
        if wrong_target:
            return MLArtifactDiagnosticsCompareResponse(status="error", target=target, notes=[f"Artifacts must share target {target}: {', '.join(wrong_target)}"])
        items = []
        for detail in found:
            diagnostics = self._artifact_diagnostics(detail.artifact_id)
            item = {
                "artifact_id": detail.artifact_id,
                "target": detail.target,
                "model": detail.model,
                "created_at": detail.created_at,
                "status": detail.status,
                "metrics": detail.metrics,
                "class_metrics": diagnostics.get("class_metrics", []),
                "confusion_pairs": diagnostics.get("confusion_pairs", []),
                "failure_factors": diagnostics.get("failure_factors", []),
                "recommendations": diagnostics.get("recommendations", []),
                "notes": diagnostics.get("notes", []),
            }
            if not diagnostics:
                item["notes"] = ["Diagnostics file is missing. Retrain this artifact to persist full diagnostics."]
            items.append(item)
        best = max(items, key=lambda item: float(item.get("metrics", {}).get("f1_macro") or item.get("metrics", {}).get("accuracy") or -1), default=None)
        return MLArtifactDiagnosticsCompareResponse(
            status="ready" if items else "insufficient_data",
            target=target,
            items=items,
            metric_deltas=self._artifact_metric_deltas(items),
            class_deltas=self._artifact_class_deltas(items),
            confusion_deltas=self._artifact_confusion_deltas(items),
            best_artifact=best,
            notes=notes,
        )

    def error_samples(
        self,
        target: MLTarget,
        model: MLModelName = "logistic_regression",
        artifact_id: str | None = None,
        actual: str | None = None,
        predicted: str | None = None,
        class_label: str | None = None,
        correct: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        **kwargs: Any,
    ) -> MLErrorSamplesResponse:
        diagnostics: dict[str, Any] = {}
        if artifact_id:
            detail = self.artifact(artifact_id)
            if not detail:
                return MLErrorSamplesResponse(status="insufficient_data", target=target, model=model, notes=["Artifact not found."])
            if detail.target != target:
                return MLErrorSamplesResponse(status="error", target=target, model=detail.model, notes=[f"Artifact target is {detail.target}, not {target}."])
            diagnostics = self._artifact_diagnostics(artifact_id)
            model = detail.model
        if not diagnostics:
            fitted = self._fit(target=target, model=model, **kwargs)
            if fitted["status"] != "ready":
                return MLErrorSamplesResponse(status=fitted["status"], target=target, model=model, total_documents=fitted["total_documents"], notes=fitted["notes"])
            diagnostics = self._diagnostics_payload_from_fitted(fitted, target, model).model_dump()
        rows = list(diagnostics.get("sample_predictions") or diagnostics.get("error_samples") or [])
        if correct is None:
            rows = [row for row in rows if not bool(row.get("correct"))]
        else:
            rows = [row for row in rows if bool(row.get("correct")) is correct]
        if actual:
            rows = [row for row in rows if str(row.get("actual")) == actual]
        if predicted:
            rows = [row for row in rows if str(row.get("predicted")) == predicted]
        if class_label:
            rows = [row for row in rows if str(row.get("actual")) == class_label or str(row.get("predicted")) == class_label]
        total = len(rows)
        page = max(page, 1)
        page_size = min(max(page_size, 1), 10000)
        start = (page - 1) * page_size
        return MLErrorSamplesResponse(
            status="ready",
            target=target,
            model=model,
            total_documents=int(diagnostics.get("total_documents") or total),
            items=rows[start:start + page_size],
            total=total,
            page=page,
            page_size=page_size,
            filters={"actual": actual, "predicted": predicted, "class_label": class_label, "correct": correct, "artifact_id": artifact_id},
            notes=diagnostics.get("notes", []),
        )

    def article_explanation(
        self,
        article_id: str,
        target: MLTarget,
        mode: str = "top_terms",
        artifact_id: str | None = None,
        limit: int = 2000,
        **kwargs: Any,
    ) -> ArticleExplanationResponse:
        article = self.db.fetch_one(
            """
            SELECT article_id, title, source, category, category_name, content_clean
            FROM articles
            WHERE article_id = ?
            """,
            (article_id,),
        )
        if not article:
            return ArticleExplanationResponse(status="insufficient_data", article_id=article_id, target=target, mode=self._explanation_mode(mode), notes=["Article not found."])
        text = f"{article['title'] or ''}\n{article['content_clean'] or ''}".strip()
        mode = self._explanation_mode(mode)
        if mode == "tree_path":
            return self._tree_explanation(article_id, target, text, artifact_id, limit, **kwargs)
        model_name: MLModelName = "logistic_regression" if mode == "linear_coefficients" else "logistic_regression"
        loaded = self._load_artifact_model(artifact_id, target) if artifact_id else self._latest_artifact_model(target, prefer_linear=(mode == "linear_coefficients"))
        model_source = "artifact"
        if loaded is None:
            fitted = self._fit(target=target, model=model_name, limit=limit, **kwargs)
            if fitted["status"] != "ready":
                return ArticleExplanationResponse(status=fitted["status"], total_documents=fitted["total_documents"], article_id=article_id, target=target, mode=mode, notes=fitted["notes"])
            model, vectorizer, labels, model_name, artifact = fitted["model_object"], fitted["vectorizer_object"], fitted["labels"], fitted["model"], None
            model_source = "on_demand"
        else:
            artifact, model, vectorizer, labels = loaded
            model_name = artifact.model
        payload = self._prediction_payload(article_id, text, target, model_name, model, vectorizer, labels, model_source, artifact.artifact_id if loaded else None)
        contributions = payload["top_terms"]
        if mode == "linear_coefficients" and not hasattr(model, "coef_"):
            mode = "top_terms"
            payload["explanation"] = f"{model_name} does not expose linear coefficients, so this explanation falls back to top text terms."
        return ArticleExplanationResponse(
            status="ready",
            total_documents=1,
            article_id=article_id,
            target=target,
            mode=mode,
            prediction=payload["prediction"],
            confidence=payload["confidence"],
            actual_label=self._actual_label_for_article(article_id, target),
            model=model_name,
            model_source=model_source,
            artifact_id=payload["artifact_id"],
            explanation=payload["explanation"],
            contributions=contributions,
            probabilities=payload["probabilities"],
        )

    def artifact_download(self, artifact_id: str, file_key: str) -> tuple[Path, str, str]:
        if file_key not in self.artifact_files:
            raise ValueError("Unsupported artifact file")
        detail = self.artifact(artifact_id)
        if not detail:
            raise FileNotFoundError("Artifact not found")
        filename, media_type = self.artifact_files[file_key]
        path = Path(detail.artifact_dir) / filename
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("Artifact file not found")
        return path, media_type, filename

    def decision_path(self, article_id: str, **kwargs: Any) -> DecisionPathResponse:
        fitted = self._fit(model="decision_tree", **kwargs)
        target = kwargs.get("target", "category")
        if fitted["status"] != "ready":
            return DecisionPathResponse(status=fitted["status"], total_documents=fitted["total_documents"], article_id=article_id, target=target, notes=fitted["notes"])
        row = next((item for item in fitted["rows"] if item["article_id"] == article_id), None)
        if not row:
            return DecisionPathResponse(status="insufficient_data", total_documents=fitted["total_documents"], article_id=article_id, target=target, notes=["Article is not available in the current ML corpus."])

        vector = fitted["vectorizer_object"].transform([row["text"]])
        tree = fitted["model_object"].tree_
        node_indicator = fitted["model_object"].decision_path(vector)
        leaf_id = fitted["model_object"].apply(vector)[0]
        node_ids = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
        steps = []
        for node_id in node_ids:
            if node_id == leaf_id or tree.feature[node_id] < 0:
                steps.append({"node_id": int(node_id), "type": "leaf", "samples": int(tree.n_node_samples[node_id])})
                continue
            feature_idx = int(tree.feature[node_id])
            feature_name = fitted["feature_names"][feature_idx]
            threshold = float(tree.threshold[node_id])
            value = float(vector[0, feature_idx])
            direction = "left" if value <= threshold else "right"
            steps.append({
                "node_id": int(node_id),
                "type": "split",
                "feature": feature_name,
                "threshold": round(threshold, 6),
                "value": round(value, 6),
                "direction": direction,
                "condition": f"{feature_name} <= {threshold:.4f}" if direction == "left" else f"{feature_name} > {threshold:.4f}",
                "samples": int(tree.n_node_samples[node_id]),
            })
        probs = fitted["model_object"].predict_proba(vector)[0]
        pred_idx = int(np.argmax(probs))
        prediction = fitted["labels"][pred_idx]
        actual = fitted["label_by_id"].get(article_id)
        explanation = f"Article {article_id} is classified as {prediction}. The tree used {sum(1 for step in steps if step['type'] == 'split')} split conditions before reaching the leaf node."
        return DecisionPathResponse(
            status="ready",
            total_documents=fitted["total_documents"],
            article_id=article_id,
            target=target,
            prediction=prediction,
            actual_label=actual,
            confidence=round(float(probs[pred_idx]), 4),
            path=steps,
            explanation=explanation,
            notes=fitted["notes"],
        )

    def export(self, section: str, fmt: str, **kwargs: Any) -> tuple[str | bytes, str, str]:
        if section == "tree_image":
            return self.decision_tree_image(fmt="png" if fmt == "png" else "svg", **kwargs)
        result = self.train(**kwargs)
        if section == "feature_importance":
            payload: Any = result.feature_importance
        elif section == "classification_report":
            payload = result.classification_report
        else:
            payload = result.model_dump()
        if fmt == "csv":
            rows = payload if isinstance(payload, list) else self._flatten(payload)
            out = StringIO()
            if rows:
                writer = csv.DictWriter(out, fieldnames=sorted({key for row in rows for key in row}))
                writer.writeheader()
                writer.writerows(rows)
            return out.getvalue(), "text/csv; charset=utf-8", f"ml-{section}.csv"
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json; charset=utf-8", f"ml-{section}.json"

    def _fit(self, target: MLTarget, model: MLModelName, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, test_size: float = 0.3, feature_limit: int = 5000, min_class_count: int = 2, collapse_rare: bool = True, max_depth: int | None = None, min_samples_split: int = 2, min_samples_leaf: int = 1, criterion: str = "gini", limit: int = 2000) -> dict[str, Any]:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
            from sklearn.model_selection import train_test_split
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.tree import DecisionTreeClassifier
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.svm import LinearSVC
        except ImportError:
            return {"status": "dependency_missing", "total_documents": 0, "notes": ["scikit-learn is required for ML model analysis."]}

        rows = self._rows(source, category, date_from, date_to, limit)
        prepared = self._prepare_dataset(rows, target, min_class_count, collapse_rare)
        if not prepared["usable"]:
            return {"status": "insufficient_data", "total_documents": len(rows), "notes": prepared["notes"]}
        docs = prepared["texts"]
        labels = prepared["labels"]
        label_names = sorted(set(labels))
        indices = list(range(len(docs)))
        test_size = min(max(test_size, 0.2), 0.5)
        feature_limit = min(max(feature_limit, 100), 30000)
        vectorizer = TfidfVectorizer(max_features=feature_limit, min_df=1, max_df=1.0, sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")
        stratify = labels if min(Counter(labels).values()) >= 2 and int(round(len(labels) * test_size)) >= len(label_names) else None
        try:
            train_idx, test_idx = train_test_split(indices, test_size=test_size, random_state=42, stratify=stratify)
        except ValueError:
            train_idx, test_idx = train_test_split(indices, test_size=test_size, random_state=42)
        X_train_text = [docs[i] for i in train_idx]
        X_test_text = [docs[i] for i in test_idx]
        y_train = [labels[i] for i in train_idx]
        y_test = [labels[i] for i in test_idx]
        start = time.perf_counter()
        X_train = vectorizer.fit_transform(X_train_text)
        X_test = vectorizer.transform(X_test_text)
        if model == "linear_svm":
            classifier = LinearSVC(random_state=42)
        elif model == "naive_bayes":
            classifier = MultinomialNB()
        elif model == "decision_tree":
            classifier = DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, criterion=criterion, random_state=42)
        elif model == "random_forest":
            classifier = RandomForestClassifier(n_estimators=80, max_depth=max_depth, min_samples_split=min_samples_split, min_samples_leaf=min_samples_leaf, random_state=42)
        else:
            classifier = LogisticRegression(max_iter=1000, random_state=42)
        classifier.fit(X_train, y_train)
        train_seconds = time.perf_counter() - start
        infer_start = time.perf_counter()
        y_pred = classifier.predict(X_test)
        inference_seconds = time.perf_counter() - infer_start
        report = classification_report(y_test, y_pred, labels=label_names, output_dict=True, zero_division=0)
        matrix = confusion_matrix(y_test, y_pred, labels=label_names)
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4),
            "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4),
            "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        }
        return {
            "status": "ready",
            "target": target,
            "model": model,
            "rows": prepared["rows"],
            "total_documents": len(rows),
            "train_documents": len(y_train),
            "test_documents": len(y_test),
            "labels": label_names,
            "raw_distribution": prepared["raw_distribution"],
            "prepared_distribution": prepared["prepared_distribution"],
            "metrics": metrics,
            "classification_report": self._round_nested(report),
            "confusion_matrix": matrix.astype(int).tolist(),
            "vectorizer": {"type": "TfidfVectorizer", "max_features": feature_limit, "vocabulary_size": len(vectorizer.vocabulary_), "text_fields": ["title", "content_clean"]},
            "model_object": classifier,
            "vectorizer_object": vectorizer,
            "feature_names": list(vectorizer.get_feature_names_out()),
            "feature_importance": self._feature_importance(classifier, list(vectorizer.get_feature_names_out()), label_names),
            "class_metrics": self._class_metrics(report, label_names),
            "sample_predictions": self._sample_predictions(prepared["rows"], test_idx, y_test, list(y_pred), classifier, X_test),
            "confusion_pairs": self._confusion_pairs(y_test, list(y_pred)),
            "timings": {"training_seconds": round(train_seconds, 4), "inference_seconds": round(inference_seconds, 4)},
            "notes": prepared["notes"],
            "label_by_id": prepared["label_by_id"],
            "test_size": test_size,
            "stratified": stratify is not None,
        }

    def _train_response(self, fitted: dict[str, Any]) -> MLTrainResponse:
        return MLTrainResponse(
            status="ready",
            target=fitted["target"],
            model=fitted["model"],
            total_documents=fitted["total_documents"],
            metrics=fitted["metrics"],
            train_test_split={"train_documents": fitted["train_documents"], "test_documents": fitted["test_documents"], "test_size": fitted["test_size"], "stratified": fitted["stratified"]},
            vectorizer=fitted["vectorizer"],
            classification_report=fitted["classification_report"],
            confusion_matrix=fitted["confusion_matrix"],
            labels=fitted["labels"],
            feature_importance=fitted["feature_importance"],
            timings=fitted["timings"],
            class_metrics=fitted.get("class_metrics", []),
            sample_predictions=fitted.get("sample_predictions", []),
            confusion_pairs=fitted.get("confusion_pairs", []),
            notes=fitted["notes"],
        )

    def _prepare_dataset(self, rows: list[dict[str, Any]], target: MLTarget, min_class_count: int, collapse_rare: bool) -> dict[str, Any]:
        min_class_count = max(min_class_count, 1)
        items = []
        for row in rows:
            label = self._label(row, target)
            if label and row["text"].strip():
                items.append({**row, "label": label})
        raw_counts = Counter(item["label"] for item in items)
        notes = []
        if target == "sentiment":
            notes.append("Sentiment labels are weak labels generated by the built-in lexicon baseline.")
        if collapse_rare:
            rare = {label for label, count in raw_counts.items() if count < min_class_count}
            if rare and target == "category":
                notes.append(f"Collapsed rare category labels into Other because they had fewer than {min_class_count} samples.")
                for item in items:
                    if item["label"] in rare:
                        item["label"] = "Other"
        prepared_counts = Counter(item["label"] for item in items)
        usable = len(prepared_counts) >= 2 and min(prepared_counts.values(), default=0) >= min_class_count and len(items) >= 4
        if not usable:
            notes.append("At least 2 labels with enough samples are required for train/test evaluation.")
        return {
            "usable": usable,
            "rows": items,
            "texts": [item["text"] for item in items],
            "labels": [item["label"] for item in items],
            "label_by_id": {item["article_id"]: item["label"] for item in items},
            "raw_distribution": dict(raw_counts),
            "prepared_distribution": dict(prepared_counts),
            "preprocessing": {"text_fields": ["title", "content_clean"], "min_class_count": min_class_count, "collapse_rare": collapse_rare, "target": target},
            "notes": notes,
        }

    def _rows(self, source: str | None = None, category: str | None = None, date_from: str | None = None, date_to: str | None = None, limit: int = 2000) -> list[dict[str, Any]]:
        clauses = ["1=1"]
        params: list[Any] = []
        if source:
            clauses.append("a.source = ?")
            params.append(source)
        if category:
            clauses.append("(a.category = ? OR a.category_name = ?)")
            params.extend([category, category])
        if date_from:
            clauses.append("a.publish_date >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("a.publish_date <= ?")
            params.append(date_to)
        params.append(min(max(limit, 1), 2000))
        rows = self.db.fetch_all(
            f"""
            SELECT a.article_id, a.title, a.source, a.category, a.category_name,
                   COALESCE(NULLIF(a.category_name, ''), NULLIF(a.category, ''), 'unknown') AS category_label,
                   a.publish_date, a.content_clean
            FROM articles a
            WHERE {' AND '.join(clauses)}
            ORDER BY COALESCE(a.publish_date, a.crawled_at) DESC, a.article_id DESC
            LIMIT ?
            """,
            tuple(params),
        )
        out = []
        for row in rows:
            data = dict(row)
            text = f"{data.get('title') or ''}\n{data.get('content_clean') or ''}".strip()
            data["text"] = text
            out.append(data)
        return out

    def _label(self, row: dict[str, Any], target: MLTarget) -> str:
        if target == "source":
            return str(row.get("source") or "").strip()
        if target == "sentiment":
            result = SentimentAnalyzer().analyze([row["text"]])[0]
            return result.label
        return str(row.get("category_label") or "").strip()

    def _predict_from_artifact(self, article_id: str, text: str, target: MLTarget) -> dict[str, Any] | None:
        row = self.db.fetch_one(
            """
            SELECT * FROM model_artifacts
            WHERE target = ? AND status = 'ready'
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (target,),
        )
        if not row:
            return None
        record = self._artifact_record(dict(row))
        artifact_dir = Path(record.artifact_dir)
        try:
            import joblib

            model = joblib.load(artifact_dir / "model.joblib")
            vectorizer = joblib.load(artifact_dir / "vectorizer.joblib")
        except Exception:
            return None
        manifest = self._read_json(artifact_dir / "manifest.json", {})
        return self._prediction_payload(article_id, text, target, record.model, model, vectorizer, manifest.get("labels", []), "artifact", record.artifact_id)

    def _predict_on_demand(self, article_id: str, text: str, target: MLTarget, limit: int) -> dict[str, Any] | None:
        fitted = self._fit(target=target, model="logistic_regression", limit=limit)
        if fitted["status"] != "ready":
            return None
        return self._prediction_payload(article_id, text, target, fitted["model"], fitted["model_object"], fitted["vectorizer_object"], fitted["labels"], "on_demand", None)

    def _prediction_payload(
        self,
        article_id: str,
        text: str,
        target: str,
        model_name: str,
        model: Any,
        vectorizer: Any,
        labels: list[str],
        source: str,
        artifact_id: str | None,
    ) -> dict[str, Any]:
        vector = vectorizer.transform([text])
        predicted = str(model.predict(vector)[0])
        confidence = None
        probabilities: list[dict[str, Any]] = []
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(vector)[0]
            class_names = [str(item) for item in getattr(model, "classes_", labels or [])]
            probabilities = [{"label": class_names[i], "score": round(float(score), 4)} for i, score in enumerate(probs)]
            confidence = max((item["score"] for item in probabilities), default=None)
        elif hasattr(model, "decision_function"):
            scores = np.asarray(model.decision_function(vector)).ravel()
            class_names = [str(item) for item in getattr(model, "classes_", labels or [])]
            probabilities = [{"label": class_names[i], "score": round(float(score), 4)} for i, score in enumerate(scores[: len(class_names)])]

        top_terms = self._top_text_features(vector, vectorizer, model, predicted)
        return {
            "article_id": article_id,
            "target": target,
            "model": model_name,
            "model_source": source,
            "artifact_id": artifact_id,
            "prediction": predicted,
            "confidence": confidence,
            "probabilities": sorted(probabilities, key=lambda item: item["score"], reverse=True)[:8],
            "top_terms": top_terms,
            "explanation": self._prediction_explanation(target, predicted, confidence, top_terms, source),
        }

    def _top_text_features(self, vector: Any, vectorizer: Any, model: Any, predicted: str) -> list[dict[str, Any]]:
        names = list(vectorizer.get_feature_names_out())
        coo = vector.tocoo()
        weights: dict[int, float] = {int(idx): float(value) for idx, value in zip(coo.col, coo.data)}
        if not weights:
            return []
        contributions = weights.copy()
        if hasattr(model, "coef_") and hasattr(model, "classes_"):
            classes = [str(item) for item in model.classes_]
            class_idx = classes.index(predicted) if predicted in classes else 0
            coef = np.asarray(model.coef_)
            coef_row = coef[class_idx if coef.shape[0] > 1 else 0]
            contributions = {idx: value * float(coef_row[idx]) for idx, value in weights.items()}
        ranked = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)[:12]
        return [{"term": names[idx], "weight": round(float(score), 6), "tfidf": round(weights[idx], 6)} for idx, score in ranked if idx < len(names)]

    def _prediction_explanation(self, target: str, predicted: str, confidence: float | None, top_terms: list[dict[str, Any]], source: str) -> str:
        term_text = ", ".join(str(item["term"]) for item in top_terms[:5]) or "the article text profile"
        confidence_text = f" with {confidence:.0%} confidence" if isinstance(confidence, float) else ""
        source_text = "saved model artifact" if source == "artifact" else "on-demand baseline model"
        return f"The {source_text} predicts {target} as {predicted}{confidence_text}. The strongest text signals are {term_text}."

    def _diagnostics_payload_from_fitted(self, fitted: dict[str, Any], target: MLTarget, model: MLModelName) -> MLDiagnosticsResponse:
        class_metrics = fitted.get("class_metrics", [])
        low_classes = [
            {**item, "reason": self._class_issue_reason(item)}
            for item in class_metrics
            if float(item.get("f1", 0)) < 0.6 or float(item.get("recall", 0)) < 0.6 or float(item.get("precision", 0)) < 0.6
        ]
        error_samples = [item for item in fitted.get("sample_predictions", []) if not item.get("correct")][:30]
        factors = self._failure_factors(fitted, target, low_classes)
        payload = MLDiagnosticsResponse(
            status="ready",
            target=target,
            model=model,
            total_documents=fitted["total_documents"],
            metrics=fitted["metrics"],
            class_metrics=class_metrics,
            low_performing_classes=low_classes,
            confusion_matrix=fitted["confusion_matrix"],
            labels=fitted["labels"],
            confusion_pairs=fitted["confusion_pairs"],
            error_samples=error_samples,
            failure_factors=factors,
            recommendations=self._recommendations(factors, target, model),
            feature_diagnostics={
                "vectorizer": fitted["vectorizer"],
                "top_features": fitted["feature_importance"][:20],
                "vocabulary_size": fitted["vectorizer"].get("vocabulary_size", 0),
                "feature_limit": fitted["vectorizer"].get("max_features", 0),
                "notes": self._feature_notes(fitted),
            },
            train_test_split={"train_documents": fitted["train_documents"], "test_documents": fitted["test_documents"], "test_size": fitted["test_size"], "stratified": fitted["stratified"]},
            notes=fitted["notes"],
        )
        return payload

    def _artifact_diagnostics(self, artifact_id: str) -> dict[str, Any]:
        detail = self.artifact(artifact_id)
        if not detail:
            return {}
        diagnostics = self._read_json(Path(detail.artifact_dir) / "diagnostics.json", {})
        if diagnostics:
            diagnostics["sample_predictions"] = self._read_json(Path(detail.artifact_dir) / "sample_predictions.json", diagnostics.get("error_samples", []))
            diagnostics["class_metrics"] = self._read_json(Path(detail.artifact_dir) / "class_metrics.json", diagnostics.get("class_metrics", []))
        return diagnostics

    def _artifact_metric_deltas(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not items:
            return []
        baseline = items[0]
        rows = []
        for item in items:
            metrics = item.get("metrics", {})
            base_metrics = baseline.get("metrics", {})
            rows.append({
                "artifact_id": item["artifact_id"],
                "model": item["model"],
                "accuracy": metrics.get("accuracy"),
                "accuracy_delta": self._metric_delta(metrics.get("accuracy"), base_metrics.get("accuracy")),
                "f1_macro": metrics.get("f1_macro"),
                "f1_delta": self._metric_delta(metrics.get("f1_macro"), base_metrics.get("f1_macro")),
                "precision_macro": metrics.get("precision_macro"),
                "recall_macro": metrics.get("recall_macro"),
            })
        return rows

    def _artifact_class_deltas(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(items) < 2:
            return []
        baseline_by_label = {row.get("label"): row for row in items[0].get("class_metrics", [])}
        rows = []
        for item in items[1:]:
            for row in item.get("class_metrics", []):
                label = row.get("label")
                baseline = baseline_by_label.get(label, {})
                rows.append({
                    "artifact_id": item["artifact_id"],
                    "label": label,
                    "precision_delta": self._metric_delta(row.get("precision"), baseline.get("precision")),
                    "recall_delta": self._metric_delta(row.get("recall"), baseline.get("recall")),
                    "f1_delta": self._metric_delta(row.get("f1"), baseline.get("f1")),
                    "support": row.get("support"),
                })
        return rows

    def _artifact_confusion_deltas(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(items) < 2:
            return []
        baseline = {(row.get("actual"), row.get("predicted")): int(row.get("count") or 0) for row in items[0].get("confusion_pairs", [])}
        rows = []
        for item in items[1:]:
            for row in item.get("confusion_pairs", []):
                key = (row.get("actual"), row.get("predicted"))
                count = int(row.get("count") or 0)
                rows.append({
                    "artifact_id": item["artifact_id"],
                    "actual": row.get("actual"),
                    "predicted": row.get("predicted"),
                    "count": count,
                    "count_delta": count - baseline.get(key, 0),
                    "correct": row.get("correct"),
                })
        return rows

    def _metric_delta(self, value: Any, baseline: Any) -> float | None:
        try:
            return round(float(value) - float(baseline), 4)
        except (TypeError, ValueError):
            return None

    def _load_artifact_model(self, artifact_id: str | None, target: MLTarget) -> tuple[MLArtifactRecord, Any, Any, list[str]] | None:
        if not artifact_id:
            return None
        detail = self.artifact(artifact_id)
        if not detail or detail.target != target or detail.status != "ready":
            return None
        try:
            import joblib

            model = joblib.load(Path(detail.artifact_dir) / "model.joblib")
            vectorizer = joblib.load(Path(detail.artifact_dir) / "vectorizer.joblib")
        except Exception:
            return None
        labels = detail.manifest.get("labels", []) if isinstance(detail.manifest, dict) else []
        return detail, model, vectorizer, [str(label) for label in labels]

    def _latest_artifact_model(self, target: MLTarget, prefer_linear: bool = False) -> tuple[MLArtifactRecord, Any, Any, list[str]] | None:
        clauses = ["target = ?", "status = 'ready'"]
        params: list[Any] = [target]
        if prefer_linear:
            clauses.append("model IN ('logistic_regression', 'linear_svm')")
        row = self.db.fetch_one(
            f"""
            SELECT artifact_id FROM model_artifacts
            WHERE {' AND '.join(clauses)}
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            tuple(params),
        )
        return self._load_artifact_model(row["artifact_id"], target) if row else None

    def _tree_explanation(self, article_id: str, target: MLTarget, text: str, artifact_id: str | None, limit: int, **kwargs: Any) -> ArticleExplanationResponse:
        loaded = self._load_artifact_model(artifact_id, target) if artifact_id else self._latest_artifact_model(target)
        model_source = "artifact"
        if loaded and not hasattr(loaded[1], "tree_"):
            loaded = None
        if loaded is None:
            fitted = self._fit(target=target, model="decision_tree", limit=limit, **kwargs)
            if fitted["status"] != "ready":
                return ArticleExplanationResponse(status=fitted["status"], total_documents=fitted["total_documents"], article_id=article_id, target=target, mode="tree_path", notes=fitted["notes"])
            model, vectorizer, labels, feature_names, artifact = fitted["model_object"], fitted["vectorizer_object"], fitted["labels"], fitted["feature_names"], None
            model_source = "on_demand"
        else:
            artifact, model, vectorizer, labels = loaded
            feature_names = list(vectorizer.get_feature_names_out())
        if not hasattr(model, "tree_"):
            return ArticleExplanationResponse(status="insufficient_data", article_id=article_id, target=target, mode="tree_path", notes=["No Decision Tree model is available for tree path explanation."])
        vector = vectorizer.transform([text])
        tree = model.tree_
        node_indicator = model.decision_path(vector)
        leaf_id = model.apply(vector)[0]
        node_ids = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
        path = []
        for node_id in node_ids:
            if node_id == leaf_id or tree.feature[node_id] < 0:
                path.append({"node_id": int(node_id), "type": "leaf", "samples": int(tree.n_node_samples[node_id])})
                continue
            feature_idx = int(tree.feature[node_id])
            feature_name = feature_names[feature_idx]
            threshold = float(tree.threshold[node_id])
            value = float(vector[0, feature_idx])
            direction = "left" if value <= threshold else "right"
            path.append({"node_id": int(node_id), "type": "split", "feature": feature_name, "threshold": round(threshold, 6), "value": round(value, 6), "direction": direction, "condition": f"{feature_name} <= {threshold:.4f}" if direction == "left" else f"{feature_name} > {threshold:.4f}", "samples": int(tree.n_node_samples[node_id])})
        probs = model.predict_proba(vector)[0] if hasattr(model, "predict_proba") else []
        prediction = str(model.predict(vector)[0])
        confidence = round(float(max(probs)), 4) if len(probs) else None
        probabilities = [{"label": str(label), "score": round(float(probs[idx]), 4)} for idx, label in enumerate(getattr(model, "classes_", labels))] if len(probs) else []
        return ArticleExplanationResponse(
            status="ready",
            total_documents=1,
            article_id=article_id,
            target=target,
            mode="tree_path",
            prediction=prediction,
            confidence=confidence,
            actual_label=self._actual_label_for_article(article_id, target),
            model="decision_tree",
            model_source=model_source,
            artifact_id=artifact.artifact_id if loaded else None,
            explanation=f"The Decision Tree predicts {target} as {prediction}. It followed {sum(1 for step in path if step['type'] == 'split')} split conditions before the leaf node.",
            path=path,
            probabilities=probabilities,
        )

    def _actual_label_for_article(self, article_id: str, target: MLTarget) -> str | None:
        row = self.db.fetch_one(
            """
            SELECT article_id, title, source, category, category_name, content_clean,
                   COALESCE(NULLIF(category_name, ''), NULLIF(category, ''), 'unknown') AS category_label
            FROM articles
            WHERE article_id = ?
            """,
            (article_id,),
        )
        if not row:
            return None
        data = dict(row)
        data["text"] = f"{data.get('title') or ''}\n{data.get('content_clean') or ''}".strip()
        return self._label(data, target)

    def _explanation_mode(self, mode: str) -> str:
        return mode if mode in {"tree_path", "linear_coefficients", "top_terms"} else "top_terms"

    def _class_issue_reason(self, item: dict[str, Any]) -> str:
        if float(item.get("recall", 0)) < 0.5:
            return "Low recall: many true samples in this class are being missed."
        if float(item.get("precision", 0)) < 0.5:
            return "Low precision: predictions for this class often belong to another class."
        return "F1 is below the review threshold."

    def _failure_factors(self, fitted: dict[str, Any], target: MLTarget, low_classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        factors: list[dict[str, Any]] = []
        total = int(fitted.get("total_documents") or 0)
        if total < 50:
            factors.append({"severity": "warning", "factor": "small_dataset", "title": "Small evaluation corpus", "detail": "Model metrics are unstable because fewer than 50 documents are available."})
        distribution = fitted.get("prepared_distribution", {})
        if distribution:
            counts = list(distribution.values())
            if min(counts) and max(counts) / min(counts) >= 3:
                factors.append({"severity": "warning", "factor": "label_imbalance", "title": "Label imbalance", "detail": "Some labels have at least 3x more samples than the smallest label."})
        if low_classes:
            factors.append({"severity": "error", "factor": "weak_classes", "title": "Low-performing classes", "detail": f"{len(low_classes)} labels are below precision/recall/F1 review thresholds."})
        if target == "sentiment":
            factors.append({"severity": "info", "factor": "weak_labels", "title": "Weak sentiment labels", "detail": "Sentiment training currently uses lexicon-derived weak labels, not manually audited labels."})
        if float(fitted.get("metrics", {}).get("f1_macro", 0)) < 0.65:
            factors.append({"severity": "warning", "factor": "low_macro_f1", "title": "Low macro F1", "detail": "Macro F1 is below 0.65, which means class-level performance is inconsistent."})
        if not fitted.get("feature_importance"):
            factors.append({"severity": "info", "factor": "limited_explainability", "title": "Limited feature importance", "detail": "This model does not expose reliable feature importance; use Logistic Regression or Decision Tree for clearer explanations."})
        return factors

    def _recommendations(self, factors: list[dict[str, Any]], target: MLTarget, model: MLModelName) -> list[dict[str, Any]]:
        factor_keys = {item["factor"] for item in factors}
        recs = []
        if "small_dataset" in factor_keys:
            recs.append({"priority": "high", "title": "Add more labeled articles", "detail": "Increase each target class to at least 30-50 examples before trusting model comparisons."})
        if "label_imbalance" in factor_keys:
            recs.append({"priority": "high", "title": "Balance classes or apply class weights", "detail": "Use stratified sampling, class_weight, or targeted ingestion for underrepresented labels."})
        if "weak_classes" in factor_keys:
            recs.append({"priority": "medium", "title": "Review confused labels", "detail": "Inspect error samples and merge ambiguous categories or add discriminative keywords/entities."})
        if target == "sentiment":
            recs.append({"priority": "medium", "title": "Replace weak sentiment labels", "detail": "Create a small manually labeled validation set before reporting sentiment accuracy as business truth."})
        if model == "decision_tree":
            recs.append({"priority": "medium", "title": "Use tree as explanation baseline", "detail": "Compare against Logistic Regression or SVM for accuracy, then use tree paths for stakeholder explanation."})
        if not recs:
            recs.append({"priority": "low", "title": "Run artifact comparison", "detail": "Persist candidate models and compare performance over time with the same dataset filters."})
        return recs

    def _feature_notes(self, fitted: dict[str, Any]) -> list[str]:
        notes = []
        vocab = int(fitted.get("vectorizer", {}).get("vocabulary_size") or 0)
        limit = int(fitted.get("vectorizer", {}).get("max_features") or 0)
        if limit and vocab >= int(limit * 0.9):
            notes.append("Vocabulary is close to the feature limit; increasing feature_limit may preserve more signals.")
        if vocab < 50:
            notes.append("Vocabulary is small; run NLP preprocessing or ingest richer article content.")
        return notes

    def _feature_importance(self, model: Any, feature_names: list[str], labels: list[str]) -> list[dict[str, Any]]:
        values = None
        if hasattr(model, "feature_importances_"):
            values = np.asarray(model.feature_importances_)
        elif hasattr(model, "coef_"):
            values = np.mean(np.abs(np.asarray(model.coef_)), axis=0)
        if values is None:
            return []
        order = np.argsort(values)[::-1][:20]
        return [{"feature": feature_names[i], "weight": round(float(values[i]), 6), "rank": rank + 1} for rank, i in enumerate(order) if values[i] > 0]

    def _tree_summary(self, fitted: dict[str, Any]) -> dict[str, Any]:
        model = fitted["model_object"]
        return {"max_depth": int(model.get_depth()), "node_count": int(model.tree_.node_count), "n_leaves": int(model.get_n_leaves())}

    def _class_metrics(self, report: dict[str, Any], labels: list[str]) -> list[dict[str, Any]]:
        rows = []
        for label in labels:
            value = report.get(label, {})
            if isinstance(value, dict):
                rows.append({
                    "label": label,
                    "precision": round(float(value.get("precision", 0)), 4),
                    "recall": round(float(value.get("recall", 0)), 4),
                    "f1": round(float(value.get("f1-score", 0)), 4),
                    "support": int(value.get("support", 0)),
                })
        return rows

    def _sample_predictions(self, rows: list[dict[str, Any]], test_idx: list[int], actual: list[str], predicted: list[str], classifier: Any, x_test: Any) -> list[dict[str, Any]]:
        confidence_values: list[float | None]
        if hasattr(classifier, "predict_proba"):
            probs = classifier.predict_proba(x_test)
            confidence_values = [round(float(max(row)), 4) for row in probs]
        else:
            confidence_values = [None for _ in predicted]
        output = []
        for pos, idx in enumerate(test_idx):
            row = rows[idx]
            output.append({
                "article_id": row["article_id"],
                "title": row["title"],
                "source": row["source"],
                "category": row["category_label"],
                "actual": actual[pos],
                "predicted": predicted[pos],
                "correct": actual[pos] == predicted[pos],
                "confidence": confidence_values[pos],
            })
        return output

    def _confusion_pairs(self, actual: list[str], predicted: list[str]) -> list[dict[str, Any]]:
        counts = Counter(zip(actual, predicted))
        return [
            {"actual": a, "predicted": p, "count": count, "correct": a == p}
            for (a, p), count in counts.most_common()
        ]

    def _round_nested(self, value: Any) -> Any:
        if isinstance(value, float):
            return round(value, 4)
        if isinstance(value, dict):
            return {key: self._round_nested(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._round_nested(item) for item in value]
        return value

    def _flatten(self, payload: Any, prefix: str = "") -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item if isinstance(item, dict) else {"value": item} for item in payload]
        if isinstance(payload, dict):
            rows = []
            for key, value in payload.items():
                if isinstance(value, dict):
                    row = {"section": key, **value}
                    rows.append(row)
                else:
                    rows.append({"section": key, "value": json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value})
            return rows
        return [{"value": payload}]

    def _insert_artifact(self, artifact_id: str, job_id: int | None, target: str, model: str, status: str, params: dict[str, Any], metrics: dict[str, Any], artifact_dir: Path, error: str | None = None) -> MLArtifactRecord:
        self.db.execute(
            """
            INSERT OR REPLACE INTO model_artifacts
                (artifact_id, job_id, target, model, status, params_json, metrics_json, artifact_dir, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                job_id,
                target,
                model,
                status,
                json.dumps(params, ensure_ascii=False),
                json.dumps(metrics, ensure_ascii=False),
                str(artifact_dir),
                error,
            ),
        )
        row = self.db.fetch_one("SELECT * FROM model_artifacts WHERE artifact_id = ?", (artifact_id,))
        return self._artifact_record(dict(row))

    def _artifact_record(self, data: dict[str, Any]) -> MLArtifactRecord:
        artifact_dir = Path(data.get("artifact_dir") or "")
        files = sorted(path.name for path in artifact_dir.iterdir() if artifact_dir.exists() and path.is_file())
        return MLArtifactRecord(
            artifact_id=data["artifact_id"],
            job_id=int(data["job_id"]) if data.get("job_id") is not None else None,
            target=data["target"],
            model=data["model"],
            status=data["status"],
            params=self._read_json_value(data.get("params_json"), {}),
            metrics=self._read_json_value(data.get("metrics_json"), {}),
            artifact_dir=str(artifact_dir),
            error=data.get("error"),
            created_at=data.get("created_at"),
            files=files,
        )

    def _matrix_rows(self, labels: list[str], matrix: list[list[int]]) -> list[dict[str, Any]]:
        return [{"actual": labels[idx], **{label: row[col_idx] for col_idx, label in enumerate(labels)}} for idx, row in enumerate(matrix)]

    def _write_json(self, path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_json(self, path: Path, fallback: Any) -> Any:
        if not path.exists():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return fallback

    def _read_json_value(self, value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            if not rows:
                f.write("")
                return
            writer = csv.DictWriter(f, fieldnames=sorted({key for row in rows for key in row}))
            writer.writeheader()
            writer.writerows(rows)
