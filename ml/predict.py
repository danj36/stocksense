"""
Loads the trained baseline model and produces a live prediction
for a single ticker, using its most recent available data.
"""

import joblib

from ml.features import load_prices, build_latest_features, FEATURE_COLS

MODEL_PATH = "ml/artifacts/baseline_model.pkl"
SCALER_PATH = "ml/artifacts/scaler.pkl"


def predict_latest(ticker: str) -> dict | None:
    raw = load_prices()
    raw = raw[raw["ticker"] == ticker]
    if raw.empty:
        return None

    latest = build_latest_features(raw)
    if latest.empty:
        return None

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    X = latest[FEATURE_COLS]
    X_scaled = scaler.transform(X)
    proba_up = model.predict_proba(X_scaled)[0][1]

    row = latest.iloc[0]
    return {
        "ticker": ticker,
        "as_of_date": row["date"],
        "prediction": "up" if proba_up >= 0.5 else "down",
        "probability_up": round(float(proba_up), 4),
    }
