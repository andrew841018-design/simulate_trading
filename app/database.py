from collections.abc import Generator

import psycopg

from app.config import account_settings


def get_account_connection()-> Generator[psycopg.Connection, None, None]:
    connection = psycopg.connect(account_settings.DATABASE_URL)
    try:
        yield connection
    finally:
        connection.close()