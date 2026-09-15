# simulate_trading

以 FastAPI 與 PostgreSQL 建立的模擬交易練習專案，使用合成帳戶與訂單資料。此提交涵蓋 Day 1～4：帳戶查詢、限價 BUY、資金預留、冪等回應、交易紀錄與瀏覽器操作介面。

## 已實作範圍

| 入口 | 行為 |
| --- | --- |
| `GET /live` | 回傳服務存活狀態 |
| `GET /` | 顯示模擬交易介面 |
| `GET /v1/accounts/{account_id}` | 查詢總現金、預留現金及可用現金 |
| `POST /v1/orders` | 建立訂單並預留資金；需要 `Idempotency-Key` header |
| `GET /v1/orders/{order_id}` | 查詢訂單狀態、成交數量及巢狀帳戶資料 |

建立訂單時，同一個 PostgreSQL transaction 更新 `accounts`，並寫入 `orders`、`order_transitions`、`outbox_events` 與 `idempotency_requests`。資金不足回傳 409；相同 key 與相同 normalized payload 重播已保存回應，相同 key 搭配不同 payload 回傳 409。

前端提供帳戶載入、BUY 表單、訂單查詢與本分頁訂單列表。成功送單後，以 GET 更新畫面；POST 回應遺失時保留原 key 與 payload，讓使用者確認原請求結果。列表與暫存限目前分頁。

## 本機啟動

需要 Python 3.12+、uv、PostgreSQL，以及執行前端測試用的 Node.js。以下指令都在專案根目錄執行，PostgreSQL 須已啟動且允許目前本機使用者連線。

```sh
uv sync --frozen
createdb simulate_trading
createdb simulate_trading_test
```

在本機 `.env` 設定兩個獨立資料庫（此檔由 Git 忽略）：

```dotenv
DATABASE_URL=postgresql:///simulate_trading
TEST_DATABASE_URL=postgresql:///simulate_trading_test
```

`alembic.ini` 預設連到本機 `simulate_trading`；若使用自訂資料庫位置，需一併調整其中的 `sqlalchemy.url`。

```sh
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m scripts.upgrade_test_database
psql -d simulate_trading -f scripts/seed_accounts.sql
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

開啟 <http://127.0.0.1:8000>，載入合成帳戶 `SIM-001`，即可送出限價 BUY 並查回結果。Seed 指令會將該帳戶重設為總現金 100000.00、預留現金 30000.00，僅用於首次本機 demo 初始化，勿在已有訂單後重跑。

## 驗證

```sh
.venv/bin/python -m pytest -q --tb=line
node --test scripts/check_browser_buy.cjs
```

Python 測試使用獨立的 `_test` 資料庫，會清空其中五張交易相關資料表。2026-09-15 對本次 Day 1～4 範圍重跑：70 項 Python 測試、22 項前端測試通過。

## 目前界線

此階段驗證限價 BUY 與循序請求；雖然 request schema 接受 `SELL`，SELL 持倉語意尚未完成。成交／取消、Kafka 發布、projection、並行冪等與效能驗證均屬後续工作。Outbox 目前是資料庫紀錄，沒有對外事件發布。Day 5 虛擬使用者不包含在本次提交。
