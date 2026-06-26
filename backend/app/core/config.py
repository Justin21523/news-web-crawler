from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "News Web Crawler API"
    api_prefix: str = "/api/v1"
    cors_origins: str = ",".join(
        f"http://{host}:{port}"
        for port in range(3000, 3011)
        for host in ("localhost", "127.0.0.1")
    )
    data_dir: Path = Path("data")
    db_path: Path | None = None
    raw_dir: Path | None = None
    processed_dir: Path | None = None
    reports_dir: Path | None = None
    models_dir: Path | None = None
    jobs_dir: Path | None = None
    max_job_workers: int = 1
    llm_enabled: bool = False
    llm_base_url: str = "http://127.0.0.1:8080/v1"
    llm_model: str = "local-llama"
    llm_timeout_seconds: float = 45.0

    model_config = SettingsConfigDict(
        env_prefix="NEWS_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def resolved_db_path(self) -> Path:
        return self.db_path or self.data_dir / "news.db"

    @property
    def resolved_raw_dir(self) -> Path:
        return self.raw_dir or self.data_dir / "raw"

    @property
    def resolved_processed_dir(self) -> Path:
        return self.processed_dir or self.data_dir / "processed"

    @property
    def resolved_reports_dir(self) -> Path:
        return self.reports_dir or self.data_dir / "reports"

    @property
    def resolved_models_dir(self) -> Path:
        return self.models_dir or self.data_dir / "models"

    @property
    def resolved_jobs_dir(self) -> Path:
        return self.jobs_dir or self.data_dir / "jobs"

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.resolved_raw_dir,
            self.resolved_processed_dir,
            self.resolved_reports_dir,
            self.resolved_models_dir,
            self.resolved_jobs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        self.resolved_db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
