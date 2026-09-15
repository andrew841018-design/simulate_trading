from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_account_connection

router = APIRouter()


@router.get("/{account_id}")
def get_account(
    account_id: str,
    connection: Annotated[
        psycopg.Connection,
        Depends(get_account_connection),
    ],
):
    row = connection.execute(
        """
        SELECT total_cash, reserved_cash
        FROM accounts 
        WHERE account_id = %s
        """,
        (account_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    total_cash, reserved_cash = row
    return {
        "account_id": account_id,
        "total_cash": total_cash,
        "reserved_cash": reserved_cash,
        "available_cash": total_cash - reserved_cash,
    }
