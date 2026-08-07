from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas import PriceOut, NewsOut, PredictionOut
from db.models import Price, NewsArticle

app = FastAPI(title="StockSense API", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prices/{ticker}", response_model=list[PriceOut])
def get_prices(ticker: str, limit: int = 30, db: Session = Depends(get_db)):
    ticker = ticker.upper()
    rows = (
        db.query(Price)
        .filter(Price.ticker == ticker)
        .order_by(Price.date.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No price data found for ticker '{ticker}"
        )
    return rows


@app.get("/news/latest", response_model=list[NewsOut])
def get_latest_news(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(NewsArticle)
        .order_by(NewsArticle.published_at.desc())
        .limit(limit)
        .all()
    )


@app.get("/predictions/{ticker}", response_model=PredictionOut)
def get_prediction(ticker: str):
    from ml.predict import predict_latest

    ticker = ticker.upper()
    result = predict_latest(ticker)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Count not generate a prediction for '{ticker}'"
        )
    return result
