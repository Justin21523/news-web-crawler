from __future__ import annotations

import argparse
import json

from app.services.database import Database
from app.services.ml_diagnostics_report import MLDiagnosticsReportService


def _csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ML diagnostics reports.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--job-id", type=int, default=0)
    parser.add_argument("--target", default="source", choices=["category", "source", "sentiment"])
    parser.add_argument("--model", default="logistic_regression", choices=["logistic_regression", "linear_svm", "naive_bayes", "decision_tree", "random_forest"])
    parser.add_argument("--artifact-ids", default="")
    parser.add_argument("--article-ids", default="")
    parser.add_argument("--explanation-modes", default="linear_coefficients,tree_path")
    parser.add_argument("--template", default="portfolio")
    parser.add_argument("--sections", default="")
    parser.add_argument("--report-title", default="ML Diagnostics Report")
    parser.add_argument("--prepared-for")
    parser.add_argument("--source")
    parser.add_argument("--category")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--actual")
    parser.add_argument("--predicted")
    parser.add_argument("--class-label")
    parser.add_argument("--feature-limit", type=int, default=1000)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    db = Database(args.db)
    db.init()
    record = MLDiagnosticsReportService(db).generate(
        target=args.target,
        model=args.model,
        job_id=args.job_id or None,
        artifact_ids=_csv(args.artifact_ids),
        article_ids=_csv(args.article_ids),
        explanation_modes=_csv(args.explanation_modes),
        template=args.template,
        sections=_csv(args.sections) or None,
        report_title=args.report_title,
        prepared_for=args.prepared_for,
        source=args.source,
        category=args.category,
        date_from=args.date_from,
        date_to=args.date_to,
        actual=args.actual,
        predicted=args.predicted,
        class_label=args.class_label,
        feature_limit=args.feature_limit,
        max_depth=args.max_depth,
        limit=args.limit,
    )
    print(json.dumps(record.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
