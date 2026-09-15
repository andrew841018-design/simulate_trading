import psycopg
import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from app.config import account_settings

@pytest.fixture(scope="session",autouse=True)
def reset_test_database():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}", autocommit=True)
    assert connection.info.dbname.endswith("_test")
    connection.execute("TRUNCATE TABLE accounts,orders,order_transitions,outbox_events,idempotency_requests")
    connection.close()
def test_account_id_constraints():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES (NULL, 1000.00, 0.00)
                """
        )
    except NotNullViolation:
        pass
    else:
        result = connection.execute(
            """
            SELECT * FROM accounts WHERE account_id IS NULL
            """
        ).fetchone()
        assert result is None
    finally:
        connection.rollback()
        connection.close()
def test_total_cash_constraints():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test', -1000.00, 0.00)
                """
            )
    except CheckViolation:
        pass
    else:
        result = connection.execute(
            """
            SELECT * FROM accounts WHERE account_id = 'test'
            """
        ).fetchone()
        assert result is None
    finally:
        connection.rollback()
        connection.close()
def test_reserved_cash_constraints():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test_1', 1000.00, -500.00)
                """
            )
    except CheckViolation:
        pass
    else:
        result = connection.execute(
            """
            SELECT * FROM accounts WHERE account_id = 'test_1'
            """
        ).fetchone()
        assert result is None
    finally:
        connection.rollback()
        connection.close()
def test_reserved_cash_not_exceed_total_cash_constraints():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test_2', 1000.00, 1500.00)
                """
            )
    except CheckViolation:
        pass
    else:
        result = connection.execute(
            """
            SELECT * FROM accounts WHERE account_id = 'test_2'
            """
        ).fetchone()
        assert result is None
    finally:
        connection.rollback()
        connection.close()
def test_valid_account_insertion():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test_3', 1000.00, 500.00)
                """
            )
        result = connection.execute(
            """
            SELECT * FROM accounts WHERE account_id = 'test_3'
            """
        ).fetchone()
        assert result is not None
        assert result[0] == 'test_3'
        assert result[1] == 1000
        assert result[2] == 500
    finally:
        connection.rollback()
        connection.close()
def test_duplicate_account_id_insertion():
    connection = psycopg.connect(f"{account_settings.TEST_DATABASE_URL}")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test_4', 1000.00, 500.00)
                """
            )
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO accounts (account_id, total_cash, reserved_cash)
                VALUES ('test_4', 2000.00, 1000.00)
                """
            )
        assert error.value.diag.constraint_name == 'accounts_pkey'
    finally:
        connection.rollback()
        connection.close()
