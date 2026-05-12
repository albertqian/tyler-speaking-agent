from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


DEFAULT_QUERIES: list[str] = [
    '"call for speakers" "women entrepreneurs" "paid speaker"',
    '"speaker application" "women in business" honorarium',
    '"keynote speaker" "women leadership" paid',
    '"conference speaker proposal" "female founders" honorarium',
    '"workshop facilitator" "women entrepreneurs" paid',
    '"women leadership conference" "call for speakers" California',
    '"small business conference" "speaker proposal" paid',
    '"San Luis Obispo" speaker "women entrepreneurs"',
    '"Central Coast" "call for speakers"',
    '"California" "women in business" "speaker application"',
    '"Bay Area" "female founders" "speaker application"',
    '"Los Angeles" "women leadership" "call for speakers"',
    '"virtual summit" "women entrepreneurs" "call for speakers"',
    '"retreat facilitator" "women leaders" paid',
]


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    anthropic_model: str
    search_provider: str
    serper_api_key: str
    gmail_user: str
    gmail_app_password: str
    to_email: str
    from_name: str
    min_score: int
    max_results_per_query: int
    dry_run: bool
    queries: List[str]


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_settings() -> Settings:
    custom_queries = os.getenv("SEARCH_QUERIES", "").strip()
    queries = (
        [q.strip() for q in custom_queries.split("||") if q.strip()]
        if custom_queries
        else DEFAULT_QUERIES
    )

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest").strip(),
        search_provider=os.getenv("SEARCH_PROVIDER", "serper").strip().lower(),
        serper_api_key=os.getenv("SERPER_API_KEY", "").strip(),
        gmail_user=os.getenv("GMAIL_USER", "").strip(),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", "").strip(),
        to_email=os.getenv("TO_EMAIL", "").strip(),
        from_name=os.getenv("FROM_NAME", "Speaking Gig Agent").strip(),
        min_score=_get_int("MIN_SCORE", 5),
        max_results_per_query=_get_int("MAX_RESULTS_PER_QUERY", 6),
        dry_run=_get_bool("DRY_RUN", False),
        queries=queries,
    )


def validate_settings(settings: Settings) -> None:
    missing = []
    if not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")

    if settings.search_provider == "serper" and not settings.serper_api_key:
        missing.append("SERPER_API_KEY")

        if settings.search_provider != "serper":
        raise RuntimeError(
            f"Unsupported SEARCH_PROVIDER={settings.search_provider!r}. "
            "This repo version is configured for SEARCH_PROVIDER=serper."
        )

    if not settings.dry_run:
        if not settings.gmail_user:
            missing.append("GMAIL_USER")
        if not settings.gmail_app_password:
            missing.append("GMAIL_APP_PASSWORD")
        if not settings.to_email:
            missing.append("TO_EMAIL")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
