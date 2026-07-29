"""
Builds a feature matrix + binary labels (next-day up/down) from price history.
"""

import pandas as pd
from sqlalchemy import select

from db.database import SessionLocal
from db.models import Price, NewsArticle


def load_prices() -> pd.DataFrame:
    session = SessionLocal()
    try:
        rows = session.execute(select(Price)).scalars().all()
        df = pd.DataFrame(
            [
                {
                    "ticker": r.ticker,
                    "date": r.date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                }
                for r in rows
            ]
        )
        return df
    finally:
        session.close()


def load_daily_sentiment() -> pd.DataFrame:
    """market-wide average sentiment per calendar day, from all scored articles."""

    session = SessionLocal()
    try:
        rows = (
            session.query(NewsArticle)
            .filter(NewsArticle.sentiment_score.isnot(None))
            .filter(NewsArticle.market_relevant.is_(True))
            .all()
        )
        df = pd.DataFrame(
            [
                {
                    "date": r.published_at.date(),
                    "sentiment_score": r.sentiment_score,
                }
                for r in rows
            ]
        )

        if df.empty:
            return pd.DataFrame(columns=["date", "avg_sentiment"])

        daily = df.groupby("date")["sentiment_score"].mean().reset_index()
        daily.columns = ["date", "avg_sentiment"]
        return daily
    finally:
        session.close()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each ticker independently, build features from past price behavior and a label for whether the NEXT day's close is higher than today's"""
    all_feats = []

    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("date").reset_index(drop=True)

        g["return_1d"] = g["close"].pct_change(1)
        g["return_5d"] = g["close"].pct_change(5)
        g["ma_5"] = g["close"].rolling(5).mean()
        g["ma_10"] = g["close"].rolling(10).mean()
        g["ma_ratio"] = g["ma_5"] / g["ma_10"]
        g["volatility_5d"] = g["return_1d"].rolling(5).std()
        g["volume_change"] = g["volume"].pct_change(1)

        # label: did the NEXT day close higher than today? shift(-1) looks forward.
        g["next_close"] = g["close"].shift(-1)
        g["target"] = (g["next_close"] > g["close"]).astype(int)

        all_feats.append(g)

    result = pd.concat(all_feats, ignore_index=True)

    # merge in market-wide daily sentiment (same value applied across all tickers for that date)
    sentiment_df = load_daily_sentiment()
    result["date_only"] = pd.to_datetime(result["date"]).dt.normalize()
    sentiment_df["date_only"] = pd.to_datetime(sentiment_df["date"]).dt.normalize()
    result = result.merge(
        sentiment_df[["date_only", "avg_sentiment"]],
        on="date_only",
        how="left",
    )
    result = result.drop(columns=["date_only"])

    # missing sentiment (days with no scored news) default to neutral, not dropped
    result["avg_sentiment"] = result["avg_sentiment"].fillna(0.0)

    # drop rows with NaNs from rolling windows (start of each ticker's history)
    # and the very last row per ticker (no next_day label exists yet)
    feature_cols = [
        "return_1d",
        "return_5d",
        "ma_ratio",
        "volatility_5d",
        "volume_change",
        "avg_sentiment",
    ]
    result = result.dropna(subset=feature_cols + ["target"])

    return result[["ticker", "date"] + feature_cols + ["target"]]
