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
    """A simple sanity check task — did today's ingestion actually produce rows?"""
    from db.database import SessionLocal
    from db.models import Price, NewsArticle
    from datetime import date

    session = SessionLocal()
    try:
        today_prices = session.query(Price).filter(Price.date >= date.today()).count()
        total_news = session.query(NewsArticle).count()

        if today_prices == 0:
            raise ValueError(
                "No price rows found for today — ingestion may have silently failed upstream."
            )

        # ---news check: sofw warning, since low/zero counts can be legitimate ---
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_news = (
            session.query(NewsArticle)
            .filter(NewsArticle.published_at >= cutoff)
            .count()
        )

        if recent_news == 0:
            print(
                f"WARNING: no news articles published in the last 24hrs "
                f"(total articles in DB: {total_news}). Could be a quiet news day"
            )
        else:
            print(
                f"news check: {recent_news} articles in the last 24hrs ({total_news} total)."
            )

        print(
            f"Data quality check passed: {today_prices} price rows today, {total_news} total news articles."
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
