"""
Fetches recent business/market news headlines using NewsAPI
"""

import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL = "https://newsapi.org/v2/everything"


def fetch_news(query: str = "stock_market", page_size: int = 30) -> list[dict]:
    """
    Fetch recent news articles matching the query.
    Returns a list of simplified article dicts.
    """
    if not NEWS_API_KEY:
        logger.error("NEWS_API_KEY not set - check your .env file")
        return []

    params = {
        "q": query,
        "language": "en",
        "sortBY": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY,
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()  # raises an exception on 4xx/5xx
    except requests.exceptions.RequestException as e:
        logger.error(f"News API request failed: {e}")
        return []

    payload = response.json()
    articles = payload.get("articles", [])

    if not articles:
        logger.warning("No articles returned.")
        return []

    simplified = [
        {
            "source": a["source"]["name"],
            "title": a["title"],
            "description": a.get("description"),
            "url": a["url"],
            "published_at": a["publishedAt"],
        }
        for a in articles
    ]
    logger.info(f"Fetched {len(simplified)} articles.")
    return simplified


if __name__ == "__main__":
    articles = fetch_news()

    import json

    os.makedirs("data", exist_ok=True)
    filename = f"data/news_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2)
    logger.info(f"Saved to {filename}")
