from __future__ import annotations

import json
import logging
import re
from typing import Any

from anthropic import Anthropic

from .fetch import build_candidate_context
from .models import Opportunity, SearchResult

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You extract paid speaking opportunities from web search results.

You are helping identify opportunities relevant to Tyler Skinner, Founder of Women Making Waves in San Luis Obispo County.

Prioritize:
- Paid speaking gigs
- Keynotes
- Workshop facilitation
- Retreat facilitation
- Panels with honorariums
- Women leadership, women entrepreneurs, female founders
- Community building, mentorship, professional development
- California, Central Coast, Bay Area, Los Angeles, or virtual opportunities

Reject or mark low confidence:
- Unpaid exposure-only opportunities
- Generic event pages with no speaker application
- Past events with no open application
- Student-only, academic-only, or irrelevant industry events unless clearly aligned
- Sponsorship opportunities that are not speaking opportunities

Return JSON only. No Markdown. No prose outside JSON.
"""


USER_PROMPT_TEMPLATE = """Analyze this candidate page and determine whether it contains a relevant speaking opportunity.

Return JSON using this exact shape:

{{
  "is_opportunity": true,
  "opportunity": "Name of event, organization, or speaking opportunity",
  "opportunity_description": "Short practical description of why this may fit Tyler / Women Making Waves",
  "location": "City/state, virtual, hybrid, or unknown",
  "date_of_opportunity": "Event date, application deadline, or unknown",
  "pay": "Exact compensation if listed; otherwise Paid amount not listed, Likely paid, Unknown, or Unpaid",
  "pay_certainty": "confirmed_paid | likely_paid | unclear | unpaid",
  "relevance_notes": "Brief notes on fit and any caveats",
  "warnings": ["Specific caveats, if any"]
}}

If this is not a relevant opportunity, return:

{{
  "is_opportunity": false,
  "reason": "brief reason"
}}

Candidate page:

{context}
"""


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON object extraction from model output."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def anthropic_extract_opportunity(
    client: Anthropic,
    model: str,
    result: SearchResult,
    page_text: str,
) -> Opportunity | None:
    context = build_candidate_context(result, page_text)
    user_prompt = USER_PROMPT_TEMPLATE.format(context=context)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=900,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        logger.exception("Anthropic call failed for %s: %s", result.url, exc)
        return None

    raw_text_parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            raw_text_parts.append(block.text)

    raw_text = "\n".join(raw_text_parts).strip()
    try:
        data = extract_json(raw_text)
    except Exception as exc:
        logger.warning("Failed to parse JSON for %s: %s | output=%r", result.url, exc, raw_text)
        return None

    if not data.get("is_opportunity"):
        return None

    return Opportunity(
        opportunity=str(data.get("opportunity", result.title)).strip() or result.title,
        opportunity_description=str(data.get("opportunity_description", "")).strip(),
        location=str(data.get("location", "Unknown")).strip() or "Unknown",
        date_of_opportunity=str(data.get("date_of_opportunity", "Unknown")).strip() or "Unknown",
        pay=str(data.get("pay", "Unknown")).strip() or "Unknown",
        url=result.url,
        source_query=result.source_query,
        pay_certainty=str(data.get("pay_certainty", "unclear")).strip() or "unclear",
        relevance_notes=str(data.get("relevance_notes", "")).strip(),
        warnings=list(data.get("warnings", [])) if isinstance(data.get("warnings", []), list) else [],
    )
