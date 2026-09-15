import sys
from pathlib import Path
import pytest
from scripts.virtual_user import build_manifest
from uuid import uuid4
from decimal import Decimal
import random
def test_build_manifest():
    batch_id = str(uuid4())
    seed = random.randint(0,2**32-1)
    manifest = build_manifest("SIM-001",batch_id,seed)
    assert type(manifest) is list and len(manifest) == 100
    unique_keys=[]
    cost=0
    for row in manifest:   
        assert row["idempotency_key"] not in unique_keys
        assert row["idempotency_key"] != ""
        assert len(row["payload"]) == 6  and len(row) == 2
        assert row["payload"]["account_id"] == "SIM-001"
        assert row["payload"]["action"] == "BUY"
        assert row["payload"]["order_type"] == "LIMIT"
        assert row["payload"]["symbol"] == "DEMO"
        assert 1 <= row["payload"]["quantity"] <= 100 and type(row["payload"]["quantity"]) is int
        assert row["payload"]["price"] == "10.00"
        cost += row["payload"]["quantity"] * Decimal(row["payload"]["price"])
        unique_keys.append(row["idempotency_key"])
    assert cost <= Decimal("100000.00")
@pytest.mark.parametrize(
    "account_id,batch_id,seed",
    [
        ### test seed
        ("SIM-001","batch_id",-1),
        ("SIM-001","batch_id","42"),
        ("SIM-001","batch_id",None),
        ("SIM-001","batch_id",2**32),
        ("SIM-001","batch_id",1.5),
        ("SIM-001","batch_id",True),
        ("SIM-001","batch_id",False),
        ### test account
        ("","batch_id",7),
        (1212,"batch_id",7),
        (1.5,"batch_id",7),
        (True,"batch_id",7),
        (False,"batch_id",7),
        (None,"batch_id",7),
        ("A"*65,"batch_id",7),
        ### test batch_id
        ("SIM-001","",7),
        ("SIM-001",1212,7),
        ("SIM-001",1.5,7),
        ("SIM-001",True,7),
        ("SIM-001",False,7),
        ("SIM-001","A"*65,7),
    ]
)
def test_manifest(account_id,batch_id,seed):
    with pytest.raises(ValueError) as error:
        build_manifest(account_id,batch_id,seed)
    assert str(error.value) in (
    "seed must be an integer from 0 to 2^32-1",
     "account_id must be a string from 1 to 64 characters",
     "batch_id must be a string from 1 to 64 characters"
    )
def test_repeatable_calling_manifest():
    batch_id = str(uuid4())
    seed = random.randint(0,2**32-1)
    first = build_manifest("SIM-001",batch_id,seed)
    second = build_manifest("SIM-001",batch_id,seed)
    key=[]
    for i in range(100):
        assert first[i]["idempotency_key"] == second[i]["idempotency_key"]
        key.append(first[i]["idempotency_key"])
        assert first[i]["payload"] == second[i]["payload"]
    batch_id = str(uuid4())
    third = build_manifest("SIM-001",batch_id,seed)
    for i in range(100):
        assert first[i]["idempotency_key"] != third[i]["idempotency_key"]
        assert first[i]["payload"] == third[i]["payload"]
        assert third[i]["idempotency_key"] not in key