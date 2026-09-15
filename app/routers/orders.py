"""Order API routes."""
from decimal import Decimal
from uuid import uuid4
from typing import Annotated,Literal
from psycopg.rows import dict_row

import psycopg
from psycopg.types.json import Jsonb
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, Header, status, HTTPException
from pydantic import BaseModel, Field

from app.database import get_account_connection


router = APIRouter()


class CreateOrderRequest(BaseModel):
    account_id: str
    action: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT"]
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=32)
    
@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    order: CreateOrderRequest,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key"),
    ],
    connection: Annotated[
        psycopg.Connection,
        Depends(get_account_connection),
    ],
):
    """
    order_id manage from backend(receive) not frontend(request),
    so class CreateOrderRequest can't have order_id....because it is frontend request
    """
    order_request_payload = order.model_dump()
    order_request_payload["price"] = format(order_request_payload["price"], ".2f")
    order_id = str(uuid4())
    with connection.transaction():
        saved_request = connection.execute(
            """
            SELECT request_payload,response_body,response_status 
            FROM idempotency_requests
            WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        ).fetchone()
        if saved_request is not None:
            saved_payload, saved_response, saved_status = saved_request
            if saved_payload != order_request_payload:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency key already exists",
                )
            return JSONResponse(status_code=saved_status, content=saved_response)
        connection.execute(
            """
            INSERT INTO idempotency_requests (idempotency_key,request_payload)
            VALUES (%s, %s)
            """,
            (idempotency_key, Jsonb(order_request_payload)),
        )
        account = connection.execute(
            """
            SELECT total_cash,reserved_cash
            FROM accounts
            WHERE account_id = %s
            FOR UPDATE
            """,
            (order.account_id,),
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found")
        total_cash, reserved_cash = account
        required_cash = order.quantity * order.price
        available_cash = total_cash - reserved_cash
        if required_cash > available_cash:
            raise HTTPException(status_code=409, detail="Insufficient cash")
        connection.execute(
            """
            UPDATE accounts
            SET reserved_cash = reserved_cash + %s
            WHERE account_id = %s
            """,
            (order.quantity * order.price, order.account_id),
        )
        connection.execute(
            """
            INSERT INTO orders (order_id, account_id, action, order_type, quantity, price, symbol)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (order_id, order.account_id, order.action, order.order_type, order.quantity, order.price, order.symbol),
        )
        transition_payload = {
            **order_request_payload,
            "fill_quantity": 0,
        }
        connection.execute(
            """
            INSERT INTO order_transitions (order_id, status_change_version, previous_status, current_status, transition_type, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (order_id, 1, None, "OPEN", "ORDER_CREATED", Jsonb(transition_payload)),
        )
        connection.execute(
            """
            INSERT INTO outbox_events (event_id, event_type, order_id, payload, status_change_version)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(uuid4()), "ORDER_CREATED", order_id, Jsonb(transition_payload), 1),
        )
        response_body = {
            **order_request_payload,
            "order_id": order_id,
        }
        connection.execute(
            """
            UPDATE idempotency_requests
            SET response_status = %s, response_body = %s, completed_at = NOW()
            WHERE idempotency_key = %s
            """,
            (201, Jsonb(response_body), idempotency_key),
        )
        return response_body
@router.get("/{order_id}", status_code=status.HTTP_200_OK)
def get_order(
    order_id: str,
    connection: Annotated[
        psycopg.Connection,
        Depends(get_account_connection),
    ],):
        with connection.cursor(row_factory=dict_row) as cursor:
            row = cursor.execute(
                """
                SELECT orders.order_id, status, fill_quantity, a.total_cash, a.reserved_cash,a.account_id
                FROM orders
                JOIN accounts AS a ON orders.account_id = a.account_id
                WHERE order_id = %s
                """,
                (order_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Order not found")
            available_cash = row["total_cash"] - row["reserved_cash"]
            response_body = {
                "order_id": order_id,
                "status": row["status"],
                "fill_quantity": row["fill_quantity"],
                "account": {
                    "total_cash": row["total_cash"],
                    "reserved_cash": row["reserved_cash"],
                    "available_cash": available_cash,
                    "account_id": row["account_id"],
                }
            }
        return response_body
