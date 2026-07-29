"""
One-time (or occasional) pull of longer price history for model training.
Separate from daily incremental ingestion, which only needs the last few days.
"""

import logging
import yfinance as yf

from ingestion.fetch_prices import TICKERS
from db.repository import upsert_prices

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def backfill(period: str = "2y") -> None:
    for ticker in TICKERS:
        try:
            logger.info(f"Backfilling {ticker} ({period})...")
            data = yf.Ticker(ticker).history(period=period)
            if data.empty:
                logger.warning(f"No history for {ticker}, skipping.")
                continue

            data = data.reset_index()
            data["ticker"] = ticker
            data.columns = data.columns.str.lower()
            df = data[["ticker", "date", "open", "high", "low", "close", "volume"]]
            upsert_prices(df)

        except Exception as e:
            logger.error(f"Backfill failed for {ticker}: {e}")
            continue


if __name__ == "__main__":
    backfill(period="2y")
