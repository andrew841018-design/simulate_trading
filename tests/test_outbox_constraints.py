"""Database contract tests for outbox-event persistence."""

from decimal import Decimal

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from uuid import uuid4
from app.config import account_settings


event_id = str(uuid4())
def test_pending_outbox_event():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("SIM-001", Decimal("100000.00"), Decimal("30000.00"))
            )
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                ("SIM-001", "ORDER_CREATED", "BUY", "LIMIT", 10, Decimal("100.00"), "AAPL")
            )
        event_payload = {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 0,
        }
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER_CREATED", 1, None, "OPEN", "ORDER_CREATED", Jsonb(event_payload))
            )
        with connection.cursor(row_factory=dict_row) as cursor:
            outbox_event = {
                "event_type": "ORDER_CREATED",
                "status_change_version": 1,
                "order_id": "ORDER_CREATED",    
                "payload": event_payload
            }
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    outbox_event["event_type"],
                    outbox_event["status_change_version"],
                    outbox_event["order_id"],
                    Jsonb(outbox_event["payload"]),
                ),
            )
        with connection.cursor(row_factory=dict_row) as cursor:
            row = cursor.execute(
                """
                SELECT * FROM outbox_events WHERE event_id=%s
                """,
                (event_id,)
            ).fetchone()
        assert row is not None
        assert row["outbox_id"] > 0
        assert row["event_id"] == event_id
        assert row["event_type"] == outbox_event["event_type"]
        assert row["status_change_version"] == outbox_event["status_change_version"]
        assert row["order_id"] == outbox_event["order_id"]
        assert row["payload"] == outbox_event["payload"]
        assert row["published_at"] is None
        assert row["created_at"] is not None
    finally:
        connection.rollback()
        connection.close()
def test_outbox_event_id_constraint():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "",
                    "ORDER_CREATED",
                    1,
                    "ORDER_CREATED",
                    Jsonb({"account_id": "SIM-001", "action": "BUY"}),
                ),
            )
        assert error.value.diag.constraint_name == "check_event_id_valid"
    finally:
        connection.rollback()
        connection.close()
def test_outbox_event_id_duplicate_constraint():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                (
                    "SIM-001",
                    Decimal("100000.00"),
                    Decimal("30000.00"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "SIM-001",
                    "ORDER_123",
                    "BUY",
                    "LIMIT",
                    10,
                    Decimal("100.00"),
                    "AAPL",
                ),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "ORDER_123",
                    1,
                    None,
                    "OPEN",
                    "ORDER_CREATED",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    }),
                ),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "ORDER_123",
                    2,
                    "OPEN",
                    "PARTIAL_FILLED",
                    "ORDER_PARTIALLY_FILLED",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 5
                    }),
                ),
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    "ORDER_CREATED",
                    1,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    }),
                ),
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    "ORDER_PARTIALLY_FILLED",
                    2,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 5
                    }),
                ),
            )
        assert error.value.diag.constraint_name == "outbox_events_event_id_unique"
    finally:
        connection.rollback()
        connection.close()
def test_outbox_composite_foreign_key_constraint():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(ForeignKeyViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    "ORDER_CREATED",
                    1,
                    "ORDER_123",
                    Jsonb({"account_id": "SIM-001", "action": "BUY"}),
                ),
            )
        assert error.value.diag.constraint_name == "outbox_events_order_id_composite_fkey"
    finally:
        connection.rollback()
        connection.close()
def test_outbox_event_order_transitions_unique():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                (
                    "SIM-001",
                    Decimal("100000.00"),
                    Decimal("30000.00"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "SIM-001",
                    "ORDER_123",
                    "BUY",
                    "LIMIT",
                    10,
                    Decimal("100.00"),
                    "AAPL",
                ),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "ORDER_123",
                    1,
                    None,
                    "OPEN",
                    "ORDER_CREATED",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    }),
                ),
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "event_id_1",
                    "ORDER_CREATED",
                    1,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    }),
                ),
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "event_id_2",
                    "ORDER_CREATED",
                    1,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    }),
                ),
            )
        assert error.value.diag.constraint_name == "order_id_status_change_version_unique"
    finally:
        connection.rollback()
        connection.close()
@pytest.mark.parametrize(
    "status_change_version,event_type,expected_constraint",
    [
        (0, "ORDER_CREATED", "check_status_change_version_non_zero"),
        (1, "", "check_event_type_valid"),
        (1, "asdfgrddgddsdfdsfdfdsdfdfdfdffggdghflkgf", "check_event_type_valid")
    ]
)
def test_outbox_constraint(status_change_version,event_type,expected_constraint):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                (
                    "SIM-001",
                    Decimal("100000.00"),
                    Decimal("30000.00"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "SIM-001",
                    "ORDER_123",
                    "BUY",
                    "LIMIT",
                    10,
                    Decimal("100.00"),
                    "AAPL",
                ),
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    event_type,
                    status_change_version,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    })
                ),
            )
        assert error.value.diag.constraint_name == expected_constraint
    finally:
        connection.rollback()
        connection.close()
def test_outbox_invalid_publish_time():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                (
                    "SIM-001",
                    Decimal("100000.00"),
                    Decimal("30000.00"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "SIM-001",
                    "ORDER_123",
                    "BUY",
                    "LIMIT",
                    10,
                    Decimal("100.00"),
                    "AAPL",
                ),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "ORDER_123",
                    1,
                    None,
                    "OPEN",
                    "ORDER_CREATED",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    })
                ),
            )
            row = cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload,published_at,created_at)
                VALUES (%s, %s, %s, %s, %s, now(), now() + interval '1 second')
                """,
                (
                    event_id,
                    "ORDER_CREATED",
                    1,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",    
                        "fill_quantity": 0
                    }),
                )
                ).fetchone()
        assert error.value.diag.constraint_name == "check_published_at_valid"
    finally:
        connection.rollback()
        connection.close()
def test_outbox_event_type_constraint():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                (
                    "SIM-001",
                    Decimal("100000.00"),
                    Decimal("30000.00"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "SIM-001",
                    "ORDER_123",
                    "BUY",
                    "LIMIT",
                    10,
                    Decimal("100.00"),
                    "AAPL",
                ),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "ORDER_123",
                    1,
                    None,
                    "OPEN",
                    "ORDER_CREATED",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",
                        "fill_quantity": 0
                    })
                )
            )
            cursor.execute(
                """
                INSERT INTO outbox_events (event_id, event_type,status_change_version,order_id,payload)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    "ORDER_ACCEPTED",
                    1,
                    "ORDER_123",
                    Jsonb({            
                        "account_id": "SIM-001",
                        "action": "BUY",
                        "order_type": "LIMIT",
                        "quantity": 10,
                        "price": "100.00",
                        "symbol": "AAPL",    
                        "fill_quantity": 0
                    }),
                ),
            )
        assert error.value.diag.constraint_name == "check_outbox_event_type_domain_valid"
    finally:
        connection.rollback()
        connection.close()
