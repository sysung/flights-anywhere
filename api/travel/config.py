from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AIConfig:
    google_api_key: str | None
    gemini_model: str = "gemini-3.5-flash"


def load_ai_config() -> AIConfig:
    return AIConfig(
        google_api_key=os.environ.get("GOOGLE_CLOUD_API_KEY") or None,
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
    )

