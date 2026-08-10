"""
Thin wrapper around the FastAPI backend. Keeps HTTP details out of the
Streamlit page code itself.
"""

import requests
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_prices(ticker: str, limit: int = 60) -> list[dict]:
    resp = requests.get(
        f"{API_BASE_URL}/prices/{ticker}", params={"limit": limit}, timeout=10
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json()


def get_latest_news(limit: int = 15) -> list[dict]:
    resp = requests.get(
        f"{API_BASE_URL}/news/latest", params={"limit": limit}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def get_prediction(ticker: str) -> dict | None:
    resp = requests.get(f"{API_BASE_URL}/predictions/{ticker}", timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()
