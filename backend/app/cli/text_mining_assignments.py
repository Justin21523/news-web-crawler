from __future__ import annotations

import argparse
import json

from app.services.database import Database
from app.services.text_mining import TextMiningService


def main() -> None:
    parser = argparse.ArgumentParser(description="Persist topic and cluster assignments for article facets.")
    parser.add_argument("--db", required=True)
    parser.add_argument("--assignment-type", default="both", choices=["topic", "cluster", "both"])
    parser.add_argument("--topic-method", default="nmf", choices=["nmf", "lda"])
    parser.add_argument("--cluster-method", default="kmeans", choices=["kmeans", "hierarchical"])
    parser.add_argument("--n-topics", type=int, default=5)
    parser.add_argument("--n-clusters", type=int, default=5)
    parser.add_argument("--source")
    parser.add_argument("--category")
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    db = Database(args.db)
    db.init()
    result = TextMiningService(db).persist_assignments(
        assignment_type=args.assignment_type,
        topic_method=args.topic_method,
        cluster_method=args.cluster_method,
        n_topics=args.n_topics,
        n_clusters=args.n_clusters,
        source=args.source,
        category=args.category,
        date_from=args.date_from,
        date_to=args.date_to,
        limit=args.limit,
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
