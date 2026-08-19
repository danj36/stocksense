import pandas as pd
from sqlalchemy import select

from db.database import SessionLocal
from db.models import Price, NewsArticle

FEATURE_COLS = [
    "return_1d",
    "return_5d",
    "ma_ratio",
    "volatility_5d",
    "volume_change",
    "avg_sentiment",
]


def load_prices() -> pd.DataFrame:
    session = SessionLocal()
    try:
        rows = session.execute(select(Price)).scalars().all()
        return pd.DataFrame(
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
    finally:
        session.close()


def load_daily_sentiment() -> pd.DataFrame:
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
                {"date": r.published_at.date(), "sentiment_score": r.sentiment_score}
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


def _compute_ticker_features(g: pd.DataFrame) -> pd.DataFrame:
    """Rolling price-based features, computed per-ticker. Shared by training and serving."""
    g = g.sort_values("date").reset_index(drop=True)
    g["return_1d"] = g["close"].pct_change(1)
    g["return_5d"] = g["close"].pct_change(5)
    g["ma_5"] = g["close"].rolling(5).mean()
    g["ma_10"] = g["close"].rolling(10).mean()
    g["ma_ratio"] = g["ma_5"] / g["ma_10"]
    g["volatility_5d"] = g["return_1d"].rolling(5).std()
    g["volume_change"] = g["volume"].pct_change(1)
    return g


def _merge_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    sentiment_df = load_daily_sentiment()

    # Normalize both inputs to the same pandas datetime precision and resolution.
    df["date_only"] = (
        pd.to_datetime(df["date"], errors="coerce")
        .dt.normalize()
        .astype("datetime64[ns]")
    )
    sentiment_df["date"] = (
        pd.to_datetime(sentiment_df["date"], errors="coerce")
        .dt.normalize()
        .astype("datetime64[ns]")
    )

    df = df.merge(
        sentiment_df.rename(columns={"date": "date_only"}),
        on="date_only",
        how="left",
    )
    df = df.drop(columns=["date_only"])
    df["avg_sentiment"] = df["avg_sentiment"].fillna(0.0)
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    all_feats = []
    for ticker, g in df.groupby("ticker"):
        g = _compute_ticker_features(g)
        g["next_close"] = g["close"].shift(-1)

        # Compute target as float first so NaN survives the comparison —
        # comparing NaN > x evaluates to False, not NaN, so we must handle
        # the "no next day yet" case explicitly rather than relying on
        # the comparison itself to propagate missingness.
        g["target"] = (g["next_close"] > g["close"]).astype(float)
        g.loc[g["next_close"].isna(), "target"] = float("nan")

        all_feats.append(g)

    result = pd.concat(all_feats, ignore_index=True)
    result = _merge_sentiment(result)
    result = result.dropna(subset=FEATURE_COLS + ["target"])
    result["target"] = result["target"].astype(int)  # safe now — NaNs are already gone
    return result[["ticker", "date"] + FEATURE_COLS + ["target"]]


def build_latest_features(df: pd.DataFrame) -> pd.DataFrame:
    """SERVING features: the most recent row per ticker, no label needed —
    this is deliberately the row build_features() throws away."""
    all_feats = []
    for ticker, g in df.groupby("ticker"):
        g = _compute_ticker_features(g)
        all_feats.append(g)

    result = pd.concat(all_feats, ignore_index=True)
    result = _merge_sentiment(result)
    result = result.dropna(subset=FEATURE_COLS)
    result = result.sort_values("date").groupby("ticker").tail(1).reset_index(drop=True)
    return result[["ticker", "date"] + FEATURE_COLS]
