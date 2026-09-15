from random import Random
from math import pow as power
import httpx
from decimal import Decimal


def build_manifest(account_id,batch_id,seed):
    if type(seed) is not int or not 0 <= seed <= power(2,32)-1:
        raise ValueError("seed must be an integer from 0 to 2^32-1")
    if (not isinstance(account_id, str) or not 1 <= len(account_id) <= 64):
        raise ValueError("account_id must be a string from 1 to 64 characters")
    if (not isinstance(batch_id, str) or not 1 <= len(batch_id) <= 64):
        raise ValueError("batch_id must be a string from 1 to 64 characters")
    random=Random(seed)
    manifest=[]

    for i in range(100):
        manifest.append({
            "idempotency_key":f"{batch_id}-{i}",
            "payload": {
                "account_id":account_id,
                "action":"BUY",
                "order_type":"LIMIT",
                "symbol":"DEMO",
                "quantity":random.randint(1,100),
                "price":"10.00"
            }
        })
    return manifest
def manifest_response(client,manifest):
    rejected=0
    succeeded=0
    report={
        "attempted":0,
        "succeeded":0,
        "failed":0,
        "results":[]
    }
    record=[]
    results=[]
    for i in range(len(manifest)):
        record={
            "idempotency_key":manifest[i]["idempotency_key"],
            "order_id":None,
            "post_status":None,
            "get_status":None,
            "verified":False,
            "error":True,
            "total_cost":0
        }
        results.append(record)
        try:
            response=client.post("/v1/orders",json=manifest[i]["payload"],headers={"Idempotency-Key":manifest[i]["idempotency_key"]})
            results[i]["post_status"]=response.status_code
        except httpx.RequestError:
            rejected+=1
            results[i]["error"]="post_request_error"
            continue
        if response.status_code != 201:
            rejected+=1
            results[i]["error"]="post_http_error"
            continue
        try:
            body=response.json()
            order_id=body["order_id"]
        except ValueError:
            results[i]["error"]="post_json_error"
            rejected+=1
            continue
        except (KeyError,TypeError):# catch {},null,[]
            results[i]["error"]="post_invalid_response"
            rejected+=1
            continue
        if isinstance(order_id,str) and order_id!="":
            results[i]["order_id"]=order_id
            try:
                get_response=client.get(f"/v1/orders/{order_id}")
                results[i]["get_status"]=get_response.status_code
            except httpx.RequestError:
                results[i]["error"]="get_request_error"
                rejected+=1
                continue
            try:
                body_json=get_response.json()
                get_order_id=body_json["order_id"]
            except ValueError:
                results[i]["error"]="post_json_error"
                rejected+=1
                continue
            except (KeyError,TypeError):# catch {},null,[]
                results[i]["error"]="get_invalid_response"
                rejected+=1
                continue
            if (get_response.status_code != 200):
                rejected+=1
                results[i]["error"]="get_http_error"
                continue
            if (get_order_id != order_id):
                rejected+=1
                results[i]["error"]="order_id_mismatch"
                continue
            results[i]["error"]=None
            results[i]["verified"]=True
            results[i]["total_cost"]=manifest[i]["payload"]["quantity"]*Decimal(manifest[i]["payload"]["price"])
            succeeded+=1
        else:
            rejected+=1
            results[i]["error"]="post_invalid_response"
            continue
    report["results"]=results
    report["attempted"]=rejected+succeeded
    report["succeeded"]=succeeded
    report["failed"]=rejected
    return report

