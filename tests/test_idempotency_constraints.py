"""Database contract tests for idempotency and saved-response persistence."""

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg.errors import CheckViolation, UniqueViolation
from app.config import account_settings


def test_idempotency_unfinish_request():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    request={
        "idempotency_key":"SIM-001",
        "response_status":None,
        "response_body":None,
        "completed_at":None,
        "request_payload":{}
    }
    try:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO idempotency_requests (idempotency_key,request_payload)
                VALUES (%s, %s)
                """,
                (request["idempotency_key"],Jsonb(request["request_payload"])),
            )
        with connection.cursor(row_factory=dict_row) as cursor:
            row=cursor.execute(
            """
            SELECT * FROM idempotency_requests WHERE idempotency_key=%s
            """,(request["idempotency_key"],)
        ).fetchone()
        assert row is not None
        assert row["idempotency_key"] == request["idempotency_key"]
        assert row["request_payload"] == request["request_payload"]
        assert row["response_status"] is None
        assert row["response_body"] is None
        assert row["completed_at"] is None
    finally:
        connection.rollback()
        connection.close()
@pytest.mark.parametrize(
    "response_status,response_body,idempotency_key,request_payload,expected_constraint",
    [
        (200,None,"SIM-001","SIM1-001","check_response_status_and_body_valid"),
        (None,{"idempotency_key":"SIM-001"},"SIM1-001",{"idempotency_key":"SIM-001"},"check_response_status_and_body_valid"),
        (99,{"idempotency_key":"SIM-001"},"SIM-001",{"idempotency_key":"SIM-001"},"check_response_status_valid"),
        (600,{"idempotency_key":"SIM-001"},"SIM-001",{"idempotency_key":"SIM-001"},"check_response_status_valid"),
    ]
)
def test_idempotency_invalid_request(response_status,response_body,idempotency_key,request_payload,expected_constraint):
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idempotency_requests (response_status,response_body,idempotency_key,request_payload)
                VALUES (%s, %s, %s, %s)
                """,
                (response_status,None if response_body is None else Jsonb(response_body),
                 idempotency_key,None if request_payload is None else Jsonb(request_payload)),
            )
        assert error.value.diag.constraint_name == expected_constraint
    finally:
        connection.rollback()
        connection.close()
def test_idempotency_key_empty():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(CheckViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idempotency_requests (idempotency_key,request_payload,response_status,response_body)
                VALUES (%s, %s, %s, %s)
                """,
                ("",Jsonb({"idempotency_key":"SIM-001"}),None,Jsonb({"idempotency_key":"SIM-001"})),
            )
        assert error.value.diag.constraint_name == "check_idempotency_key_not_empty"
    finally:
        connection.rollback()
        connection.close()

def test_idempotency_key_unique():
    connection = psycopg.connect(account_settings.TEST_DATABASE_URL)
    assert connection.info.dbname.endswith("_test")
    try:
        with pytest.raises(UniqueViolation) as error, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idempotency_requests (idempotency_key,request_payload,response_status,response_body)
                VALUES (%s, %s, %s, %s)
                """,
                ("SIM-001",Jsonb({"idempotency_key":"SIM-001"}),200,Jsonb({"idempotency_key":"SIM-001"})),
            )
            cursor.execute(
                """
                INSERT INTO idempotency_requests (idempotency_key,request_payload,response_status,response_body)
                VALUES (%s, %s, %s, %s)
                """,
                ("SIM-001",Jsonb({"idempotency_key":"SIM-001"}),200,Jsonb({"idempotency_key":"SIM-001"})),
            )
        assert error.value.diag.constraint_name == "idempotency_requests_pkey"
    finally:
        connection.rollback()
        connection.close()