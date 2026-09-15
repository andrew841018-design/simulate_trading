"""Database contract tests for order-transition persistence."""

import psycopg
import pytest
from decimal import Decimal
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import account_settings
def test_valid_initial_and_later_order_transitions():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id,total_cash,reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("SIM-001", Decimal("100000.00"), Decimal("30000.00")),
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id,order_id,action,order_type,quantity,price,symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                ("SIM-001", "ORDER-001", "BUY", "LIMIT", 10, 100, "AAPL"),
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 1, None, "OPEN", "ORDER_CREATED", 
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
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 2, "OPEN", "FILLED", "ORDER_FILLED", 
                Jsonb({
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL",
                    "fill_quantity": 10,
                    "fill_number": 1,
                    "fill_price": "100.00"
                })
                ),
            )
            rows = cursor.execute(
                """
                SELECT order_id, status_change_version, previous_status, current_status, transition_type, payload
                FROM order_transitions
                WHERE order_id = 'ORDER-001'
                ORDER BY status_change_version
                """
            ).fetchall()
            assert rows ==[
            {
                "order_id": "ORDER-001",
                "status_change_version": 1,
                "previous_status": None,
                "current_status": "OPEN",
                "transition_type": "ORDER_CREATED",
                "payload": {
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL",
                    "fill_quantity": 0,
                }
            },
            {
                "order_id": "ORDER-001",
                "status_change_version": 2,
                "previous_status": "OPEN",
                "current_status": "FILLED",
                "transition_type": "ORDER_FILLED",
                "payload": {
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL",
                    "fill_quantity": 10,
                    "fill_number": 1,
                    "fill_price": "100.00"
                }
            }]
    finally:
        connection.rollback()
        connection.close()
@pytest.mark.parametrize(
    "previous_status,current_status,status_change_version,transition_type,payload,expected_constraint",
    [

        (None, "OPEN", 0, "ORDER_CREATED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 0
        }, "check_status_change_version_non_zero"),
        ("OPEN", "OPEN", 1, "ORDER_CREATED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 0
        }, "check_status_change_version_valid"),
        (None, "FILLED", 1, "ORDER_FILLED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 10,
            "fill_number": 1,
            "fill_price": "100.00"
        }, "check_status_change_version_valid"),
        (None, "FILLED", 2, "ORDER_FILLED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 10,
            "fill_number": 1,   
            "fill_price": "100.00"
        }, "check_status_change_version_valid")
    ]
)
def test_reject_invalid_status_change_version(previous_status, current_status, status_change_version, transition_type, payload,expected_constraint):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", status_change_version, previous_status, current_status, transition_type,Jsonb(payload)
                ),
            )
        assert error.value.diag.constraint_name == expected_constraint
    finally:
        connection.rollback()
        connection.close()

@pytest.mark.parametrize(
    "previous_status,current_status,transition_type,payload,expected_constraint",
    [
        ("INVALID_STATUS", "FILLED", "ORDER_FILLED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 10,
            "fill_number": 1,
            "fill_price": "100.00"
        }, "check_previous_status_valid"),
        ("OPEN", "INVALID_STATUS", "ORDER_FILLED", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 10,
            "fill_number": 1,
            "fill_price": "100.00"
        }, "check_current_status_valid"),
        ("OPEN", "FILLED", "INVALID_TRANSITION", {
            "account_id": "SIM-001",
            "action": "BUY",
            "order_type": "LIMIT",
            "quantity": 10,
            "price": "100.00",
            "symbol": "AAPL",
            "fill_quantity": 10,
            "fill_number": 1,
            "fill_price": "100.00"
        }, "check_transition_type_domain_valid")
    ]
)
def test_invalid_transition_domain(previous_status, current_status, transition_type, payload,expected_constraint):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 2, previous_status, current_status, transition_type, Jsonb(payload))
            )
        assert error.value.diag.constraint_name == expected_constraint
    finally:
        connection.rollback()
        connection.close()

def test_reject_duplicate_order_transition():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id,total_cash,reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("SIM-001", 1000.00, 0.00)
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id,order_id,action,order_type,quantity,price,symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                ("SIM-001", "ORDER-001", "BUY", "LIMIT", 10, 100.00, "AAPL")
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 1, None, "OPEN", "ORDER_CREATED", Jsonb({
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL"
                }))
            )
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 1, None, "OPEN", "ORDER_CREATED", Jsonb({
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL"
                }))
            )
        assert error.value.diag.constraint_name == "order_transitions_pkey"
    finally:
        connection.rollback()
        connection.close()
def test_reject_transition_for_missing_order():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(ForeignKeyViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO order_transitions (order_id,status_change_version,previous_status,current_status,transition_type,payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ORDER-001", 1, None, "OPEN", "ORDER_CREATED", Jsonb({
                    "account_id": "SIM-001",
                    "action": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 10,
                    "price": "100.00",
                    "symbol": "AAPL"
                }))
            )
        assert error.value.diag.constraint_name == "order_transitions_order_id_fkey"
    finally:
        connection.rollback()
        connection.close()

