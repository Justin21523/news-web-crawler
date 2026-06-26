from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.schemas.jobs import JobCreateRequest, JobRecord
from app.services.database import Database, decode_json

ROOT_DIR = Path(__file__).resolve().parents[3]


class JobService:
    def __init__(self, db: Database | None = None, settings: Settings | None = None):
        self.db = db or Database()
        self.settings = settings or get_settings()
        self.executor = ThreadPoolExecutor(max_workers=self.settings.max_job_workers)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def create(self, request: JobCreateRequest) -> JobRecord:
        log_path = self.settings.resolved_jobs_dir / "pending.log"
        job_id = self.db.execute(
            """
            INSERT INTO jobs (type, status, params_json, log_path)
            VALUES (?, 'queued', ?, ?)
            """,
            (request.type, json.dumps(request.params, ensure_ascii=False), str(log_path)),
        )
        log_path = self.settings.resolved_jobs_dir / f"{job_id}.log"
        self.db.execute("UPDATE jobs SET log_path=? WHERE id=?", (str(log_path), job_id))
        self.executor.submit(self._run_job, job_id)
        job = self.get(job_id)
        if job is None:
            raise RuntimeError("Failed to create job")
        return job

    def list(self, limit: int = 20) -> list[JobRecord]:
        rows = self.db.fetch_all(
            """
            SELECT * FROM jobs
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (min(max(limit, 1), 100),),
        )
        return [self._to_record(dict(row)) for row in rows]

    def get(self, job_id: int) -> JobRecord | None:
        row = self.db.fetch_one("SELECT * FROM jobs WHERE id=?", (job_id,))
        return self._to_record(dict(row)) if row else None

    def logs(self, job_id: int, max_bytes: int = 120_000) -> str:
        job = self.get(job_id)
        if not job or not job.log_path:
            return ""
        path = Path(job.log_path)
        if not path.exists():
            return ""
        with path.open("rb") as f:
            if path.stat().st_size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            return f.read().decode("utf-8", errors="replace")

    def _run_job(self, job_id: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        log_path = Path(job.log_path or self.settings.resolved_jobs_dir / f"{job_id}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.db.execute(
            "UPDATE jobs SET status='running', started_at=datetime('now') WHERE id=?",
            (job_id,),
        )
        command = self._build_command(job.type, job.params, job_id)
        env = os.environ.copy()
        pythonpath = os.pathsep.join([str(ROOT_DIR / "backend"), str(ROOT_DIR)])
        env.update(
            {
                "PYTHONPATH": pythonpath,
                "NEWS_DATA_DIR": str(self.settings.data_dir),
                "NEWS_DB_PATH": str(self.settings.resolved_db_path),
                "NEWS_MODELS_DIR": str(self.settings.resolved_models_dir),
            }
        )
        try:
            with log_path.open("w", encoding="utf-8") as log:
                log.write(f"$ {' '.join(command)}\n\n")
                log.flush()
                result = subprocess.run(
                    command,
                    cwd=ROOT_DIR,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            if result.returncode == 0:
                self.db.execute(
                    """
                    UPDATE jobs
                    SET status='succeeded', progress_done=1, progress_total=1, ended_at=datetime('now')
                    WHERE id=?
                    """,
                    (job_id,),
                )
            else:
                self.db.execute(
                    """
                    UPDATE jobs
                    SET status='failed', error=?, ended_at=datetime('now')
                    WHERE id=?
                    """,
                    (f"Command exited with code {result.returncode}", job_id),
                )
        except Exception as exc:
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"\n[error] {exc}\n")
            self.db.execute(
                "UPDATE jobs SET status='failed', error=?, ended_at=datetime('now') WHERE id=?",
                (str(exc), job_id),
            )

    def _build_command(self, job_type: str, params: dict[str, Any], job_id: int | None = None) -> list[str]:
        py = sys.executable
        db_path = str(self.settings.resolved_db_path)
        if job_type == "demo":
            command = [py, "pipeline_cli.py", "--db", db_path, "demo"]
            if params.get("reset", True):
                command.append("--reset")
            if params.get("sample"):
                command.extend(["--sample", str(params["sample"])])
            return command
        if job_type == "crawl":
            spider = str(params.get("spider") or "all")
            command = [py, "run_crawler.py", spider]
            for key in ("days", "start_date", "end_date", "max_articles", "categories"):
                if params.get(key) not in (None, ""):
                    command.extend([f"--{key.replace('_', '-')}", str(params[key])])
            return command
        if job_type == "ingest":
            input_dir = str(params.get("input_dir") or self.settings.resolved_raw_dir)
            return [py, "pipeline_cli.py", "--db", db_path, "ingest", "--input-dir", input_dir]
        if job_type == "nlp":
            engine = str(params.get("engine") or "jieba")
            batch_size = str(params.get("batch_size") or 32)
            command = [py, "pipeline_cli.py", "--db", db_path, "nlp", "--engine", engine, "--batch-size", batch_size]
            if params.get("ner_strategy"):
                command.extend(["--ner-strategy", str(params["ner_strategy"])])
            return command
        if job_type == "entity_extraction":
            command = [
                py,
                "pipeline_cli.py",
                "--db",
                db_path,
                "entities",
                "--provider",
                str(params.get("provider") or "fallback"),
                "--limit",
                str(params.get("limit") or 500),
            ]
            if params.get("activate", True):
                command.append("--activate")
            if params.get("spacy_model"):
                command.extend(["--spacy-model", str(params["spacy_model"])])
            for key in ("source", "category", "date_from", "date_to"):
                if params.get(key) not in (None, ""):
                    command.extend([f"--{key.replace('_', '-')}", str(params[key])])
            return command
        if job_type == "tfidf":
            return [py, "pipeline_cli.py", "--db", db_path, "tfidf", "--output", str(self.settings.resolved_models_dir)]
        if job_type == "export":
            fmt = str(params.get("format") or "parquet")
            output = str(params.get("output") or self.settings.resolved_processed_dir / f"articles.{fmt}")
            command = [py, "pipeline_cli.py", "--db", db_path, "export", "--format", fmt, "--output", output]
            if params.get("with_nlp", True):
                command.append("--with-nlp")
            return command
        if job_type == "run_all":
            return [
                py,
                "pipeline_cli.py",
                "--db",
                db_path,
                "run-all",
                "--input-dir",
                str(params.get("input_dir") or self.settings.resolved_raw_dir),
                "--batch-size",
                str(params.get("batch_size") or 32),
            ]
        if job_type == "analysis":
            steps = params.get("steps") or ["collocation", "text_mining", "clustering", "sentiment", "time_series", "summarization"]
            command = [py, "run_analysis.py", "--limit", str(params.get("limit") or 1000), "--steps"]
            command.extend([str(step) for step in steps])
            return command
        if job_type in {"train_ml", "train_decision_tree"}:
            model = "decision_tree" if job_type == "train_decision_tree" else str(params.get("model") or "logistic_regression")
            command = [
                py,
                "-m",
                "app.cli.ml_train",
                "--db",
                db_path,
                "--models-dir",
                str(self.settings.resolved_models_dir),
                "--job-id",
                str(job_id or 0),
                "--target",
                str(params.get("target") or "source"),
                "--model",
                model,
                "--test-size",
                str(params.get("test_size") or 0.3),
                "--feature-limit",
                str(params.get("feature_limit") or 5000),
                "--min-class-count",
                str(params.get("min_class_count") or 2),
                "--min-samples-split",
                str(params.get("min_samples_split") or 2),
                "--min-samples-leaf",
                str(params.get("min_samples_leaf") or 1),
                "--criterion",
                str(params.get("criterion") or "gini"),
                "--limit",
                str(params.get("limit") or 2000),
            ]
            if params.get("collapse_rare", True):
                command.append("--collapse-rare")
            else:
                command.append("--no-collapse-rare")
            for key in ("source", "category", "date_from", "date_to", "max_depth"):
                if params.get(key) not in (None, ""):
                    command.extend([f"--{key.replace('_', '-')}", str(params[key])])
            return command
        if job_type in {"persist_text_mining_assignments", "text_mining_assignments"}:
            command = [
                py,
                "-m",
                "app.cli.text_mining_assignments",
                "--db",
                db_path,
                "--assignment-type",
                str(params.get("assignment_type") or "both"),
                "--topic-method",
                str(params.get("topic_method") or "nmf"),
                "--cluster-method",
                str(params.get("cluster_method") or "kmeans"),
                "--n-topics",
                str(params.get("n_topics") or 5),
                "--n-clusters",
                str(params.get("n_clusters") or 5),
                "--limit",
                str(params.get("limit") or 500),
            ]
            for key in ("source", "category", "date_from", "date_to"):
                if params.get(key) not in (None, ""):
                    command.extend([f"--{key.replace('_', '-')}", str(params[key])])
            return command
        if job_type == "export_ml_diagnostics_report":
            command = [
                py,
                "-m",
                "app.cli.ml_diagnostics_report",
                "--db",
                db_path,
                "--job-id",
                str(job_id or 0),
                "--target",
                str(params.get("target") or "source"),
                "--model",
                str(params.get("model") or "logistic_regression"),
                "--feature-limit",
                str(params.get("feature_limit") or 1000),
                "--max-depth",
                str(params.get("max_depth") or 4),
                "--limit",
                str(params.get("limit") or 2000),
                "--artifact-ids",
                ",".join(str(item) for item in params.get("artifact_ids", []) if item) if isinstance(params.get("artifact_ids"), list) else str(params.get("artifact_ids") or ""),
                "--article-ids",
                ",".join(str(item) for item in params.get("article_ids", []) if item) if isinstance(params.get("article_ids"), list) else str(params.get("article_ids") or ""),
                "--explanation-modes",
                ",".join(str(item) for item in params.get("explanation_modes", []) if item) if isinstance(params.get("explanation_modes"), list) else str(params.get("explanation_modes") or "linear_coefficients,tree_path"),
                "--template",
                str(params.get("template") or "portfolio"),
                "--sections",
                ",".join(str(item) for item in params.get("sections", []) if item) if isinstance(params.get("sections"), list) else str(params.get("sections") or ""),
                "--report-title",
                str(params.get("report_title") or "ML Diagnostics Report"),
            ]
            if params.get("prepared_for") not in (None, ""):
                command.extend(["--prepared-for", str(params["prepared_for"])])
            for key in ("source", "category", "date_from", "date_to", "actual", "predicted", "class_label"):
                if params.get(key) not in (None, ""):
                    command.extend([f"--{key.replace('_', '-')}", str(params[key])])
            return command
        raise ValueError(f"Unsupported job type: {job_type}")

    def _to_record(self, data: dict[str, Any]) -> JobRecord:
        return JobRecord(
            id=int(data["id"]),
            type=data["type"],
            status=data["status"],
            params=decode_json(data.get("params_json"), {}),
            progress_done=int(data.get("progress_done") or 0),
            progress_total=int(data.get("progress_total") or 0),
            log_path=data.get("log_path"),
            error=data.get("error"),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
        )
