from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.database import Database
from app.services.ml import MLService


def _none_if_empty(value: str | None) -> str | None:
    return value if value not in (None, "") else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Train and persist ML model artifacts.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--models-dir", required=True)
    parser.add_argument("--job-id", type=int)
    parser.add_argument("--target", choices=["category", "source", "sentiment"], default="source")
    parser.add_argument("--model", choices=["logistic_regression", "linear_svm", "naive_bayes", "decision_tree", "random_forest"], default="logistic_regression")
    parser.add_argument("--source")
    parser.add_argument("--category")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--test-size", type=float, default=0.3)
    parser.add_argument("--feature-limit", type=int, default=5000)
    parser.add_argument("--min-class-count", type=int, default=2)
    parser.add_argument("--collapse-rare", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-depth", type=int)
    parser.add_argument("--min-samples-split", type=int, default=2)
    parser.add_argument("--min-samples-leaf", type=int, default=1)
    parser.add_argument("--criterion", choices=["gini", "entropy", "log_loss"], default="gini")
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    db = Database(args.db)
    db.init()
    service = MLService(db=db, models_dir=Path(args.models_dir))
    params: dict[str, Any] = {
        "source": _none_if_empty(args.source),
        "category": _none_if_empty(args.category),
        "date_from": _none_if_empty(args.date_from),
        "date_to": _none_if_empty(args.date_to),
        "test_size": args.test_size,
        "feature_limit": args.feature_limit,
        "min_class_count": args.min_class_count,
        "collapse_rare": args.collapse_rare,
        "max_depth": args.max_depth,
        "min_samples_split": args.min_samples_split,
        "min_samples_leaf": args.min_samples_leaf,
        "criterion": args.criterion,
        "limit": args.limit,
    }
    print(f"Training {args.model} for target={args.target}")
    print(json.dumps({"job_id": args.job_id, "params": params}, ensure_ascii=False, indent=2))
    record = service.train_and_persist(target=args.target, model=args.model, job_id=args.job_id, **params)
    print("Artifact persisted")
    print(json.dumps(record.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
