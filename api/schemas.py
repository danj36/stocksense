from datetime import datetime
from pydantic import BaseModel


class PriceOut(BaseModel):
    ticker: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        from_attributes = (
            True  # lets Pydantic build this direcxtly from a SQLAlchemy row
        )


class NewsOut(BaseModel):
    source: str | None
    title: str
    description: str | None
    url: str
    published_at: datetime | None
    sentiment_score: float | None
    market_relevant: bool | None

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    ticker: str
    as_of_date: datetime
    prediction: str
    probability_up: float
