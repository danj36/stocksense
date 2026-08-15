from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def run_fetch_prices():
    from ingestion.fetch_prices import fetch_prices, TICKERS
    from db.repository import upsert_prices

    df = fetch_prices(TICKERS)
    if df.empty:
        raise ValueError("No price data fetched — failing task so Airflow flags it.")
    upsert_prices(df)


def run_fetch_news():
    from ingestion.fetch_news import fetch_news
    from db.repository import upsert_news

    articles = fetch_news()
    upsert_news(articles)


def run_score_sentiment():
    from ml.sentiment import score_unscored_articles

    score_unscored_articles()


def check_data_quality():
    from datetime import date, datetime, timedelta

    from db.database import SessionLocal
    from db.models import Price, NewsArticle

    session = SessionLocal()
    try:
        # Check for recent price data (last 4 days) rather than exact "today" —
        # markets don't trade on weekends/holidays, so "today" can legitimately have zero rows.
        recent_cutoff = date.today() - timedelta(days=4)
        recent_prices = session.query(Price).filter(Price.date >= recent_cutoff).count()
        if recent_prices == 0:
            raise ValueError(
                f"No price rows found in the last 4 days (since {recent_cutoff}) — "
                f"ingestion may have silently failed upstream."
            )

        # --- News check, unchanged ---
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_news = (
            session.query(NewsArticle)
            .filter(NewsArticle.published_at >= cutoff)
            .count()
        )
        total_news = session.query(NewsArticle).count()

        if recent_news == 0:
            print(
                f"WARNING: no news articles published in the last 24 hours "
                f"(total articles in DB: {total_news}). Could be a quiet news day, "
                f"a rate limit, or a query issue — worth a manual look if this repeats."
            )
        else:
            print(
                f"News check: {recent_news} articles in the last 24h ({total_news} total)."
            )

        print(
            f"Data quality check passed: {recent_prices} price rows in the last 4 days."
        )

    finally:
        session.close()


default_args = {
    "owner": "stocksense",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="daily_ingestion",
    default_args=default_args,
    description="Daily ingestion of S&P 500 prices and market news",
    schedule="0 6 * * *",  # every day at 6:00 AM
    start_date=datetime(2026, 7, 1),
    catchup=False,  # don't backfill every missed day since start_date
    tags=["stocksense", "ingestion"],
) as dag:
    fetch_prices_task = PythonOperator(
        task_id="fetch_prices",
        python_callable=run_fetch_prices,
    )

    fetch_news_task = PythonOperator(
        task_id="fetch_news",
        python_callable=run_fetch_news,
    )

    score_sentiment_task = PythonOperator(
        task_id="score_sentiment",
        python_callable=run_score_sentiment,
    )

    quality_check_task = PythonOperator(
        task_id="data_quality_check",
        python_callable=check_data_quality,
    )

    fetch_news_task >> score_sentiment_task
    [fetch_prices_task, score_sentiment_task] >> quality_check_task
