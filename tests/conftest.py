import pandas as pd
import pytest


@pytest.fixture
def sample_price_df():
    """Two tickers, enough rows for rolling-window features to be computable."""
    dates = pd.date_range("2026-01-01", periods=15, freq="D")
    rows = []
    for ticker, base_price in [("AAPL", 150), ("MSFT", 300)]:
        for i, date in enumerate(dates):
            rows.append(
                {
                    "ticker": ticker,
                    "date": date,
                    "open": base_price + i,
                    "high": base_price + i + 2,
                    "low": base_price + i - 2,
                    "close": base_price + i + 1,
                    "volume": 1_000_000 + i * 1000,
                }
            )
    return pd.DataFrame(rows)
