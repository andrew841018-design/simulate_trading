"""API contract tests for orders."""
from decimal import Decimal
import pytest
import psycopg
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from app.config import account_settings
from app.database import get_account_connection
from app.main import app

@pytest.fixture
def order_api_client_and_connection():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("SIM-001",Decimal("100000.00"), Decimal("30000.00"))
            )
        def get_test_account_connection():
            yield connection
        app.dependency_overrides[get_account_connection] = get_test_account_connection
        with TestClient(app) as client:
            yield client, connection
    finally:
        app.dependency_overrides.clear()
        connection.rollback()
        connection.close()
@pytest.fixture
def order_api_client():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("SIM-001", Decimal("100000.00"), Decimal("30000.00"))
            )
        def get_test_account_connection():
            yield connection
        app.dependency_overrides[get_account_connection] = get_test_account_connection
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        connection.rollback()
        connection.close()
def test_create_limit_buy_order(order_api_client):
        response = order_api_client.post(
            "/v1/orders",
            headers={"Idempotency-Key": "20260823-001"},
            json={
                "account_id": "SIM-001",
                "action": "BUY",
                "order_type": "LIMIT",
                "quantity": 100,
                "price": "10.00",
                "symbol": "AAPL"
            }
        )
        body=response.json()
        assert response.status_code == 201
        assert body.get("action")=="BUY"
        """
        order_id won't generate from here,order_id is generated from create_order()
        create_order() is in orders.py
        """
        assert isinstance(body.get("order_id"), str)
        assert body.get("order_id")
        assert body.get("order_type")=="LIMIT"
        assert body.get("quantity")==100
        assert body.get("price")=="10.00"
        assert body.get("symbol")=="AAPL"
        assert body.get("account_id")=="SIM-001" 

        response_account = order_api_client.get("/v1/accounts/SIM-001")
        body_account=response_account.json()
        correct_reserved_cash=Decimal("30000.00")+body.get("quantity")*Decimal(body.get("price"))
        correct_available_cash=Decimal("100000.00")-correct_reserved_cash
        assert response_account.status_code == 200
        assert body_account.get("account_id")=="SIM-001"
        assert body_account.get("total_cash")==100000.00
        assert body_account.get("reserved_cash")==correct_reserved_cash
        assert body_account.get("available_cash")==correct_available_cash

def test_rejects_insufficient_cash(order_api_client):
        payload = {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 1000,
            "price": "1000.00",
            "symbol": "AAPL"
        }
        response = order_api_client.post(
            "/v1/orders",
            headers={"Idempotency-Key": "20260825-001"},
            json=payload
        )
        response_account = order_api_client.get("/v1/accounts/SIM-001")
        body_account=response_account.json()
        assert response_account.status_code == 200
        assert body_account.get("total_cash")==100000.00
        assert body_account.get("reserved_cash")==30000.00
        assert body_account.get("available_cash")==70000.00

        required_cash=Decimal(payload["quantity"])*Decimal(payload["price"])
        available_cash=body_account.get("available_cash")
        assert required_cash > available_cash
        assert response.status_code == 409
        assert response.json() == {"detail": "Insufficient cash"}
# simulate network disconnect while creating order,so we need to replay
def test_replays_same_key_same_payload(order_api_client):
    payload = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    first_response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload
    )
    assert first_response.status_code == 201
    json=first_response.json()
    replay_response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload
    )
    assert replay_response.status_code == 201
    assert replay_response.json()==json
def test_rejects_same_key_different_payload(order_api_client):
    payload1 = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    payload2 = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 101,
        "price": "10.00",
        "symbol": "AAPL"
    }
    first_response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload1
    )
    assert first_response.status_code == 201
    replay_response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload2
    )
    assert replay_response.status_code == 409
    assert replay_response.json() == {"detail": "Idempotency key already exists"}
def test_rejects_non_positive_quantity(order_api_client):
    payload = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": -1,
        "price": "10.00",
        "symbol": "AAPL"
    }
    response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload
    )
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["body", "quantity"]
def test_gets_existing_order(order_api_client):
    pay_load = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    response = order_api_client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=pay_load
    )
    order_id=response.json().get("order_id")
    assert response.status_code == 201
    get_response = order_api_client.get(f"/v1/orders/{order_id}")
    assert get_response.status_code == 200
    get_json=get_response.json()
    assert get_json["account"]["account_id"]=="SIM-001"
    assert get_json["account"]["total_cash"]==100000
    assert get_json["account"]["reserved_cash"]==31000
    assert get_json["account"]["available_cash"]==69000
    assert get_json["order_id"]==order_id
    assert get_json["status"]=="OPEN"
    assert get_json["fill_quantity"]==0
def test_returns_404_for_missing_order(order_api_client):
    MISSING_ID = "ORDER_NOT_FOUND"
    response=order_api_client.get(f"/v1/orders/{MISSING_ID}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}
def test_create_limit_buy_order_initial_transition(order_api_client_and_connection):
        client, connection = order_api_client_and_connection
        response = client.post(
            "/v1/orders",
            headers={"Idempotency-Key": "20260823-001"},
            json={
                "account_id": "SIM-001",
                "action": "BUY",
                "order_type": "LIMIT",
                "quantity": 100,
                "price": "10.00",
                "symbol": "AAPL"
            }
        )
        body=response.json()
        assert response.status_code == 201
        order_id=body.get("order_id")
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT * FROM order_transitions
                WHERE order_id = %s
                """,
                (order_id,)
            )
            transition = cursor.fetchall()
            assert transition is not None
            assert len(transition) == 1
            assert transition[0]['order_id'] == order_id
            assert transition[0]['status_change_version'] == 1
            assert transition[0]['previous_status'] is None
            assert transition[0]['current_status'] == "OPEN"
            assert transition[0]['transition_type'] == "ORDER_CREATED"
            assert transition[0]['payload']['fill_quantity'] == 0
def test_create_limit_buy_order_initial_outbox(order_api_client_and_connection):
        client, connection = order_api_client_and_connection
        response = client.post(
            "/v1/orders",
            headers={"Idempotency-Key": "20260823-001"},
            json={
                "account_id": "SIM-001",
                "action": "BUY",
                "order_type": "LIMIT",
                "quantity": 100,
                "price": "10.00",
                "symbol": "AAPL"
            }
        )
        body=response.json()
        assert response.status_code == 201
        order_id=body.get("order_id")
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT * FROM outbox_events
                WHERE order_id = %s
                """,
                (order_id,)
            )
            outbox_event = cursor.fetchall()
            assert outbox_event is not None
            assert len(outbox_event) == 1
            assert outbox_event[0]['order_id'] == order_id
            assert outbox_event[0]['status_change_version'] == 1
            assert outbox_event[0]['event_type'] == "ORDER_CREATED"
            assert outbox_event[0]['published_at'] is None
            cursor.execute(
                """
                SELECT * FROM order_transitions
                WHERE order_id = %s
                """,
                (order_id,)
            )
            transition = cursor.fetchall()
            assert transition is not None
            assert len(transition) == 1
            assert transition[0]['payload'] == outbox_event[0]['payload']
def test_retries_same_key_after_funding_insufficient_cash(order_api_client_and_connection):
    client, connection = order_api_client_and_connection
    payload = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 1000,
        "price": "1000.00",
        "symbol": "AAPL"
    }
    first_response = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload
    )
    assert first_response.status_code == 409
    assert first_response.json() == {"detail": "Insufficient cash"}
    with connection.cursor(row_factory=dict_row) as cursor:
        idempotency_request = cursor.execute(
            """
            SELECT * FROM idempotency_requests WHERE idempotency_key = %s
            """,
            ("20260825-001",)
        ).fetchone()
    assert idempotency_request is None
    connection.execute(
        """
        UPDATE accounts SET total_cash = 1300000.00,reserved_cash = 30000.00 WHERE account_id = %s
        """,
        ("SIM-001",),
    )
    retry_response = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-001"},
        json=payload
    )
    assert retry_response.status_code == 201
    with connection.cursor(row_factory=dict_row) as cursor:
        saved_success = cursor.execute(
            """
            SELECT response_status, response_body FROM idempotency_requests
            WHERE idempotency_key = %s
            """,
            ("20260825-001",),
        ).fetchone()
    assert saved_success is not None
    assert saved_success["response_status"] == 201
    assert saved_success["response_body"] == retry_response.json()
    order_count = connection.execute(
        "SELECT COUNT(*) FROM orders WHERE order_id = %s",
        (retry_response.json()["order_id"],),
    ).fetchone()[0]
    assert order_count == 1
def test_create_order_with_invalid_account(order_api_client_and_connection):
    client, connection = order_api_client_and_connection
    payload = {
        "account_id": "INVALID-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    first_response = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-002"},
        json=payload
    )
    assert first_response.status_code == 404
    assert first_response.json() == {"detail": "Account not found"}
    with connection.cursor(row_factory=dict_row) as cursor:
        idempotency_request = cursor.execute(
            """
            SELECT * FROM idempotency_requests WHERE idempotency_key = %s
            """,
            ("20260825-002",)
        ).fetchone()
    assert idempotency_request is None
    connection.execute(
        """
        INSERT INTO accounts (account_id, total_cash, reserved_cash)
        VALUES (%s, %s, %s)
        """,
        (payload["account_id"], Decimal("100000.00"), Decimal("30000.00"))
    )
    retry_response = client.post(
        "/v1/orders",
        headers={"Idempotency-Key": "20260825-002"},
        json=payload
    )
    with connection.cursor(row_factory=dict_row) as cursor:
        idempotency_request = cursor.execute(
        """
        SELECT * FROM idempotency_requests WHERE idempotency_key = %s
        """,
        ("20260825-002",)
    ).fetchone()
    assert retry_response.status_code == idempotency_request["response_status"] == 201
    assert idempotency_request["response_body"] == retry_response.json()
    order_id = retry_response.json()["order_id"]
    row = connection.execute(
        """
        SELECT * FROM orders WHERE order_id = %s
        """,
        (order_id,)
    ).fetchone()
    assert row is not None
class OutboxFailureConnection:
    def __init__(self, real_connection):
        self.real_connection = real_connection
    def transaction(self):
        return self.real_connection.transaction()
    def execute(self, query, params=None):
        if "INSERT INTO outbox_events" in query:
            raise RuntimeError("Simulated outbox failure")
        return self.real_connection.execute(query, params)
def test_rolls_back_order_when_outbox_write_fails(order_api_client_and_connection):
    client, connection = order_api_client_and_connection
    payload = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    def read_state():
        return {
            "total_cash": connection.execute("""SELECT total_cash FROM accounts WHERE account_id = %s""", ("SIM-001",)).fetchone()[0],
            "reserved_cash": connection.execute("""SELECT reserved_cash FROM accounts WHERE account_id = %s""", ("SIM-001",)).fetchone()[0],
            "accounts_count": connection.execute("""SELECT COUNT(*) FROM accounts""").fetchone()[0],
            "orders_count": connection.execute("""SELECT COUNT(*) FROM orders""").fetchone()[0],
            "order_transitions_count": connection.execute("""SELECT COUNT(*) FROM order_transitions""").fetchone()[0],
            "outbox_events_count": connection.execute("""SELECT COUNT(*) FROM outbox_events""").fetchone()[0],
            "idempotency_requests_count": connection.execute("""SELECT COUNT(*) FROM idempotency_requests""").fetchone()[0],
        }
    before = read_state()
    invalid_connection = OutboxFailureConnection(connection)# assign self.real connection evne if it doesn't have return
    def get_invalid_connection():
        yield invalid_connection

    original_override = app.dependency_overrides[get_account_connection]
    app.dependency_overrides[get_account_connection] = get_invalid_connection

    try:
        with pytest.raises(
            RuntimeError,
            match="^Simulated outbox failure$",
        ):
            client.post(
                "/v1/orders",
                headers={"Idempotency-Key": "rollback_outbox_001"},
                json=payload,
            )

        after = read_state()
        assert before == after
    finally:
        app.dependency_overrides[get_account_connection] = original_override
# test there are enougth available cashes for created order or not
def test_reconciles_created_order_cashes(order_api_client_and_connection):
    client, connection = order_api_client_and_connection
    with connection.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute("SELECT * FROM accounts WHERE account_id = %s", ("SIM-001",)).fetchone()
        assert row is not None
    reserved_cash_before = row["total_cash"]-row["reserved_cash"]
    payload = {
        "account_id": "SIM-001",
        "action": "BUY",
        "order_type": "LIMIT",
        "quantity": 100,
        "price": "10.00",
        "symbol": "AAPL"
    }
    response = client.post("/v1/orders", headers={"Idempotency-Key": "20260825-001"}, json=payload)
    assert response.status_code == 201
    order_id = response.json()["order_id"]
    with connection.cursor(row_factory=dict_row) as cursor:
        row = cursor.execute(
            """
            SELECT quantity,fill_quantity,price FROM orders WHERE order_id = %s
            """,(order_id,)
        ).fetchone()
        assert row is not None
        quantity = row["quantity"]
        fill_quantity = row["fill_quantity"]
        price = row["price"]
        total_cost = (quantity-fill_quantity) * price
        row = cursor.execute("SELECT * FROM accounts WHERE account_id = %s", ("SIM-001",)).fetchone()
        available_cash_after = row["total_cash"] - row["reserved_cash"]
        assert reserved_cash_before-available_cash_after ==  total_cost
 
