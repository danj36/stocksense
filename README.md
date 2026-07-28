# StockSense
A daily S&P 500 + news ingestion pipeline with a baseline prediction model, served via FastAPI and visualized in Streamlit. Built to practice Docker, Kubernetes, Airflow, and FastAPI in a real end-to-end project. 

## Architecture

## Tech Stack
Python, PostgreSQL, Apache Airflow, FastAPI, Streamlit, Docker, Kubernetes 



## what i learned
- localhost inside a container ≠ localhost on your host — containers reach each other via service name on Docker's internal network
- load_dotenv() doesn't override already-set env vars — so Compose-level environment: values win over .env file values inside containers
- PYTHONPATH controls where Python looks for importable packages, and it's not automatically inherited from "wherever your code happens to sit" the way it is when you run scripts locally from your project root