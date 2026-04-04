from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    provider: str
    model: str
    search_provider: str
    max_sources: int
    output_dir: Path
    enable_image_consul: bool
    image_model: str
    image_count: int
    image_size: str
    article_min_words: int
    article_max_words: int
    senate_reject_score_threshold: float
    senate_max_rework_rounds: int

    @staticmethod
    def load() -> "Settings":
        # Force .env values to override inherited shell variables
        # so runtime behavior is deterministic for each run.
        load_dotenv(override=True)
        provider = os.getenv("ROMA_PROVIDER", "mock").strip().lower()
        model = os.getenv("ROMA_MODEL", "gpt-4o-mini").strip()
        search_provider = os.getenv("ROMA_SEARCH_PROVIDER", "tavily").strip().lower()
        max_sources = int(os.getenv("ROMA_MAX_SOURCES", "8"))
        output_dir = Path(os.getenv("ROMA_OUTPUT_DIR", "output"))
        enable_image_consul = os.getenv("ROMA_ENABLE_IMAGE_CONSUL", "false").strip().lower() in {"1", "true", "yes", "on"}
        image_model = os.getenv("ROMA_IMAGE_MODEL", "gpt-image-1").strip()
        image_count = int(os.getenv("ROMA_IMAGE_COUNT", "2"))
        image_size = os.getenv("ROMA_IMAGE_SIZE", "256x256").strip()
        article_min_words = int(os.getenv("ROMA_ARTICLE_MIN_WORDS", "1200"))
        article_max_words = int(os.getenv("ROMA_ARTICLE_MAX_WORDS", "1800"))
        senate_reject_score_threshold = float(os.getenv("ROMA_SENATE_REJECT_SCORE_THRESHOLD", "80"))
        senate_max_rework_rounds = int(os.getenv("ROMA_SENATE_MAX_REWORK_ROUNDS", "2"))
        return Settings(
            provider=provider,
            model=model,
            search_provider=search_provider,
            max_sources=max_sources,
            output_dir=output_dir,
            enable_image_consul=enable_image_consul,
            image_model=image_model,
            image_count=image_count,
            image_size=image_size,
            article_min_words=article_min_words,
            article_max_words=article_max_words,
            senate_reject_score_threshold=senate_reject_score_threshold,
            senate_max_rework_rounds=senate_max_rework_rounds,
        )

