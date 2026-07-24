import logging
from sqlalchemy.dialects.postgresql import insert

from db.database import SessionLocal
from db.models import Price, NewsArticle

logger = logging.getLogger(__name__)


def upsert_prices(df) -> int:
    """insert price rows, updating ohlcv values if (ticker, date) already exists."""
    if df.empty:
        logger.warning("No price rows to upsert.")
        return 0

    session = SessionLocal()
    try:
        records = df.to_dict(orient="records")
        for r in records:
            stmt = insert(Price).values(**r)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            session.execute(stmt)
        session.commit()
        logger.info(f"Upserted {len(records)} price rows.")
        return len(records)
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to upsert prices: {e}")
        raise
    finally:
        session.close()


def upsert_news(articles: list[dict]) -> int:
    """Insert news articles, skipping ones already stored (matched by URL)"""
    if not articles:
        logger.warning("No news articles to upsert")
        return 0
    session = SessionLocal()
    try:
        inserted = 0
        for a in articles:
            stmt = insert(NewsArticle).values(**a)
            stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
            result = session.execute(stmt)
            inserted += result.rowcount
        session.commit()
        logger.info(f"Inserted {inserted} new articles (skipped duplicates)")
        return inserted
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to upsert news: {e}")
        raise
    finally:
        session.close()
