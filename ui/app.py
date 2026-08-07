"""
StockSense dashboard: price chart, latest news with sentiment, and a live prediction.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.api_client import get_prices, get_latest_news, get_prediction

st.set_page_config(page_title="StockSense", layout="wide")

TICKERS = [
    "^GSPC",
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

st.title("📈 StockSense")
st.caption(
    "Daily-ingested S&P 500 prices + news sentiment, with a baseline ML prediction."
)

# --- Sidebar: ticker selection ---
selected_ticker = st.sidebar.selectbox("Select a ticker", TICKERS)

# --- Section 1: Price chart ---
st.subheader(f"{selected_ticker} — Recent Price History")

prices = get_prices(selected_ticker, limit=60)

if not prices:
    st.warning(f"No price data available for {selected_ticker} yet. Has ingestion run?")
else:
    df = pd.DataFrame(prices).sort_values("date")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["close"], mode="lines", name="Close price")
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Close price ($)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Section 2: Prediction ---
st.subheader(f"{selected_ticker} — Next-Day Prediction")

prediction = get_prediction(selected_ticker)

if prediction is None:
    st.info(
        "No prediction available yet — the model may not have enough recent data for this ticker."
    )
else:
    col1, col2, col3 = st.columns(3)
    direction = prediction["prediction"]
    confidence = (
        prediction["probability_up"]
        if direction == "up"
        else 1 - prediction["probability_up"]
    )

    col1.metric("Predicted direction", direction.upper())
    col2.metric("Model confidence", f"{confidence:.1%}")
    col3.metric("As of", str(prediction["as_of_date"])[:10])

    st.caption(
        "⚠️ This is a baseline model trained on limited features for a learning project — "
        "not investment advice. Short-horizon price direction is notoriously close to a coin flip; "
        "see the README for honest evaluation numbers against a naive baseline."
    )

# --- Section 3: Latest news with sentiment ---
st.subheader("Latest Market News")

news = get_latest_news(limit=15)

if not news:
    st.info("No news articles ingested yet.")
else:
    for article in news:
        sentiment = article.get("sentiment_score")
        relevant = article.get("market_relevant")

        if sentiment is None:
            badge = "⏳ not yet scored"
        elif sentiment > 0.2:
            badge = f"🟢 +{sentiment:.2f} bullish"
        elif sentiment < -0.2:
            badge = f"🔴 {sentiment:.2f} bearish"
        else:
            badge = f"⚪ {sentiment:.2f} neutral"

        if relevant is False:
            badge += " (flagged not market-relevant)"

        with st.container(border=True):
            st.markdown(f"**{article['title']}**")
            st.caption(
                f"{article['source']} · {str(article['published_at'])[:16]} · {badge}"
            )
            if article.get("description"):
                st.write(article["description"])
            st.markdown(f"[Read more]({article['url']})")
