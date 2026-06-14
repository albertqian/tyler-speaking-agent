from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import TARGET_REGIONS, REGIONAL_UMBRELLAS
from .models import Opportunity


# Build geographic positive terms from the configured target regions.
# Lowercased once at import time so scoring stays O(n) per opportunity.
_GEO_TERMS: list[str] = []
for _state, _cities in TARGET_REGIONS.items():
    _GEO_TERMS.append(_state.lower())
    _GEO_TERMS.extend(c.lower() for c in _cities)
_GEO_TERMS.extend(u.lower() for u in REGIONAL_UMBRELLAS)


POSITIVE_TERMS = [
    "paid",
    "honorarium",
    "speaker fee",
    "keynote",
    "workshop",
    "facilitator",
    "retreat",
    "women",
    "female founder",
    "founder",
    "entrepreneur",
    "leadership",
    "mentorship",
    "professional development",
    "community",
    "virtual",
    "hybrid",
    *_GEO_TERMS,
]

NEGATIVE_TERMS = [
    "unpaid",
    "volunteer only",
    "exposure",
    "no compensation",
    "student only",
    "past event",
    "closed",
    "deadline passed",
]


def score_opportunity(opp: Opportunity) -> Opportunity:
    text = " ".join(
        [
            opp.opportunity,
            opp.opportunity_description,
            opp.location,
            opp.date_of_opportunity,
            opp.pay,
            opp.pay_certainty,
            opp.relevance_notes,
            " ".join(opp.warnings),
        ]
    ).lower()

    score = 0

    if opp.pay_certainty == "confirmed_paid":
        score += 4
    elif opp.pay_certainty == "likely_paid":
        score += 2
    elif opp.pay_certainty == "unclear":
        score += 0
    elif opp.pay_certainty == "unpaid":
        score -= 4

    if re.search(r"\$\s?\d+|\d+\s?(usd|dollars)", text):
        score += 2

    for term in POSITIVE_TERMS:
        if term in text:
            score += 1

    for term in NEGATIVE_TERMS:
        if term in text:
            score -= 3

    if any(term in text for term in ["call for speakers", "speaker application", "proposal", "cfp"]):
        score += 2

    if opp.date_of_opportunity.lower() in {"unknown", "n/a", ""}:
        score -= 1
    if opp.location.lower() in {"unknown", "n/a", ""}:
        score -= 1

    domain = urlparse(opp.url).netloc.lower()
    if "eventbrite" in domain and opp.pay_certainty == "unclear":
        score -= 1

    opp.fit_score = max(0, min(score, 12))
    return opp


def filter_and_sort(opportunities: list[Opportunity], min_score: int) -> list[Opportunity]:
    scored = [score_opportunity(opp) for opp in opportunities]
    filtered = [opp for opp in scored if opp.fit_score >= min_score and opp.pay_certainty != "unpaid"]
    return sorted(filtered, key=lambda o: (o.fit_score, o.pay_certainty == "confirmed_paid"), reverse=True)


def dedupe_opportunities(opportunities: list[Opportunity]) -> list[Opportunity]:
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    deduped: list[Opportunity] = []

    for opp in opportunities:
        url_key = opp.normalized_url().lower()
        name_key = re.sub(r"\W+", "", opp.opportunity.lower())

        if url_key in seen_urls or name_key in seen_names:
            continue

        seen_urls.add(url_key)
        seen_names.add(name_key)
        deduped.append(opp)

    return deduped
