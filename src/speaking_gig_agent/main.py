from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from anthropic import Anthropic

from .config import load_settings, validate_settings
from .emailer import build_html_email, build_text_email, send_email
from .extract import anthropic_extract_opportunity
from .fetch import fetch_page_text
from .score import dedupe_opportunities, filter_and_sort
from .search import search_all
from .utils import configure_logging

logger = logging.getLogger(__name__)


def run() -> None:
    configure_logging()
    settings = load_settings()
    validate_settings(settings)

    logger.info("Starting speaking gig search")
    logger.info("Dry run: %s", settings.dry_run)
    logger.info("Search provider: %s", settings.search_provider)
    logger.info("Minimum score: %s", settings.min_score)

    search_results = search_all(
        queries=settings.queries,
        provider=settings.search_provider,
        serper_api_key=settings.serper_api_key,
        max_results_per_query=settings.max_results_per_query,
    )

    logger.info("Found %d deduped search results", len(search_results))

    client = Anthropic(api_key=settings.anthropic_api_key)
    opportunities = []

    for index, result in enumerate(search_results, 1):
        logger.info("[%d/%d] Evaluating: %s", index, len(search_results), result.url)
        page_text = fetch_page_text(result.url)

        if not page_text:
            page_text = "Page could not be fetched. Use title and search snippet only."

        opp = anthropic_extract_opportunity(
            client=client,
            model=settings.anthropic_model,
            result=result,
            page_text=page_text,
        )
        if opp:
            logger.info("Opportunity found: %s", opp.opportunity)
            opportunities.append(opp)

    opportunities = dedupe_opportunities(opportunities)
    opportunities = filter_and_sort(opportunities, min_score=settings.min_score)

    logger.info("Final opportunity count after filtering: %d", len(opportunities))

    today = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    subject = f"Weekly Paid Speaking Opportunities for Tyler Skinner - {today}"

    html_body = build_html_email(opportunities)
    text_body = build_text_email(opportunities)

    if settings.dry_run:
        print("\n=== DRY RUN EMAIL SUBJECT ===")
        print(subject)
        print("\n=== DRY RUN TEXT EMAIL ===")
        print(text_body)
        print("\n=== DRY RUN HTML EMAIL ===")
        print(html_body)
        return

    send_email(
        gmail_user=settings.gmail_user,
        gmail_app_password=settings.gmail_app_password,
        to_email=settings.to_email,
        from_name=settings.from_name,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )

    logger.info("Email sent to %s", settings.to_email)


if __name__ == "__main__":
    run()
