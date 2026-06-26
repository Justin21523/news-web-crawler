from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.schemas.llm import LLMHealthResponse


@dataclass
class LLMSummary:
    text: str
    bullets: list[str]
    provider: str


class LLMService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def health(self) -> LLMHealthResponse:
        if not self.settings.llm_enabled:
            return LLMHealthResponse(
                enabled=False,
                reachable=False,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                detail="NEWS_LLM_ENABLED is false.",
            )
        try:
            self._request("/models", method="GET")
            return LLMHealthResponse(
                enabled=True,
                reachable=True,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                detail="llama.cpp endpoint is reachable.",
            )
        except Exception as exc:
            return LLMHealthResponse(
                enabled=True,
                reachable=False,
                base_url=self.settings.llm_base_url,
                model=self.settings.llm_model,
                detail=str(exc),
            )

    def summarize(self, corpus: str, *, instruction: str, max_tokens: int = 512) -> LLMSummary | None:
        if not self.settings.llm_enabled:
            return None
        content = corpus.strip()
        if not content:
            return None
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise news intelligence analyst. Return useful Chinese bullets unless the source text is English.",
                },
                {"role": "user", "content": f"{instruction}\n\n{content[:24000]}"},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        data = self._request("/chat/completions", payload=payload)
        text = str(data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        if not text:
            return None
        bullets = [line.strip(" -•\t") for line in text.splitlines() if line.strip(" -•\t")]
        return LLMSummary(text=text, bullets=bullets or [text], provider="llama.cpp")

    def _request(self, path: str, *, payload: dict | None = None, method: str = "POST") -> dict:
        url = f"{self.settings.llm_base_url.rstrip('/')}/{path.lstrip('/')}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.llm_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"llama.cpp returned HTTP {exc.code}: {detail[:240]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"llama.cpp is not reachable: {exc.reason}") from exc
