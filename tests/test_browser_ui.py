from fastapi.testclient import TestClient
from app.main import app


def test_main_page_vaild():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/html")
        assert "<h1>模擬交易</h1>" in response.text