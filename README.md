# StockSense
Daily-ingested S&P 500 prices + market news, scored for sentiment via Gemini, feeding a baseline ML model for next-day direction prediction — served through a FastAPI backend and a Streamlit dashboard.

Built as a hands-on learning project covering the full stack: Docker, Airflow, FastAPI, PostgreSQL, LLM-based feature engineering, and cloud deployment.

## Live Demo
- Dashboard: http://18.117.251.77:8501/
- API docs: http://18.117.251.77:8000/docs
## Screenshots: 
See in folder screenshots

## Architecture

```mermaid
flowchart TB
    subgraph External["External APIs"]
        YF[yfinance]
        NA[NewsAPI]
        GM[Gemini API]
    end

    subgraph Airflow["Airflow (local, daily schedule)"]
        FP[fetch_prices]
        FN[fetch_news]
        SS[score_sentiment]
        DQ[data_quality_check]
        FP --> DQ
        FN --> SS --> DQ
    end

    subgraph Cloud["AWS EC2"]
        DB[(Postgres)]
        API[FastAPI]
        UI[Streamlit UI]
        API --> DB
        UI --> API
    end

    YF --> FP
    NA --> FN
    GM --> SS
    FP --> DB
    FN --> DB
    SS --> DB

    subgraph MLPipeline["ML Pipeline (local)"]
        BF[backfill_history]
        FE[features.py]
        TR[train.py]
        MDL[(baseline_model.pkl)]
        BF --> DB
        DB --> FE --> TR --> MDL
    end

    MDL -.scp.-> API
```

## Results
Model (with Gemini-scored news sentiment) vs. naive "always predict up" baseline:
- Naive baseline accuracy: 0.537
- Model accuracy: 0.529
- Model precision: 0.538
- Model recall: 0.865

## Tech Stack
Python · PostgreSQL · Apache Airflow · FastAPI · Streamlit · scikit-learn ·
Gemini API · Docker · Docker Compose · AWS EC2 · GitHub Actions

## Running Locally
See `stocksense-runbook.md` for full startup/shutdown instructions.

Quick start:
```powershell
docker compose up -d --build
```
Then: Airflow at localhost:8080, API at localhost:8000/docs, UI at localhost:8501.
