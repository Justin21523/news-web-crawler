from __future__ import annotations

from pydantic import BaseModel


class LLMHealthResponse(BaseModel):
    enabled: bool
    reachable: bool
    base_url: str
    model: str
    provider: str = "llama.cpp"
    detail: str = ""
