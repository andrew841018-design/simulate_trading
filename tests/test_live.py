from fastapi.testclient import TestClient
from app.main import app
test=TestClient(app)
def test_live():
    response = test.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "Live endpoint is working!"}

