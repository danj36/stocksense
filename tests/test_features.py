from ml.features import _compute_ticker_features, build_features, build_latest_features


def test_compute_ticker_features_produces_expected_columns(sample_price_df):
    g = sample_price_df[sample_price_df["ticker"] == "AAPL"]
    result = _compute_ticker_features(g)
    for col in ["return_1d", "return_5d", "ma_ratio", "volatility_5d", "volume_change"]:
        assert col in result.columns


def test_build_features_drops_last_row_per_ticker(sample_price_df, monkeypatch):
    """The most recent row per ticker has no next-day label — build_features()
    must drop it. This is the exact rule that prevents lookahead bias."""
    monkeypatch.setattr(
        "ml.features.load_daily_sentiment",
        lambda: __import__("pandas").DataFrame(columns=["date", "avg_sentiment"]),
    )

    result = build_features(sample_price_df)
    max_date_in_input = sample_price_df["date"].max()
    assert max_date_in_input not in result["date"].values


def test_build_latest_features_keeps_only_most_recent_row(sample_price_df, monkeypatch):
    """The inverse of build_features(): serving needs exactly the row training discards."""
    monkeypatch.setattr(
        "ml.features.load_daily_sentiment",
        lambda: __import__("pandas").DataFrame(columns=["date", "avg_sentiment"]),
    )

    result = build_latest_features(sample_price_df)
    assert (
        len(result) == sample_price_df["ticker"].nunique()
    )  # exactly one row per ticker
    assert "target" not in result.columns  # serving features never include a label
