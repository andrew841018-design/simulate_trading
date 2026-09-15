"""Database constraint tests for orders."""
from decimal import Decimal

import psycopg
import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row

from app.config import account_settings


def test_valid_limit_buy_order():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            """ only insert col without default"""
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("ACCOUNT_TEST_ID", Decimal("10000.00"), Decimal("0.00"))
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    100,
                    Decimal('10.00'),
                    'AAPL'
                )
            )
            ## how to check we insert successfully? we can select the row and check if it exists
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT * FROM orders WHERE order_id = %s
                """,
                ('ORDER_TEST_ID',)
            )
            row = cursor.fetchone()
            assert row is not None, "Order was not inserted successfully"
            order_id = row['order_id']
            account_id = row['account_id']
            action = row['action']
            order_type = row['order_type']
            quantity = row['quantity']
            price = row['price']
            symbol = row['symbol']
            fill_quantity = row['fill_quantity']
            status = row['status']
            version = row['version']
            created_at = row['created_at']
            updated_at = row['updated_at']
            assert(
                order_id,
                account_id,
                action,
                order_type,
                quantity,
                price,
                symbol,
                fill_quantity,
                status,
                version,
            ) == (
                'ORDER_TEST_ID',
                'ACCOUNT_TEST_ID',
                'BUY',
                'LIMIT',
                100,
                Decimal('10.00'),
                'AAPL',
                0,
                'OPEN',
                1,
            )
            assert created_at is not None
            assert updated_at is not None
    finally:
        connection.rollback()
        connection.close()

@pytest.mark.parametrize(
    "fill_quantity, quantity,status",
    [
        (5, 10, "FILLED"),
        (10, 10, "CANCELLED"),
        (1, 10, "OPEN"),
        (10, 10 ,"PARTIAL_FILLED"),
        (0, 10, "PARTIAL_FILLED"),
    ],
)
def test_order_reject_invalid_status(fill_quantity, quantity, status):
    
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("ACCOUNT_TEST_ID", Decimal("10000.00"), Decimal("0.00"))
            )
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol, fill_quantity, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    quantity,
                    Decimal('10.00'),
                    'AAPL',
                    fill_quantity,
                    status
                )
            )
        assert error.value.diag.constraint_name == 'check_status_fill_quantity_valid'
    finally:
        connection.rollback()
        connection.close()
@pytest.mark.parametrize(
    "fill_quantity, quantity,status",
    [
        (5, 5, "FILLED"),
        (10, 15, "CANCELLED"),
        (0, 10, "OPEN"),
        (10, 50 ,"PARTIAL_FILLED"),
    ],
)
def test_order_accepts_valid_status(fill_quantity, quantity, status):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("ACCOUNT_TEST_ID", Decimal("10000.00"), Decimal("0.00"))
            )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol, fill_quantity, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    quantity,
                    Decimal('10.00'),
                    'AAPL',
                    fill_quantity,
                    status
                )
            )
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT * FROM orders WHERE order_id = %s
                """,
                ('ORDER_TEST_ID',),
            )
            row = cursor.fetchone()
            assert row is not None
            assert row["order_id"] == 'ORDER_TEST_ID'
            assert row["account_id"] == 'ACCOUNT_TEST_ID'
            assert row["action"] == 'BUY'
            assert row["order_type"] == 'LIMIT'
            assert row["quantity"] == quantity
            assert row["price"] == Decimal('10.00')
            assert row["symbol"] == 'AAPL'
            assert row["fill_quantity"] == fill_quantity
            assert row["status"] == status

    finally:
        connection.rollback()
        connection.close()

@pytest.mark.parametrize(
    "quantity,symbol,price,action,order_type,status,version,order_id,acceptable_constraints",
    [
        (0, 'AAPL', Decimal('10.00'), 'BUY', 'LIMIT', 'OPEN', 1, 'ORDER_TEST_ID', {"check_quantity_non_negative"}),
        (10, '', Decimal('10.00'), 'BUY', 'LIMIT', 'OPEN', 1, 'ORDER_TEST_ID', {"check_symbol_not_empty", "check_symbol_length_valid"}),
        (10, 'AAPL', 0, 'BUY', 'LIMIT', 'OPEN', 1, 'ORDER_TEST_ID', {"check_price_non_negative"}),
        (10, 'AAPL', Decimal('10.00'), 'buy put', 'LIMIT', 'OPEN', 1, 'ORDER_TEST_ID', {"check_action_valid"}),
        (10, 'AAPL', Decimal('10.00'), 'BUY', 'none', 'OPEN', 1, 'ORDER_TEST_ID', {"check_order_type_valid"}),
        (10, 'AAPL', Decimal('10.00'), 'BUY', 'LIMIT', 'error', 1, 'ORDER_TEST_ID', {"check_status_valid", "check_status_fill_quantity_valid"}),
        (10, 'AAPL', Decimal('10.00'), 'BUY', 'LIMIT', 'OPEN', -1, 'ORDER_TEST_ID', {"check_version_non_negative"}),
        (10, 'AAPL', Decimal('10.00'), 'BUY', 'LIMIT', 'OPEN', 1, '', {"check_order_id_not_null"})
    ]
)
def test_reject_invalid_field_domain(quantity,symbol,price,action,order_type,status,version,order_id,acceptable_constraints):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("ACCOUNT_TEST_ID", Decimal("10000.00"), Decimal("0.00"))
            )
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol, status, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    order_id,
                    action,
                    order_type,
                    quantity,
                    price,
                    symbol,
                    status,
                    version
                )
            )
        assert error.value.diag.constraint_name in acceptable_constraints
    finally:
        connection.rollback()
        connection.close()

def test_order_reject_duplicate_order_id():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (%s, %s, %s)
                """,
                ("ACCOUNT_TEST_ID", Decimal("10000.00"), Decimal("0.00"))
            )
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    100,
                    Decimal('10.00'),
                    'AAPL'
                )
            )
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'ACCOUNT_TEST_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    100,
                    Decimal('10.00'),
                    'AAPL'
                )
            )
        assert error.value.diag.constraint_name == 'pk_orders'
    finally:
        connection.rollback()
        connection.close()
def test_order_rejects_unknown_account_id():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(ForeignKeyViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (account_id, order_id, action, order_type, quantity, price, symbol)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    'UNKNOWN_ACCOUNT_ID',
                    'ORDER_TEST_ID',
                    'BUY',
                    'LIMIT',
                    100,
                    Decimal('10.00'),
                    'AAPL'
                )
            )
        assert error.value.diag.constraint_name == 'fk_orders_account_id_accounts'
    finally:
        connection.rollback()
        connection.close()