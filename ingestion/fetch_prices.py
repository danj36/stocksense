"""
Feteches daily OHLCV price data for a set of tickers using yfinance
"""

import logging
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# starter set - index + handful of large caps. Expand later
TICKERS = [
    "^GSPC",  # S&P500 index
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "META",
    "TSLA",
    "JPM",
    "V",
    "UNH",
]


def fetch_prices(tickers: list[str], period: str = "5d") -> pd.DataFrame:
    """
    Fetch recent data for given tickets.
    Returns a tidy DataFrame with one row per (ticker, date)
    """

    all_rows = []
    for ticker in tickers:
        try:
            logger.info(f"Fetching {ticker}...")
            data = yf.Ticker(ticker).history(period=period)

            if data.empty:
                logger.warning(f"No data returned for {ticker}, skipping.")
                continue  # skips the code

            data = data.reset_index()
            data["ticker"] = ticker
            all_rows.append(data)
        except Exception as e:
            # we log and continue - one bad ticker shouldn't kill the whole run
            logger.error(f"Failed to fetch {ticker}: {e}")
            continue

    if not all_rows:
        logger.error("No price data fetched for any ticker.")
        return pd.DataFrame()

    combined = pd.concat(all_rows, ignore_index=True)
    combined.columns = combined.columns.str.lower()

    # combined = combined.rename(columns = {
    #     "Date": "date", "Open": "open", "High": "high",
    #     "Low":"low", "Close":"close", "Volume":"volume"
    # })

    return combined[["ticker", "date", "open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    from db.repository import upsert_prices

    df = fetch_prices(TICKERS)
    logger.info(f"Fetched {len(df)} rows across {df['ticker'].nunique()} tickers.")
    upsert_prices(df)

    # temporary: save to CSV until Phase 3 wires up the database.
    # import os

    # os.makedirs("data", exist_ok=True)
    # filename = f"data/prices_{datetime.now().strftime('%Y%m%d')}.csv"
    # df.to_csv(filename, index=False)
    # logger.info(f"Saved to {filename}")
