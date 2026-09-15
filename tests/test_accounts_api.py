from decimal import Decimal

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import account_settings
from app.database import get_account_connection
from app.main import app


@pytest.fixture  ### simulate database=>overwrite original db with testing database
def test_client():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")

    def get_test_account_connection():
        yield connection

    try:
        connection.execute(
            """
            INSERT INTO accounts (account_id, total_cash, reserved_cash)
            VALUES (%s, %s, %s)
            """,
            ("SIM-001", Decimal("100000.00"), Decimal("30000.00")),
        )
        app.dependency_overrides[get_account_connection] = get_test_account_connection
        with TestClient(app) as client:  ### simulate request(using test http)
            yield client
    finally:
        app.dependency_overrides.clear()
        connection.rollback()
        connection.close()


def test_existing_account(test_client):
    response = test_client.get("/v1/accounts/SIM-001")
    assert response.status_code == 200
    assert response.json() == {
        "account_id": "SIM-001",
        "total_cash": 100000.00,
        "reserved_cash": 30000.00,
        "available_cash": 70000.00,
    }
def test_missing_account(test_client):
    """
    {NOT_FOUND} will become account_id in sql,this word mean nothing just check whether this function
    go well when account_id is not found in database
    """
    response = test_client.get("/v1/accounts/NOT_FOUND")
    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}
