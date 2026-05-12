from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source_query: str = ""


@dataclass
class Opportunity:
    opportunity: str
    opportunity_description: str
    location: str
    date_of_opportunity: str
    pay: str
    url: str
    source_query: str = ""
    pay_certainty: str = "unclear"  # confirmed_paid, likely_paid, unclear, unpaid
    relevance_notes: str = ""
    fit_score: int = 0
    warnings: list[str] = field(default_factory=list)

    def normalized_url(self) -> str:
        return self.url.strip().rstrip("/")
