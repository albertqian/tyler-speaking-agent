from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


# Target regions for geographic search bias and scoring.
# Add or remove states here and both queries and scoring will follow.
# Each entry maps a state to its key metros/sub-regions Tyler cares about.
TARGET_REGIONS: dict[str, list[str]] = {
    "California": ["San Luis Obispo", "Central Coast", "SLO", "Bay Area", "Los Angeles", "San Diego"],
    "Nevada": ["Las Vegas", "Reno"],
    "Arizona": ["Phoenix", "Scottsdale", "Tucson"],
    "Oregon": ["Portland"],
    "Washington": ["Seattle", "Bellevue"],
    "Hawaii": ["Honolulu", "Maui"],
}

# Umbrella regional phrases worth searching once at the multi-state level.
REGIONAL_UMBRELLAS: list[str] = ["West Coast", "Pacific Northwest", "Western US"]


# Non-geographic queries — these run regardless of region.
# Strategy: keep recall high by using at most 2 quoted phrases per query
# and NOT requiring the word "paid" in the query string. Page authors
# rarely write "paid speaker" verbatim — they write "honorarium",
# "speaker fee", "$X stipend", or just nothing (you negotiate later).
# Requiring "paid" in the query filters out the very listings we want.
# Claude's extraction step determines pay status from the page content.
_BASE_QUERIES: list[str] = [
    '"call for speakers" "women entrepreneurs"',
    '"speaker application" "women in business"',
    '"keynote speaker" "women leadership"',
    '"conference speaker proposal" "female founders"',
    '"workshop facilitator" "women entrepreneurs"',
    '"speaker proposal" "small business" honorarium',
    '"virtual summit" "women entrepreneurs"',
    '"retreat facilitator" "women leaders"',
]


def _build_default_queries() -> list[str]:
    """Generate the default query list from TARGET_REGIONS + base queries.

    Strategy: keep query count bounded. One query per state (state-level),
    one query per top metro (city-level), plus umbrella regional queries.
    Heavier query counts blow up the per-week Claude extraction cost.
    """
    queries = list(_BASE_QUERIES)

    # One state-level query per state. Two quoted phrases max.
    for state in TARGET_REGIONS:
        queries.append(f'"{state}" "women" speaker application')

    # One city-level query per top metro (first city in each state's list).
    # Two quoted phrases max.
    for state, cities in TARGET_REGIONS.items():
        if not cities:
            continue
        top_metro = cities[0]
        queries.append(f'"{top_metro}" "call for speakers" women')

    # Umbrella queries. Two quoted phrases max.
    for umbrella in REGIONAL_UMBRELLAS:
        queries.append(f'"{umbrella}" "women entrepreneurs" speaker')

    return queries


DEFAULT_QUERIES: list[str] = _build_default_queries()


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
