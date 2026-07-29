from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    UniqueConstraint,
    Boolean,
)
from db.database import Base


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    # prevents duplicate rows if the ingestion job runs twice for the same day
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_ticker_date"),)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    title = Column(String, nullable=False)
    description = Column(String)
    url = Column(
        String, unique=True
    )  # natural dedup key - same article can't be inserted twice
    published_at = Column(DateTime)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0, Gemini-scored
    market_relevant = Column(Boolean, nullable=True)
