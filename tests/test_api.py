from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prices_unknown_ticker_returns_404():
    response = client.get("/prices/NOTAREALTICKER")
    assert response.status_code == 404


def test_prediction_unknown_ticker_returns_404():
    response = client.get("/predictions/NOTAREALTICKER")
    assert response.status_code == 404
