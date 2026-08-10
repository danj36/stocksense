"""
Scores news articles for market sentiment using Gemini 2.5 Flash-Lite.
Designed to run daily, only scoring articles that haven't been scored yet.
"""

import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel


load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash-lite"

# stay comfortably under the 15 RPM free-tier limit for this model
SECONDS_BETWEEN_CALLS = 5


class SentimentResult(BaseModel):
    sentiment_score: float  # -1.0 (bearish) to 1.0 (busllish), 0.0 = neutral
    market_relevant: bool  # is this actually about broad market conditions?


def _get_client() -> genai.Client:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set - check your .env file")
    return genai.Client(api_key=GEMINI_API_KEY)


def score_article(
    client: genai.Client, title: str, description: str | None
) -> SentimentResult | None:
    prompt = (
        "You are a financial news analyst. Rate this news item's likely sentiment toward the overall US stock market, from -1.0 (very negative/bearish) to 1.0 (very positive/bullish) with 0.0 meanining neutral or unclear."
        "Also flag whether it's actually relevant to broad market conditions (as opposed to unrelated news that happened to match a search).\n\n"
        f"Title: {title}\n"
        f"Description: {description or '(none provided)'}"
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SentimentResult,
                http_options=types.HttpOptions(
                    timeout=30_000
                ),  # 30 seconds, in milliseconds
            ),
        )
        return SentimentResult.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"Gemini scoring failed for '{title[:50]}...': {e}")
        return None


def score_unscored_articles() -> int:
    """Finds articles with no sentiment score yet, scores them, saves results."""
    from db.database import SessionLocal
    from db.models import NewsArticle

    client = _get_client()
    session = SessionLocal()
    scored_count = 0

    try:
        unscored = (
            session.query(NewsArticle)
            .filter(NewsArticle.sentiment_score.is_(None))
            .all()
        )
        logger.info(f"Found {len(unscored)} unscored articles.")

        for i, article in enumerate(unscored, start=1):
            result = score_article(client, article.title, article.description)
            if result is not None:
                article.sentiment_score = result.sentiment_score
                article.market_relevant = result.market_relevant
                scored_count += 1
                logger.info(
                    f"[{i}/{len(unscored)}] Scored article id={article.id}: {result.sentiment_score:.2f}"
                )
            else:
                logger.warning(
                    f"[{i}/{len(unscored)}] Skipping article id={article.id}, will retry next run."
                )

            time.sleep(SECONDS_BETWEEN_CALLS)

        session.commit()
        logger.info(f"Scored {scored_count}/{len(unscored)} articles successfully.")
        return scored_count
    except Exception as e:
        session.rollback()
        logger.error(f"Sentiment scoring run failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    score_unscored_articles()
