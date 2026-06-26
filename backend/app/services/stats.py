from __future__ import annotations

from app.schemas.stats import StatsResponse
from app.services.database import Database
from app.services.jobs import JobService


class StatsService:
    def __init__(self, db: Database | None = None, jobs: JobService | None = None):
        self.db = db or Database()
        self.jobs = jobs or JobService(self.db)

    def stats(self) -> StatsResponse:
        total = self._count("SELECT COUNT(*) FROM articles")
        cleaned = self._count("SELECT COUNT(*) FROM articles WHERE status='cleaned'")
        enriched = self._count("SELECT COUNT(*) FROM nlp_outputs")
        source_rows = self.db.fetch_all(
            "SELECT source, COUNT(*) AS cnt FROM articles GROUP BY source ORDER BY cnt DESC"
        )
        date_row = self.db.fetch_one(
            "SELECT MIN(publish_date), MAX(publish_date) FROM articles WHERE publish_date IS NOT NULL AND trim(publish_date) != ''"
        )
        return StatsResponse(
            total_articles=total,
            cleaned=cleaned,
            enriched=enriched,
            sources={row["source"] or "unknown": int(row["cnt"]) for row in source_rows},
            date_range=[date_row[0], date_row[1]] if date_row else [None, None],
            latest_jobs=self.jobs.list(limit=5),
        )

    def _count(self, sql: str) -> int:
        row = self.db.fetch_one(sql)
        return int(row[0] if row else 0)
