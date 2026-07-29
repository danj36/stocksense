"""
trains a baseline logistic regression on the up/down classification task,
using a time-based (not random) train/test split.
"""

import logging

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    classification_report,
)
from sklearn.preprocessing import StandardScaler

from ml.features import load_prices, build_features

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "return_1d",
    "return_5d",
    "ma_ratio",
    "volatility_5d",
    "volume_change",
    "avg_sentiment",
]


def time_based_split(df: pd.DataFrame, test_size: float = 0.2):
    """
    split by date, not randomly. the last 'test_size' fraction of dates (across all tickers)
    becomes the test set - this simulates genuinely predicting the future, rather than
    "leaking" nearby days into training"""
    df = df.sort_values("date")
    cutoff_idx = int(len(df) * (1 - test_size))
    cutoff_date = df.iloc[cutoff_idx]["date"]

    train = df[df["date"] < cutoff_date]
    test = df[df["date"] >= cutoff_date]
    return train, test


def train_and_evaluate():
    logger.info("Loading price data...")
    raw = load_prices()
    logger.info(f"Loaded {len(raw)} raw price rows.")

    features_df = build_features(raw)
    logger.info(f"Built {len(features_df)} labeled feature rows.")

    train_df, test_df = time_based_split(features_df, test_size=0.2)
    logger.info(f"Train: {len(train_df)} rows, Test: {len(test_df)} rows.")

    X_train, y_train = train_df[FEATURE_COLS], train_df["target"]
    X_test, y_test = test_df[FEATURE_COLS], test_df["target"]

    # scale features - logistic regression is sensitive to feature magnitude differences
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_scaled, y_train)

    preds = model.predict(X_test_scaled)

    # --- Honest evaluation, including a naive baseline for comparison ---
    baseline_preds = [1] * len(y_test)  # naive baseline: "always predict up"

    logger.info("=== Model performance ===")
    logger.info(f"Accuracy:  {accuracy_score(y_test, preds):.3f}")
    logger.info(f"Precision: {precision_score(y_test, preds):.3f}")
    logger.info(f"Recall:    {recall_score(y_test, preds):.3f}")

    logger.info("=== Naive baseline ('always predict up') ===")
    logger.info(f"Baseline accuracy: {accuracy_score(y_test, baseline_preds):.3f}")

    logger.info("\n" + classification_report(y_test, preds))

    import os

    os.makedirs("ml/artifacts", exist_ok=True)
    joblib.dump(model, "ml/artifacts/baseline_model.pkl")
    joblib.dump(scaler, "ml/artifacts/scaler.pkl")
    logger.info("Saved model and scaler to ml/artifacts/")


if __name__ == "__main__":
    train_and_evaluate()
