# simulate_trading Data Contract Spec

Last database verification (read-only): 2026-09-14 (Asia/Taipei); isolated `simulate_trading_test` remains at `d3f7a4c91e20`, with five business tables, 36 columns and 40 constraints.
Route／test驗證：2026-09-10 suite70passed in1.21s；Day4真實test DB瀏覽器／SQL驗證及結束rollback完成。詳見docs/day4_browser_acceptance.md。
Project stage (2026-09-15): Days1–4 complete (4/56); Day5 4/5, active4-1 data-flow and scope explanation. Sequential report validation (21/21) and isolated 100-order API/SQL reconciliation passed; see virtual_user_manifest.md and references/day5_api_sql_evidence_20260915.json. Frontend and Day4 explanation delegated to Codex; no independent frontend mastery claimed. No API/table/payload contract change in Day4.
Day 3 explain-back disposition (2026-09-09): Andrew explicitly requests the correct explanation and this question counted as passed. Gate waived by user authorization; independent mastery not demonstrated. This supersedes prior exam/retest requirements for this question only. No automatic reopening. Day4 frontend/explanation follows the newer2026-09-10 delegation; backend learning rules remain.
Database evidence: isolated `simulate_trading_test`, Alembic revision `d3f7a4c91e20`

## 0. 先從這裡找：table 欄位、JSON key、request／response

**本文件的查閱單位是「table → column → JSON key」。** §3 解釋每個資料庫欄位；遇到 JSONB，點同列連結看 §5 的逐 key 資料字典。每個 JSON key 的型別、中文意義、資料來源、必填條件與完整內容範例都必須明列，不能只寫「payload／snapshot」或只貼 JSON。

### 0.1 Table 目錄

| Table | 一筆 row 代表什麼 | 欄位數 | JSON 欄位與內容入口 |
|---|---|---|---|
| [accounts](#table-accounts) | 一個模擬交易帳戶目前的現金狀態 | 3 | 無 JSONB；[帳戶 GET 回應](#json-account-response) 是另外組出的 HTTP JSON |
| [orders](#table-orders) | 一張訂單目前的狀態 | 12 | 無 JSONB；POST 回應見 [response_body](#json-response-body)，不是整張 orders row |
| [idempotency_requests](#table-idempotency-requests) | 一個唯一請求 key 的輸入與保存結果 | 6 | [request_payload：輸入 6 keys](#json-request-payload)；[response_body：保存成功7 keys；錯誤HTTP body另列](#json-response-body) |
| [order_transitions](#table-order-transitions) | 某張訂單的一次狀態變更 | 7 | [payload：共同 7 keys＋依事件增加欄位](#json-transition-payload) |
| [outbox_events](#table-outbox-events) | 一次狀態變更對應的待發布事件 | 8 | [payload：與對應 transition 相同](#json-outbox-payload)；[Kafka 外層 envelope](#json-kafka-envelope) 是另一層 |
| [alembic_version](#table-alembic-version) | 資料庫套用到哪個 migration revision | 1 | 工具管理表，無 JSONB，不屬於 5 張業務 table |

上述 5 張業務 table 共 **36 個欄位、4 個 JSONB 欄位**。尚未建立的 `fills`、market tables 與其他規劃中資料見 [§6](#planned-tables)，不可把未定案欄位當成已存在 schema。

### 0.2 名稱對照：response_payload 到底在哪裡？

| 你搜尋的名稱 | 專案實際名稱／位置 | 內容與意義 |
|---|---|---|
| `request_payload` | `idempotency_requests.request_payload`；route 也有同名 Python 變數 | 使用者這次要做什麼：`account_id`、`action`、`order_type`、`quantity`、`price`、`symbol`。逐欄見 [§5.1](#json-request-payload) |
| `response_body` | `idempotency_requests.response_body`；route 的同名變數用來組成功結果 | 伺服器這次回覆什麼：201 時是 7 keys；不足資金409與帳戶不存在404的HTTP body只有`detail`，兩者均不保存。逐欄見 [§5.2](#json-response-body) |
| `response_payload` | **目前 migration、route 與核准契約沒有這個欄位或變數名稱** | 若指「回應內容」，查 `response_body`；若指「請求內容」，查 `request_payload`。這是搜尋指引，不是新增合法欄位別名 |
| `response_status` | `idempotency_requests.response_status` | HTTP 狀態碼，例如 201／409；它是獨立 DB column，**不在 response_body JSON 裡** |
| `saved_response` | route 讀回 `response_body` 後使用的 Python 變數 | 與保存的 body 是同一份內容，不是另一種 JSON schema |
| `transition_payload` | route 的 Python 變數 | 寫入 `order_transitions.payload` 與 `outbox_events.payload`；目前初始事件是 6 個輸入欄位加 `fill_quantity` |
| `payload` | 必須連 table 名一起查 | `order_transitions.payload` 與 `outbox_events.payload` 是事件資料；不是 HTTP response_body |
| `data` | 未來 Kafka envelope 內的 key | 裝入整份 outbox payload；它不是另一個資料庫 column |

注意：`orders.status` 是訂單狀態，例如 `OPEN`；`response_status` 是 HTTP 狀態碼，例如 `201`，兩者意義不同。JSON 範例的值是示意資料；欄位集合及意義以對應的核准契約表為準。

## 1. Purpose and status vocabulary

This is the cumulative field-level contract for the deterministic trading sandbox. It records what a row means, what every persisted field means, which values are accepted, what is authoritative, and which JSON payload details are still unresolved.

Status labels used below:

- **CURRENT VERIFIED**: confirmed in the isolated test database and current saved source/tests.
- **CURRENT SOURCE ONLY**: present in saved application source, but not yet a complete acceptance-verified application behavior; this label does not describe database migration status.
- **APPROVED BUT NOT IMPLEMENTED**: required by the authoritative dashboard/plan, but no current application path enforces it.
- **UNRESOLVED / CONFLICT**: current sources disagree or the field-level contract has not been approved.

Rules for reading this document:

- PostgreSQL authoritative tables decide money and current order state; Kafka/projections must never override them.
- JSON examples are illustrative unless explicitly marked **CURRENT VERIFIED contract**.
- A test fixture dictionary does not become a production payload contract by existing in a test.
- Exact decimal values are represented as PostgreSQL `NUMERIC` in authoritative tables. Canonical idempotency, transition and outbox price JSON uses decimal strings; the current account HTTP response still encodes `Decimal` cash values as JSON numbers.
- The sandbox uses fictitious accounts and no real money, credentials, or personal data. Payloads must not contain secrets or unnecessary identifiers.

## 2. System-wide ownership

| Concern | Authoritative source | Derived / snapshot consumers |
|---|---|---|
| Account total and reserved cash | `accounts` | API derives `available_cash` |
| Current order state | `orders` | Current authoritative order GET plus initial zero-fill reconciliation; future lifecycle reconciliation |
| Order state-change history | `order_transitions` | Future validator and outbox |
| Retry identity and saved HTTP result | `idempotency_requests` | Current sequential successful-result replay/conflict and rejected-key reuse; pending/concurrency handling remains future |
| Committed event awaiting publication | `outbox_events` | Future relay, Kafka and timeline projection |

Current application status:

- `GET /v1/accounts/{account_id}` reads `accounts` and derives available cash.
- `POST /v1/orders` now has a partial single-transaction implementation in saved source: it formats request `price` to two decimals, compares an existing idempotency payload, returns the row's current `response_body` or `409` for a different payload, inserts a pending idempotency row, locks the account with `FOR UPDATE`, validates available cash, increments `reserved_cash`, inserts the UUID-owned order, and saves the `201` response body plus `completed_at`. Exact API tests verify successful reservation changes account cash from `100000/30000/70000` to `100000/31000/69000`, while insufficient cash returns `409` and leaves the original values unchanged.
- Focused API verification (2026-09-09): full suite69 passed in1.47s; separate READ ONLY post-suite five-table counts all0. Day3 implementation acceptance complete; final explain-back explicitly waived by Andrew. Historical verification; latest Day4 completion is recorded above. No new trading behavior.
- Current source accepts both `BUY` and `SELL` but applies the BUY cash-reservation path to either action. That conflicts with the approved SELL position-reservation semantics and must not be treated as the current SELL contract.
- Retention policy (2026-09-07): retain successful `201` only. Unknown-account `404` and insufficient-cash `409` leave no pending or completed idempotency row and no business effects, allowing same-key retry after account creation/funding; schema-validation `422` also leaves no row. Different payload under an existing successful key returns `409` without overwriting it. Focused tests now verify both rejected-request paths leave no row and that the same key/payload succeeds after funding or account creation. Do not restore saved `404` or saved `409` snapshots.
- `idempotency_requests`, `order_transitions` and `outbox_events` exist in the isolated test database. Idempotency, transition and outbox schema constraints are complete; the latest full three-file constraint regression is `27 passed`. Follow-up revision `d3f7a4c91e20` restricts outbox `event_type` to the same four approved values as transition type, and `ORDER_ACCEPTED` has exact PostgreSQL rejection evidence. Day 3 item 10 is complete at its approved basic BUY/rejection/retry/single-failpoint scope; item 11 authoritative order GET and the item 12 initial zero-fill reconciliation code gate are verified. Day 3 was completed on2026-09-09 with item12 explain-back explicitly waived by Andrew; Day4 now complete; active Day5 manifest.

## 3. CURRENT VERIFIED database contracts

欄位表中的 `NOT NULL` 表示不可為 SQL NULL；沒有列出 `DEFAULT` 的欄位，在目前 migration 沒有 server default。`JSONB NOT NULL` 不等於已驗證 JSON 內部 keys。`now()` 是 PostgreSQL transaction timestamp，不是精確的 commit 時間。2026-09-09 以 read-only transaction 重新核對隔離 test DB 的 revision、table／column／constraint 數量與空表狀態；route／test 契約則以目前存檔 source、authoritative dashboard 和既有 69-pass 證據交叉核對。

<a id="table-accounts"></a>

### 3.1 `accounts`

Purpose: authoritative cash state for one fictitious trading account.  
Grain: exactly one row per `account_id`.  
Current writers: seed/fixtures and the partial `POST /v1/orders` path, which increments `reserved_cash` after locking the account. Future fill/cancel transactions are approved but not implemented.  
Current readers: account API and test/reconciliation SQL.

| 欄位 | PostgreSQL 型別／NULL／預設 | 中文意義與資料來源 | 限制與目前狀態 |
|---|---|---|---|
| `account_id` | `TEXT NOT NULL`, primary key | 模擬帳戶的唯一識別碼，例如 SIM-001；由 seed／fixture 建立，訂單透過此值找到資金擁有人 | 唯一；目前 DB 沒有非空或長度 CHECK，因此空字串也未明確拒絕。 |
| `total_cash` | `NUMERIC(12,2) NOT NULL` | 帳戶擁有的總現金，包含已預留部分；不是目前還能使用的現金 | `>= 0`；核准單位為隱含的 `SIM-USD`，沒有 currency column。 |
| `reserved_cash` | `NUMERIC(12,2) NOT NULL` | 已為未完成 BUY 義務預留的現金；預留仍屬於 total_cash，不能再被另一筆訂單使用 | `>= 0` 且 `<= total_cash`。 |

衍生欄位（不是 accounts column）：`available_cash` 表示目前還能拿來下新 BUY 的現金；[GET JSON 的逐 key 說明](#json-account-response)。

```text
available_cash = total_cash - reserved_cash
```

例如 total_cash=100000.00、reserved_cash=30000.00，可用資金為 70000.00。

Constraints:

- `accounts_pkey (account_id)`
- `check_total_cash_non_negative`
- `check_reserved_cash_non_negative`
- `check_reserved_cash_not_exceed_total_cash`

Not currently enforced:

- account ID nonblank/maximum length;
- account currency;
- reconciliation between `reserved_cash` and all active BUY orders;
- row-lock and mutation ownership.

<a id="table-orders"></a>

### 3.2 `orders`

Purpose: authoritative snapshot of one logical LIMIT order and its current state.  
Grain: exactly one row per `order_id`.  
Current writers: `POST /v1/orders` and database tests.  
Current readers: tests and the verified authoritative `GET /v1/orders/{order_id}` route, which returns the current order identity/status/fill quantity with a nested snapshot of the owning account's current cash state.

| 欄位 | PostgreSQL 型別／NULL／預設 | 中文意義與資料來源 | 限制與目前狀態 |
|---|---|---|---|
| `order_id` | `TEXT NOT NULL`, PK | 一張訂單的伺服器識別碼；目前由 route 產生 UUID 字串，使用者不能自行指定 | Must have character length `> 0`; no maximum length. |
| `account_id` | `TEXT NOT NULL`, FK | 這張訂單屬於哪個帳戶；從 request 取得並以 FK 關聯 accounts | Must be nonblank; references `accounts.account_id`; delete is `RESTRICT`. |
| `action` | `TEXT NOT NULL` | 買賣方向：BUY 買入、SELL 賣出；不是訂單處理狀態 | Enum-by-CHECK: `BUY`, `SELL`. |
| `order_type` | `TEXT NOT NULL` | 下單方式；LIMIT 表示使用指定的每單位限價 | Current only value: `LIMIT`. |
| `quantity` | `INTEGER NOT NULL` | 原始委託的整數數量；例如委託 10 單位，即使部分成交後仍保留 10 | `> 0`; unit is whole simulated shares/units. |
| `fill_quantity` | `INTEGER NOT NULL DEFAULT 0` | 截至目前累積已成交的數量；例如兩次各成交 2、3，這裡是 5，不是最後一筆的 3 | `>= 0`, `<= quantity`; must also match the status matrix below. |
| `symbol` | `TEXT NOT NULL` | 交易商品代碼，例如 AAPL；與 action 一起表達買／賣哪個商品 | Nonblank, length 1–32; uppercase normalization is not enforced by DB. |
| `price` | `NUMERIC(12,2) NOT NULL` | 每單位委託限價；不是整張訂單金額，也不是將來的成交價 fill_price | `> 0`; exact two-decimal authoritative value. |
| `status` | `TEXT NOT NULL DEFAULT 'OPEN'` | 訂單目前狀態：OPEN 未成交、PARTIAL_FILLED 部分成交、FILLED 全數成交、CANCELLED 已取消剩餘量 | Current DB enum: `OPEN`, `PARTIAL_FILLED`, `FILLED`, `CANCELLED`. |
| `version` | `INTEGER NOT NULL DEFAULT 1` | 目前訂單快照的版本號；預計供狀態更新與事件版本對帳，當前只有初始值 1 | `> 0`; no current application logic increments or compares it. |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 訂單 row 建立時間；由資料庫產生，不是用戶送出 request 的時間 | DB-generated. |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 預計表示訂單最後更新時間；目前只有 INSERT default，UPDATE 不會自動刷新 | Only a default exists; PostgreSQL does not automatically change it on UPDATE. |

Current status/fill matrix:

| `status` | Required `fill_quantity` relationship | Terminal? |
|---|---|---|
| `OPEN` | `fill_quantity = 0` | No |
| `PARTIAL_FILLED` | `0 < fill_quantity < quantity` | No |
| `FILLED` | `fill_quantity = quantity` | Yes |
| `CANCELLED` | `fill_quantity < quantity` | Yes |

Constraints and indexes:

- PK `pk_orders (order_id)`
- FK `fk_orders_account_id_accounts`, `ON DELETE RESTRICT`
- CHECKs for positive quantity/price/version, nonnegative bounded fill quantity, symbol length/nonblank, action/order type/status domains and the status/fill matrix
- index `idx_orders_account_status (account_id, status)`

Not currently enforced:

- legal state-to-state transition pairs;
- terminal-state immutability;
- `updated_at` refresh behavior;
- continuous agreement among `orders.version`, transition version and outbox version;
- reservation reconciliation or atomic mutation.

Current route precision conflict: request parsing accepts positive decimal values with more than two fractional digits. The idempotency payload/HTTP body uses Python two-decimal formatting, cash reservation uses the original unquantized `Decimal`, and PostgreSQL independently coerces `orders.price` into `NUMERIC(12,2)`. Until the request boundary rejects or canonically quantizes once before every use, these three values can diverge and violate reservation reconciliation.

<a id="table-idempotency-requests"></a>

### 3.3 `idempotency_requests`

Purpose: persist one logical command identity, its normalized request payload and an optional saved HTTP result.  
Grain: one globally unique `idempotency_key`.  
Current writers/readers: database contract tests plus the partial `POST /v1/orders` path. That route directly compares saved JSONB payloads, inserts a pending row, reads an existing row for replay/conflict, and completes successful `201` snapshots; 404/insufficient-cash 409 must leave no idempotency record; only successful results are retained.

| 欄位 | PostgreSQL 型別／NULL／預設 | 中文意義與資料來源 | 限制與目前狀態 |
|---|---|---|---|
| `idempotency_key` | `VARCHAR(128) NOT NULL`, PK | 用戶提供的一次邏輯請求識別碼；同 key 同輸入重播原結果，同 key 不同輸入衝突；key 單獨唯一 | DB 拒絕空字串，最多 128 字元；尚不拒絕純空白。Payload 不參與 PK／unique key。 |
| `request_payload` | `JSONB NOT NULL` | 這次請求的正規化輸入 JSON；用於比對同 key 是否為同一指令。[6 個 key 的意義與範例](#json-request-payload) | DB 只保證 JSONB NOT NULL；6-key 形狀由 route 組出，部分 normalization／bound 尚未實作，見 §5.1。 |
| `response_status` | `INTEGER NULL` | 這次請求保存的 HTTP 狀態碼；目前核准只保存成功201；不足資金409不保存；它不屬於 response_body 內部欄位 | If present, 100–599; must be NULL exactly when `response_body` is NULL. |
| `response_body` | `JSONB NULL` | 這次請求保存的 HTTP JSON 本體；成功為 7 keys，錯誤為 detail。[逐 key 與各狀態範例](#json-response-body) | Must appear as a pair with `response_status`; internal structure is not DB-validated. |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 首次建立這個 key 的紀錄時間；重播不是新的首次請求 | DB-generated. |
| `completed_at` | `TIMESTAMPTZ NULL`, no default | 預計表示 status/body 已決定並保存的時間；尚未完成時為 SQL NULL，目前 DB 尚未強制它與回應完成同步 | NULL represents unfinished; no CHECK currently ties it to response fields. |

Current lifecycle shapes:

```text
Pending:
response_status = NULL
response_body   = NULL
completed_at    = NULL

Saved result:
response_status = 100..599
response_body   = JSONB
completed_at    = intended non-NULL, but not enforced by DB
```

Constraints:

- PK `idempotency_requests_pkey (idempotency_key)`
- `check_idempotency_key_not_empty`
- `check_response_status_and_body_valid`
- `check_response_status_valid`

Current verified behavior: pending row round-trip, response pair, status range, blank key and duplicate key tests; complete file evidence recorded as `7 passed`.

<a id="table-order-transitions"></a>

### 3.4 `order_transitions`

Purpose: append-oriented history explaining how an order state changed.  
Grain: one `order_id × status_change_version` row.  
Current writers/readers: create_order() writes the initial row; the API test reads it through the same connection. Count, structural fields and payload pass. Independent transition payload preserves the six-field request and seven-field response. Existing DB constraint verification remains valid.
Future readers: validator, outbox/event flow and timeline reconstruction.

| 欄位 | PostgreSQL 型別／NULL／預設 | 中文意義與資料來源 | 限制與目前狀態 |
|---|---|---|---|
| `order_id` | `TEXT NOT NULL`, composite PK + FK | 這次狀態變更屬於哪張訂單；與 status_change_version 一起識別一筆歷史 | References `orders.order_id`; delete is `RESTRICT`. |
| `status_change_version` | `INTEGER NOT NULL`, composite PK | 同張訂單第幾個狀態變更版本；初始版本為 1，不是整張 table 的流水號 | `> 0`; version 1 has the designated initial shape, but DB constraints do not require every order's first stored transition to be version 1. |
| `previous_status` | `TEXT NULL` | 變更前的訂單狀態；初始建立事件沒有前一狀態，因此為 SQL NULL | Initial version must be NULL; later versions must be non-NULL. Non-NULL values use current order status enum. |
| `current_status` | `TEXT NOT NULL` | 這次變更後產生的訂單狀態；這是該歷史時點的狀態，不一定永遠等於目前 orders.status | Current DB enum: `OPEN`, `PARTIAL_FILLED`, `FILLED`, `CANCELLED`. Initial version must produce `OPEN`. |
| `transition_type` | `TEXT NOT NULL` | 這次變更發生什麼事：建立、部分成交、全數成交或取消；精確 mapping 見 §4.3 | Enum-by-CHECK: `ORDER_CREATED`, `ORDER_PARTIALLY_FILLED`, `ORDER_FILLED`, `ORDER_CANCELLED`; length 1–32. |
| `payload` | `JSONB NOT NULL` | 該事件的業務快照，例如委託數量、限價與變更後累積成交量。[全部 JSON keys](#json-transition-payload) | DB accepts any JSON value; the service-level field contract is defined in section 5.3. |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | 這筆狀態變更 row 的資料庫紀錄時間；不是 HTTP 回應完成時間 | DB-generated. |

Applied constraints:

- PK `order_transitions_pkey (order_id, status_change_version)`
- FK `order_transitions_order_id_fkey`, `ON DELETE RESTRICT`
- `check_status_change_version_non_zero`
- `check_status_change_version_valid`: any version-1 row must be `NULL -> OPEN`; versions greater than 1 require non-NULL previous status
- previous/current status domain CHECKs
- `check_transition_type_length_valid`: nonblank text with length 1–32; behaviorally redundant while the stricter four-value domain CHECK remains, and PostgreSQL currently reports the domain CHECK first for empty or overlength values
- `check_transition_type_domain_valid`: approved four-value transition enum

Not currently enforced:

- existence of a first transition at version 1 and gap-free versions (`1,2,3...`);
- `previous_status` equals the preceding row's `current_status`;
- legal transition pair matrix;
- transition type matches the before/after status;
- `current_status` matches the current `orders.status`;
- append-only protection against UPDATE/DELETE;
- payload shape;
- canonical price encoding inside JSON.

<a id="table-outbox-events"></a>

### 3.5 `outbox_events`

Purpose: durable committed domain event waiting for publication; PostgreSQL business commit remains correct even when Kafka is unavailable.  
Grain: currently at most one outbox event per referenced order transition; the approved atomic application invariant is exactly one.  
Current writers/readers: create_order writes one initial ORDER_CREATED outbox row after the initial transition in the same transaction. The route-level test verifies count, order/version/type, payload equality and NULL published_at. A test-only failure at the outbox insert verifies rollback to the same cash values and row counts on the shared test connection. The initial zero-fill BUY reconciliation test also verifies the newly created order's persisted remaining cost equals the account's reservation delta. Existing schema tests verify identity, linkage and publication constraints. No relay or publication writer is implemented; broader failpoint, cross-connection durability and fill/cancel lifecycle reconciliation evidence remain pending.

| 欄位 | PostgreSQL 型別／NULL／預設 | 中文意義與資料來源 | 限制與目前狀態 |
|---|---|---|---|
| `outbox_id` | `BIGINT GENERATED ALWAYS AS IDENTITY`, PK | 資料庫自動產生的本表識別碼；供 relay 穩定排序／輪詢，可有缺號，不等於業務 event_id | Starts at 1 in migration source; application must not provide it. |
| `event_id` | `TEXT NOT NULL`, unique | 這一個業務事件的固定去重識別碼；目前初始 writer 產生 UUID 字串，重送同一事件必須沿用同一值 | Nonblank; no maximum length. |
| `order_id` | `TEXT NOT NULL`, composite FK + unique pair | 事件屬於哪張訂單；與 status_change_version 一起指向 order_transitions 的同一筆歷史 | Must match an existing transition together with version. |
| `status_change_version` | `INTEGER NOT NULL`, composite FK + unique pair | 事件對應的訂單狀態變更版本；不是 outbox_id，也不是 Kafka 格式 schema_version | `> 0`. |
| `event_type` | `TEXT NOT NULL` | 事件種類；應等於所參照 transition 的 transition_type，不能因發布而改成另一種事件 | Length 1–32 and restricted by `check_outbox_event_type_domain_valid` to the referenced transition domain: `ORDER_CREATED`, `ORDER_PARTIALLY_FILLED`, `ORDER_FILLED`, `ORDER_CANCELLED`. |
| `payload` | `JSONB NOT NULL` | 待發布的業務資料 JSON；必須等於對應 transition.payload，不包含 Kafka 外層 envelope。[全部 JSON keys](#json-outbox-payload) | No field-level schema or envelope version is currently enforced. |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | outbox row 建立時的 DB timestamp；供 Kafka occurred_at 使用，不代表稍後的 transaction commit 精確時間 | DB-generated. |
| `published_at` | `TIMESTAMPTZ NULL` | 未來 relay 收到 broker ack 後才寫入的發布標記時間；SQL NULL 表示尚未標記發布，不是事件不存在 | NULL means unpublished; non-NULL must be `>= created_at`. |

Constraints and indexes:

- PK `outbox_events_pkey (outbox_id)`
- unique `outbox_events_event_id_unique (event_id)`
- unique `order_id_status_change_version_unique (order_id, status_change_version)`
- composite FK to `order_transitions (order_id, status_change_version)`, `ON DELETE RESTRICT`
- positive version, bounded event type, nonblank event ID and published-time CHECKs
- current indexes are the PK/unique backing indexes; there is no dedicated partial index for unpublished polling

Approved delivery semantics, not implemented:

- relay polls unpublished rows in stable `outbox_id` order;
- broker acknowledgment happens before `published_at` is set;
- ack-before-mark crash may duplicate delivery;
- future consumer deduplicates by `event_id` and `(order_id, status_change_version)`;
- delivery claim is at-least-once with idempotent projection effects, not exactly-once.

<a id="table-alembic-version"></a>

### 3.6 `alembic_version` — migration 管理表

一筆 row 記錄一個目前已套用的 migration head；由 Alembic 管理，應用程式不拿它儲存訂單或 JSON。此專案目前是單一路徑的 migration chain；型別由已安裝 Alembic 的 `version_table_impl` 原始碼核對，本次沒有重查 DB。

| 欄位 | 型別 | 中文意義與來源 |
|---|---|---|
| `version_num` | `VARCHAR(32) NOT NULL`；預設設置為 PK | 目前資料庫 migration revision 的識別字串，例如已紀錄的 `d3f7a4c91e20`；不是訂單 version 或 JSON schema_version |

## 4. Enum and state-machine contracts

### 4.1 CURRENT VERIFIED database values

| Domain | Values accepted by applied DB |
|---|---|
| `orders.action` | `BUY`, `SELL` |
| `orders.order_type` | `LIMIT` |
| order status fields | `OPEN`, `PARTIAL_FILLED`, `FILLED`, `CANCELLED` |
| `order_transitions.transition_type` | `ORDER_CREATED`, `ORDER_PARTIALLY_FILLED`, `ORDER_FILLED`, `ORDER_CANCELLED` |
| `outbox_events.event_type` | `ORDER_CREATED`, `ORDER_PARTIALLY_FILLED`, `ORDER_FILLED`, `ORDER_CANCELLED` |

### 4.2 APPROVED canonical domain registry

These names are the only approved values for new code, tests and documentation. Both transition and outbox event-type enum CHECKs are present in the upgraded isolated test DB.

| Domain | Approved values | Notes |
|---|---|---|
| `orders.action` | `BUY`, `SELL` | Client command side. |
| `orders.order_type` | `LIMIT` | No MARKET order in the core sandbox. |
| order status | `OPEN`, `PARTIAL_FILLED`, `FILLED`, `CANCELLED` | Use these exact spellings everywhere. `PARTIALLY_FILLED` and `CANCELED` are invalid aliases. |
| `order_transitions.transition_type` | `ORDER_CREATED`, `ORDER_PARTIALLY_FILLED`, `ORDER_FILLED`, `ORDER_CANCELLED` | `ORDER_ACCEPTED` is not part of the contract. |
| `outbox_events.event_type` | Same four values as `transition_type` | Must equal the referenced transition's type. Any other value is invalid; representative invalid aliases are `ORDER_ACCEPTED`, `ORDER_PARTIAL_FILLED` and `ORDER_CANCELED`. Target DB constraint name: `check_outbox_event_type_domain_valid`. |
| deterministic execution profile | `NO_FILL`, `PARTIAL`, `FULL` | Test/development simulator only. |
| logical currency | `SIM-USD` | One sandbox currency; it is implicit and not stored in current tables. |

The transition and outbox length/domain CHECKs have distinct names and are verified in the isolated test DB. Follow-up migration `d3f7a4c91e20` adds `check_outbox_event_type_domain_valid` with the same four approved values.

### 4.3 Transition type and state mapping

| `transition_type` / `event_type` | Required `previous_status` | Required `current_status` | Meaning |
|---|---|---|---|
| `ORDER_CREATED` | `NULL` | `OPEN` | Initial accepted order; `status_change_version = 1`. |
| `ORDER_PARTIALLY_FILLED` | `OPEN` or `PARTIAL_FILLED` | `PARTIAL_FILLED` | One bounded fill leaves remaining quantity. |
| `ORDER_FILLED` | `OPEN` or `PARTIAL_FILLED` | `FILLED` | Fill completes the remaining quantity. |
| `ORDER_CANCELLED` | `OPEN` or `PARTIAL_FILLED` | `CANCELLED` | Cancel releases only the remaining reservation. |

Applied DB currently enforces only the special initial row and status domains. The approved complete matrix is:

```text
NULL -> OPEN
OPEN -> PARTIAL_FILLED | FILLED | CANCELLED
PARTIAL_FILLED -> PARTIAL_FILLED | FILLED | CANCELLED
FILLED and CANCELLED are terminal
```

## 5. JSONB payload contracts

<a id="json-request-payload"></a>

### 5.1 `idempotency_requests.request_payload` — APPROVED contract, partial CURRENT SOURCE ONLY implementation

Approved semantic purpose: normalized representation of the submitted command, compared directly for same-key replay/conflict. No fingerprint/hash is used.

The normalized v1 payload contains exactly these keys:

| JSON key | 中文意義／來源 | 核准 JSON 型別、值與必填條件 | 範例 |
|---|---|---|---|
| `account_id` | 要用哪個帳戶下單；來自 request，對應 orders.account_id | 必填 string，非空，1–64 字元；保留大小寫，拒絕前後空白 | `"SIM-001"` |
| `action` | 買入或賣出方向；來自 request | 必填 string，只能是 `BUY`／`SELL` | `"BUY"` |
| `order_type` | 使用哪種下單方式；來自 request | 必填 string，目前只核准 `LIMIT` | `"LIMIT"` |
| `quantity` | 原始委託總數量；不是成交數量 | 必填正整數 JSON number；核准契約不接受字串或小數形式 | `10` |
| `price` | 每單位委託限價；不是總價 | 必填十進位 string，正值、固定兩位小數；不得用 JSON float | `"100.00"` |
| `symbol` | 要買／賣的商品代碼；來自 request | 必填非空 string，1–32 字元；核准 ASCII 大寫、拒絕前後空白 | `"AAPL"` |

核准內容範例（固定 **6 keys**）：

```json
{"account_id":"SIM-001","action":"BUY","order_type":"LIMIT","quantity":10,"price":"100.00","symbol":"AAPL"}
```

JSON object key order is irrelevant because PostgreSQL `JSONB` equality is used. Endpoint name, idempotency key, generated order ID, timestamps and response fields are not part of `request_payload`. The serialized normalized payload must be at most 4 KiB at the service boundary; the current DB does not enforce that bound.

**CURRENT SOURCE ONLY implementation:** `CreateOrderRequest.model_dump()` supplies the six approved keys and the route converts `price` with `format(value, ".2f")` before `Jsonb(...)` persistence and direct comparison. Exact action/order-type enums, positive quantity/price after Pydantic coercion, and symbol length 1–32 are enforced by the request model. Strict JSON integer/decimal input types, exact input scale, the approved account-ID bound/nonblank rule, whitespace rejection, uppercase-symbol normalization, idempotency-key bound/nonblank validation and 4 KiB payload limit are not implemented at the service boundary. Formatting rounds arbitrary-scale price input only for the JSON snapshot; reservation arithmetic still uses the original `Decimal`, while `orders.price` is independently coerced by PostgreSQL.

<a id="json-response-body"></a>

### 5.2 `idempotency_requests.response_body` — APPROVED contract, partial CURRENT SOURCE ONLY implementation

Purpose: exact canonical HTTP JSON body returned on same-key/same-payload replay, for successful order creation. Unknown-account 404, insufficient-cash 409 and validation 422 do not create saved results or consume a key.

Approved v1 snapshots:

| HTTP status | Canonical body | Saved? |
|---|---|---|
| `201` | `order_id`, `account_id`, `action`, `order_type`, `quantity`, two-decimal string `price`, `symbol` | Yes. Replay returns the exact saved JSON body. |
| `404` unknown account | `{"detail":"Account not found"}` | No. Leave no idempotency row; the key remains reusable after account creation. |
| `409` insufficient cash | `{"detail":"Insufficient cash"}` | No. Leave no idempotency row or business effect; after funding, the same key/payload may be processed anew. |
| `409` same key/different payload | `{"detail":"Idempotency key already exists"}` | No new snapshot; the existing canonical result remains unchanged. |
| `422` schema validation | FastAPI validation detail array | No idempotency row is created. |


#### 5.2.1 成功 201：response_body 內有哪些欄位？

以下 **7 keys 全部必填**。前 6 個來自已正規化的 request_payload；`order_id` 由伺服器建立。它是 POST 建立結果的快照，不是把 orders 全部 columns 都回傳。

| JSON key | JSON 型別 | 中文意義與來源 | 範例 |
|---|---|---|---|
| `account_id` | string | 這張新訂單使用哪個帳戶；複製正規化輸入 | `"SIM-001"` |
| `action` | string：`BUY`／`SELL` | 這次委託的買賣方向；複製正規化輸入 | `"BUY"` |
| `order_type` | string：`LIMIT` | 這次委託的下單方式；複製正規化輸入 | `"LIMIT"` |
| `quantity` | positive integer | 這張訂單原始委託數量；不是累積成交數量 | `10` |
| `price` | decimal string，固定兩位小數 | 這張訂單每單位限價；不是現金餘額或訂單總價 | `"100.00"` |
| `symbol` | string | 這張訂單的商品代碼；複製正規化輸入 | `"AAPL"` |
| `order_id` | 非空 string；目前為 UUID text | 伺服器為新訂單建立的識別碼，對應 orders.order_id；重播時保持相同 ID | `"11111111-1111-4111-8111-111111111111"` |

```json
{
  "account_id": "SIM-001",
  "action": "BUY",
  "order_type": "LIMIT",
  "quantity": 10,
  "price": "100.00",
  "symbol": "AAPL",
  "order_id": "11111111-1111-4111-8111-111111111111"
}
```

輸入欄位的 bounds／normalization 沿用 [§5.1](#json-request-payload)；那裡也標出尚未實作的檢查。`response_status=201` 存在 JSON 外面的獨立 column。這份 POST body **沒有** `status`、`fill_quantity`、`version`、`response_status`、`completed_at` 或 `available_cash`。

#### 5.2.2 不保存的不足資金 409：HTTP body 只有 detail

| JSON key | JSON 型別／必填 | 中文意義與來源 |
|---|---|---|
| `detail` | string，必填；整份 body 只有這個 key | API 決定的錯誤原因；不是 stack trace、原始 SQL error 或一張失敗 order 的欄位 |

| HTTP status（不保存到 response_status） | 情境 | HTTP response body | 保存契約 |
|---|---|---|---|
| `409` | 可用現金不足 | `{"detail":"Insufficient cash"}` | 不保存、不留下pending row；入金後同key／同payload重新處理 |

2026-09-07更新：不足資金是未產生交易效果的拒絕，撤回固定保存／重播409的要求。首次409後不得有pending或completed idempotency row，也不得建立order、reservation、transition或outbox效果；入金後可同key＋同payload重新評估並下單。成功201才保存並重播。這裡的detail是HTTP回應，並非資料庫中保存的response_body；錯誤body不添加account_id／order_id。

#### 5.2.3 其他 HTTP 錯誤與 pending，不是新的保存 body

- 帳戶不存在 `404`：回 `{"detail":"Account not found"}`，但不保存 response snapshot，也不留下 pending idempotency row；帳戶建立後可用同 key＋同 payload 重新判斷。這是 2026-09-07 核准的新規則，取代舊的「404 固定保存／重播」。本規則適用新 key 的帳戶查詢失敗，不授權覆寫既有 key 的完成結果。
- 同 key＋不同 payload：回 `409` 與 `{"detail":"Idempotency key already exists"}`；其中 `detail` 是 key 已用於另一份輸入的原因。**不覆寫**該 key 原先保存的 body/status。
- Schema validation `422`：framework 回傳 validation detail array，不建立 idempotency row；其逐 key 說明見 [§5.5](#json-other-http-response)。不能把該 array 當成這裡保存的 `detail` string。
- Pending：`response_status` 與 `response_body` 都是 **SQL NULL**，尚未有完成結果。SQL NULL、JSON 的 `null`、空 object `{}` 是不同概念；不能任意互換。

The DB only enforces that `response_status` and `response_body` appear together; the service must enforce these shapes. POST creation intentionally does not add `status`, `fill_quantity` or `version` to the v1 response unless the API contract is explicitly versioned later.

**CURRENT SOURCE ONLY implementation:** source saves successful201 body/completed_at and replays saved response_status/body; unknown-account404 and insufficient-cash409 raise within the transaction. Their retry slices and a test-only late-outbox failure with cash/count rollback evidence pass. Recorded verification covers the existing BUY/rejection/retry/rollback contracts; current collection is13 orderAPI cases, including2 GET cases and initial reconciliation. The separate authoritative GET existing/missing pair and nested account response are now CURRENT VERIFIED in §5.5. Full failpoint coverage, concurrent ownership and cross-connection durable-commit verification remain later gates.

<a id="json-transition-payload"></a>

### 5.3 `order_transitions.payload` — APPROVED contract; initial sample verified, full enforcement pending

Purpose: versioned event-specific snapshot needed to explain a state change. It is not the authoritative current order row.

Every approved transition payload uses the common shape below. It must be passed to psycopg with `Jsonb(...)`; a plain Python dictionary is not the database adapter contract. The payload has no inner version field: the future Kafka envelope's outer `schema_version` is the single format version. Current DB enforcement is only `JSONB NOT NULL`; the initial ORDER_CREATED sample is verified, while full service-level shape and bounds enforcement remains pending.

The current initial writer uses independent transition_payload: six request fields plus fill_quantity=0. API persistence and exact-payload probes pass. Saved request retains six fields; POST and saved response retain seven fields. Future-event shapes and bounds remain pending.

```json
{
  "account_id": "SIM-001",
  "action": "BUY",
  "order_type": "LIMIT",
  "quantity": 10,
  "price": "100.00",
  "symbol": "AAPL",
  "fill_quantity": 0
}
```

共同 **7 keys** 的逐欄資料字典：

| JSON key | 中文意義／來源 | 核准型別與必填條件 | 範例 |
|---|---|---|---|
| `account_id` | 事件所屬訂單的帳戶；初始 writer 複製 request_payload | 所有事件必填 string；沿用 §5.1 的識別碼契約 | `"SIM-001"` |
| `action` | 該訂單的買賣方向，不是事件種類 | 所有事件必填 `BUY`／`SELL` string | `"BUY"` |
| `order_type` | 該訂單的下單方式 | 所有事件必填 `LIMIT` string | `"LIMIT"` |
| `quantity` | 該訂單原始委託數量；部分成交後仍不變 | 所有事件必填 positive integer | `10` |
| `price` | 該訂單每單位限價；不是 fill_price | 所有事件必填固定兩位小數的 decimal string | `"100.00"` |
| `symbol` | 該訂單交易的商品代碼 | 所有事件必填 string；沿用 §5.1 的商品代碼契約 | `"AAPL"` |
| `fill_quantity` | **事件完成後的累積成交量**；初始為 0；不是僅這次成交量 | 所有事件必填 integer，0 到 quantity；另受事件狀態關係限制 | `0` |

依事件種類才出現的欄位：

| 條件式 JSON key | 中文意義 | 型別與何時必填 | 範例 |
|---|---|---|---|
| `fill_number` | 本事件對應這張訂單的第幾筆 fill；和外層 order_id 一起找到未來 fills row | positive integer；ORDER_PARTIALLY_FILLED／ORDER_FILLED 必填 | `1` |
| `fill_price` | 本次 fill 的每單位實際成交價；不同於委託限價 price | 固定兩位小數 decimal string；兩種成交事件必填 | `"100.00"` |
| `cancelled_quantity` | 本次取消的剩餘委託量，等於 quantity − fill_quantity | nonnegative integer；ORDER_CANCELLED 必填 | `6` |

Event-specific additions:

| Type | Required additional keys | Invariant |
|---|---|---|
| `ORDER_CREATED` | none | `fill_quantity = 0`. |
| `ORDER_PARTIALLY_FILLED` | `fill_number` positive integer, `fill_price` two-decimal string | `0 < fill_quantity < quantity`. |
| `ORDER_FILLED` | `fill_number` positive integer, `fill_price` two-decimal string | `fill_quantity = quantity`. |
| `ORDER_CANCELLED` | `cancelled_quantity` nonnegative integer | `cancelled_quantity = quantity - fill_quantity`. |

`fill_quantity` is the cumulative filled quantity after the event. The transition payload deliberately does not carry the quantity executed by only this event; per-fill executed quantity belongs to the future `fills` row. `fill_number`, together with the structural `order_id`, identifies that fill within the order.

Do not duplicate fields already carried structurally by the transition row: `order_id`, `status_change_version`, `previous_status`, `current_status`, `transition_type` and `created_at`. Payloads must contain no secrets/PII and must be at most 16 KiB at the service boundary.

<a id="json-outbox-payload"></a>

### 5.4 `outbox_events.payload` — APPROVED; initial writer verified, relay pending

Purpose: canonical event body published later to Kafka topic `trading.order-events.v1`.

本欄存的是**業務資料 object**。ORDER_CREATED 是下面 7 keys；成交／取消再依事件加入條件式欄位。以下逐 key 定義與 [transition payload](#json-transition-payload) 相同，不需要另外發明 outbox 專用版本。

| JSON key | 中文意義／來源 | 核准型別與必填條件 | 範例 |
|---|---|---|---|
| `account_id` | 事件所屬訂單的帳戶；初始 writer 複製 request_payload | 所有事件必填 string；沿用 §5.1 的識別碼契約 | `"SIM-001"` |
| `action` | 該訂單的買賣方向，不是事件種類 | 所有事件必填 `BUY`／`SELL` string | `"BUY"` |
| `order_type` | 該訂單的下單方式 | 所有事件必填 `LIMIT` string | `"LIMIT"` |
| `quantity` | 該訂單原始委託數量；部分成交後仍不變 | 所有事件必填 positive integer | `10` |
| `price` | 該訂單每單位限價；不是 fill_price | 所有事件必填固定兩位小數的 decimal string | `"100.00"` |
| `symbol` | 該訂單交易的商品代碼 | 所有事件必填 string；沿用 §5.1 的商品代碼契約 | `"AAPL"` |
| `fill_quantity` | **事件完成後的累積成交量**；初始為 0；不是僅這次成交量 | 所有事件必填 integer，0 到 quantity；另受事件狀態關係限制 | `0` |

| 條件式 JSON key | 中文意義 | 型別與何時必填 | 範例 |
|---|---|---|---|
| `fill_number` | 本事件對應這張訂單的第幾筆 fill；和外層 order_id 一起找到未來 fills row | positive integer；ORDER_PARTIALLY_FILLED／ORDER_FILLED 必填 | `1` |
| `fill_price` | 本次 fill 的每單位實際成交價；不同於委託限價 price | 固定兩位小數 decimal string；兩種成交事件必填 | `"100.00"` |
| `cancelled_quantity` | 本次取消的剩餘委託量，等於 quantity − fill_quantity | nonnegative integer；ORDER_CANCELLED 必填 | `6` |

ORDER_CREATED 的完整 outbox payload 範例：

```json
{"account_id":"SIM-001","action":"BUY","order_type":"LIMIT","quantity":10,"price":"100.00","symbol":"AAPL","fill_quantity":0}
```

`event_id`、`event_type`、`order_id`、`status_change_version`、`created_at`、`published_at` 是 outbox 的外層 columns，**不是這份 payload 的 keys**。`schema_version` 只存在未來 Kafka envelope，沒有內層 `payload_version`。

<a id="json-kafka-envelope"></a>

#### 5.4.1 未來 Kafka envelope：外層 keys 與 data 的差別

| JSON key | 型別／必填 | 中文意義與資料來源 |
|---|---|---|
| `schema_version` | integer，必填；此格式為 `1` | 訊息格式版本；不是訂單 version，不是 DB column |
| `event_id` | string，必填 | 事件的穩定去重 ID，來自 outbox_events.event_id |
| `event_type` | string，必填；§4 的 4 種事件之一 | 這則訊息表示什麼業務事件，來自 outbox_events.event_type |
| `order_id` | string，必填 | 事件所屬訂單，來自 outbox_events.order_id；亦作 Kafka message key，後者是 transport metadata |
| `status_change_version` | positive integer，必填 | 該訂單的狀態變更版本，來自同名 outbox column |
| `occurred_at` | UTC RFC 3339 string，必填，以 Z 結尾 | 以 outbox_events.created_at 編碼的事件時間；不是 broker 收到訊息或 published_at 的時間 |
| `data` | object，必填 | 原封不動裝入上面的 outbox payload；所有 data.account_id 等內層 keys 的意義見本節兩張表 |

The approved outbox_events.payload JSONB equals the referenced order_transitions.payload, and event_type equals transition_type. The initial ORDER_CREATED writer now uses the same transition_payload object and matching type; the API test verifies equality. DB constraints do not enforce cross-table payload/type equality. A relay is not yet implemented; the future relay constructs this Kafka envelope from the fixed columns and stored payload:

```json
{
  "schema_version": 1,
  "event_id": "uuid-text",
  "event_type": "ORDER_CREATED",
  "order_id": "uuid-text",
  "status_change_version": 1,
  "occurred_at": "2026-09-01T00:00:00.000000Z",
  "data": {
    "account_id": "SIM-001",
    "action": "BUY",
    "order_type": "LIMIT",
    "quantity": 10,
    "price": "100.00",
    "symbol": "AAPL",
    "fill_quantity": 0
  }
}
```

`occurred_at` is the outbox row's `created_at`, encoded as UTC RFC 3339 with `Z`. Object-key ordering is irrelevant; decimal values remain strings. Same `event_id` with the same canonical envelope is a duplicate no-op; the same `(order_id, status_change_version)` with different `event_type` or `data` is an integrity failure. The complete envelope must be at most 32 KiB at the producer boundary.

<a id="json-other-http-response"></a>

### 5.5 其他 API JSON：與保存的 response_body 分開查

<a id="json-account-response"></a>

#### GET /v1/accounts/{account_id} → 200（目前已實作）

| JSON key | 目前 JSON 型別 | 中文意義／來源 |
|---|---|---|
| `account_id` | string | 查詢的帳戶 ID |
| `total_cash` | number | accounts.total_cash：總現金，包含已預留部分 |
| `reserved_cash` | number | accounts.reserved_cash：已預留現金 |
| `available_cash` | number | total_cash − reserved_cash：可用現金；不是 DB column |

```json
{"account_id":"SIM-001","total_cash":100000,"reserved_cash":30000,"available_cash":70000}
```

這支 route 目前將 Python Decimal 交給 FastAPI 編碼成 JSON number；它不是 §5.1／§5.2 的兩位小數 price string 契約，也不存進 idempotency_requests。帳戶不存在回 `404`、`{"detail":"Account not found"}`；detail 的意義是找不到指定帳戶。

#### GET /v1/orders/{order_id} → 200（巢狀 account 四欄與最小 GET 契約已驗證）

2026-09-08 Andrew 已選擇在原有三個訂單欄位旁新增 `account` 物件。以下欄位全部必填；帳戶欄位不可平鋪在頂層，也不可把 `reserved_cash` 寫成 `reserve_cash` 或 `available_cash` 寫成 `cash_available`。

| JSON 路徑 | 型別與中文意義／來源 | 目前 enforcement |
|---|---|---|
| `order_id` | string；查到的 orders 訂單 ID | route／existing test 已通過 |
| `status` | string；orders 目前狀態，精確合法值見 §4；初始為 OPEN | route／existing test 已通過 |
| `fill_quantity` | integer；orders 累積成交量；初始為 0 | route／existing test 已通過 |
| `account` | object；該訂單所屬帳戶查詢當下的現金狀態 | route／四欄test已通過 |
| `account.account_id` | string；由 orders.account_id 找到的 accounts.account_id | route／existing test 已通過 |
| `account.total_cash` | number；accounts.total_cash，包含預留部分 | route／existing test 已通過 |
| `account.reserved_cash` | number；accounts.reserved_cash，整個帳戶的預留總額 | route／existing test 已通過 |
| `account.available_cash` | number；total_cash − reserved_cash；不是 DB column | route／existing test 已通過 |

金額沿用 account GET 的 JSON number 型別；計算仍使用資料庫 exact NUMERIC／Python Decimal。帳戶值是 GET 查詢當下的狀態，不是 POST 保存回應，也不是僅此張訂單的 reservation。原有 missing-order 契約保持 `404`、`{"detail":"Order not found"}`。

以下為既有測試資料下的核准目標範例（`order_id` 以 POST 實際產生值替代）：

```json
{
  "order_id": "<server-generated-order-id>",
  "status": "OPEN",
  "fill_quantity": 0,
  "account": {
    "account_id": "SIM-001",
    "total_cash": 100000,
    "reserved_cash": 31000,
    "available_cash": 69000
  }
}
```

Completed account-state slice（2026-09-08）：handler選取所屬帳戶並回傳巢狀四欄；test移除額外POST cash，四個帳戶assertions與原有order assertions全部通過。Exact existing／missing pair2 passed；fixture證據為SIM-001、total100000／reserved31000／available69000，missing404亦通過。第11項完成。完整suite在修正accounts reset後為68 passed，五表0-row cleanup也已查證；目前第12項SQL reconciliation已通過，explain-back於2026-09-09依使用者要求放行，不重開本GET切片。查詢時效仍需另取證據，不把單次建立後查詢当成所有freshness驗收。

#### POST validation 422（不保存到 idempotency_requests）

| JSON 路徑 | 型別 | 意義與契約邊界 |
|---|---|---|
| `detail` | array of objects | 一個或多個 request validation 錯誤；不是保存的業務錯誤 detail string |
| `detail[].loc` | array of string／integer | 錯誤的欄位路徑；目前 quantity test 明確要求 `["body", "quantity"]` |
| `detail[].type` | string | framework 的錯誤種類代碼；目前專案未固定每種代碼字串 |
| `detail[].msg` | string | framework 的人類可讀說明；目前專案未固定每種訊息字串 |
| `detail[].input` | 任意 JSON 值（可能出現） | framework 回報的無效輸入；不是本專案規定的必填 key |
| `detail[].ctx` | object（依錯誤類型可能出現） | framework 的錯誤參數，例如數值門檻；內部 keys 隨錯誤種類變動，不是本專案核准的固定 schema |

此格式由安裝的 FastAPI／Pydantic 產生；專案只把 test 明確斷言的部分當穩定 acceptance，不能把一次輸出的所有 framework keys 升格成業務契約。

#### GET /live → 200（目前已實作）

| JSON key | 型別／值 | 中文意義 |
|---|---|---|
| `status` | string：`"Live endpoint is working!"` | liveness 回應文字；與 orders.status、response_status 都不同；不保證 DB 或 Kafka 健康 |

<a id="planned-tables"></a>

## 6. APPROVED BUT NOT IMPLEMENTED

### 6.1 Planned `fills` row contract

Grain: one `order_id × fill_number` row. `fill_number` starts at 1 and increases within one order, so no separate global fill identifier is stored. Each row must retain its own positive `fill_quantity` and exact two-decimal `fill_price`, while `orders.fill_quantity` and transition payload `fill_quantity` remain cumulative totals. The required reconciliation is `SUM(fills.fill_quantity) = orders.fill_quantity`. Omitting per-event quantity from transition JSON does not remove it from the authoritative fills ledger.

Minimum planned fields:

| 規劃欄位 | 中文意義／資料來源 | 已核准的值／型別語意 | 尚未實作的部分 |
|---|---|---|---|
| `order_id` | 這次成交屬於哪張訂單；與 fill_number 一起識別本次 fill | 對應既有訂單 ID | 實體 column、FK 與完整 migration 尚未建立 |
| `fill_number` | 同張訂單的第幾筆成交；不是全表流水號 | 正整數，從 1 起；與 order_id 組成複合 identity | 實體 integer 型別與連續性 enforcement 尚未落地 |
| `fill_quantity` | **只有本次成交的數量**；orders.fill_quantity 與事件 JSON 的同名 key 則是累積量 | 正數數量；每張訂單的此欄 SUM 要等於 orders.fill_quantity | 實體 column 與對帳 enforcement 尚未落地 |
| `fill_price` | 本次成交的每單位實際價格；不同於 orders.price 的委託限價 | 精確十進位、兩位小數 | 實體 NUMERIC precision／完整 constraint 尚未由 migration 固定 |
| `created_at` | 資料庫記錄這次成交的時間 | timestamp 語意 | 具體型別、NULL／default 與寫入方式仍待 migration 定義 |

`fills` 目前沒有已核准的 JSONB column。未來新增 JSON 欄位時，仍須依 §9.1 補逐 key 字典，不能把 transition 的 JSON 當成這張 table 已存在的 schema。

### 6.2 Post-core Ruby/Rails market-data bridge — approved, not started

The authoritative dashboard and plan added this extension on 2026-09-06. It starts only after all 56 core learning gates pass and does not change the Day 3 trading schema, synthetic prices, implicit `SIM-USD`, tradable-symbol set, or order/fill behavior. There are no Rails files, migrations, market tables or market-data tests in the current project, so none of the following may be described as CURRENT VERIFIED.

Approved ownership and boundary:

- one permitted official source supplies daily reference data for 5–10 securities in one market/currency;
- Rails alone owns future market-table migrations and writes; Rails models/controller/view read the local PostgreSQL copy;
- the Python/FastAPI trading core neither writes these tables nor treats their closing prices as order or fill prices;
- page loads read local data and never trigger an external fetch;
- invalid or failed updates preserve the last valid local data, and missing prices must never be converted to zero.

Approved logical market-observation grain: one `market × symbol × source trade date`. The physical table name, whether identity fields and daily observations are split across tables, and the same-day revision implementation remain unresolved. The future migration must establish uniqueness on that logical key and a traceable revision policy before this becomes a physical table contract.

Approved field semantics, with physical column names/types still pending R1:

| Logical field | Approved meaning | Required representation / unresolved enforcement |
|---|---|---|
| symbol | Source security identifier | String, preserving leading zeros; length and normalization are unresolved. |
| market | Market namespace used in the logical unique key | Exact enum/code set is unresolved. |
| currency | Currency of the reference close | Stored separately from market and price; exact code domain is unresolved. |
| name | Source security name | String; nullable/length/normalization rules are unresolved. |
| close | Daily reference closing price | Exact decimal, never binary float; missing stays missing rather than `0`. Precision/scale and nullability are unresolved. |
| source | Provenance of the observation | Stored explicitly; identifier/domain is unresolved and must be rechecked at implementation time. |
| trade date | Trading date supplied by the source | Separate from fetch time; future physical type should be a date, but the migration is not yet approved. |
| fetched time | Time the source result was retrieved | Separate from trade date; timezone/default ownership is unresolved. |
| availability/update state | Distinguishes valid data from closure, suspension, missing price and unknown reason when the source supports it | Enum, reason fields and nullability are unresolved; unsupported reasons remain unknown rather than invented. |
| revision evidence | Records that a valid same-key observation was revised | Exact columns/history strategy are unresolved; a repeated unchanged sample must remain idempotent. |

An ingestion run/audit contract is also approved in principle: each run reports inserted, updated and rejected counts; retains traceable source-sample lineage; records the last successful update and the latest failure; and treats timeout, `429`, missing fields and incompatible formats as explicit outcomes. Its table versus structured-log ownership, grain, fields, retention and sensitive-data policy are unresolved. Source samples and logs must not contain credentials or unnecessary personal data.

### 6.3 Remaining approved trading-core behavior

Day 3 current SQL reconciliation boundary: create one new `OPEN` BUY with `fill_quantity=0`, then compare that order's persisted cost with its owning account's reservation delta. This is an initial whole-order reservation test, not a partial-fill test. `quantity * price` and `(quantity - fill_quantity) * price` are equivalent for this slice. Available-cash before-after is an equivalent check only while total cash is unchanged; later fill settlement needs its own acceptance. Existing fixture reservations are baseline state, not obligations created by this request.

- The successful initial outbox path, one test-only late-outbox rollback and the initial zero-fill BUY reservation reconciliation are verified. Broader failpoint coverage, cross-connection durability and fill/cancel lifecycle reconciliation remain approved future gaps.
- Rejection cleanup and same-key retry after both funding and account creation are verified in focused API tests; successful-response replay remains retained, while rejected results remain unsaved. Concurrent first-use arbitration is still unresolved.
- Nested account initial GET, initial zero-fill SQL reconciliation and full69-test regression pass; item12 explain-back was explicitly waived on2026-09-09; Day3 complete.
- Full/partial fills, cancel, positions, reconciliation and lock-order rules.
- Outbox relay, Kafka consumer, projected timeline and rebuild/gap handling.
- Continuous transition versions and agreement among current order, transition and event.

The first three bullets describe completed initial-slice evidence. Only the remaining fill/cancel, relay/projection and version-continuity work must stay planned until code and evidence exist.

## 7. Decision and implementation-gap register

| ID | Decision or remaining implementation gap | Current evidence | Required resolution |
|---|---|---|---|
| DC-001 | Transition enum CHECK is verified in the rebuilt isolated test DB | `check_transition_type_domain_valid` is present after clean reapply | Shared/non-test deployments would still require a forward migration rather than editing applied history |
| DC-002 | Transition length/domain CHECK names are distinct | Clean isolated downgrade/upgrade succeeded | Keep the two names distinct in future migrations |
| DC-011 | `outbox_events.event_type` enum CHECK is implemented | Follow-up revision `d3f7a4c91e20` is applied in the isolated test DB; `ORDER_ACCEPTED` hits `check_outbox_event_type_domain_valid` | Keep the four-value outbox domain synchronized with transition type; all other values remain invalid |
| DC-003 | Status spelling drift is resolved in active specifications | Canonical: `PARTIAL_FILLED`, `CANCELLED` | Keep regression checks so invalid aliases do not return |
| DC-004 | Runtime field naming is resolved for active specifications | Canonical: `total_cash`, `reserved_cash`, `available_cash`, `quantity`, `fill_quantity`, `price` | Historical learning-log text may retain old wording, but normative sections must not |
| DC-005 | Initial transition/outbox seven-key payload is produced and verified; full future-event validation remains pending | JSONB remains structurally unconstrained in DB; only outer Kafka `schema_version` versions the format | Enforce in service models/tests; DB stays JSONB rather than duplicating every JSON rule |
| DC-006 | Idempotency normalized JSON v1 contract is partially implemented in route source | Route persists the six-key model dump, formats `price` to two decimals and directly compares JSONB; several approved bounds/normalizations remain absent | Add the remaining account/symbol/key/payload boundary enforcement without changing the approved six-key shape |
| DC-007 | `completed_at` is not constrained to saved response completion | Applied DB permits inconsistent combinations | Decide service invariant and whether DB CHECK is required |
| DC-008 | `orders.updated_at` does not auto-update | Column has insert default only | Define service update responsibility or trigger policy |
| DC-009 | Logical currency is approved as implicit `SIM-USD`, but not stored | Cash/price use `NUMERIC(12,2)` | Do not add a currency column unless multi-currency enters product scope |
| DC-010 | All four transition constraint groups are verified | PostgreSQL-backed evidence covers legal initial/later rows, version rules, status/type domains, duplicate composite PK and missing-parent FK; the combined idempotency-plus-transition regression recorded `17 passed` | Keep the completed transition and outbox groups green; their current sources and recorded evidence are already present |
| DC-012 | Atomic LIMIT BUY item 10 is complete only at the current learning-slice scope | Recorded tests verify: successful writes/replay, both rejection/retry paths, transition/outbox persistence and one late-outbox rollback; all basic successful-path writes are inside the transaction | Item 11 initial GET, item 12 initial zero-fill reconciliation and the 69-test regression are complete; item 12 explain-back was explicitly waived on 2026-09-09 and must not be reopened. Broader failpoints, cross-connection durability, fill/cancel lifecycle reconciliation and the separate approved SELL position path remain pending |
| DC-013 | Rejected requests do not occupy keys | Focused tests verify unknown-account `404` and insufficient-cash `409` leave no idempotency row and that the same key/payload succeeds after account creation or funding | Keep both regressions green; rejected results stay unsaved and successful `201` replay remains canonical |
| DC-014 | Existing pending idempotency rows lack completed-result handling | Current source does not verify completed_at/non-NULL status/body before JSONResponse replay | Define completion/ownership semantics; never treat an unfinished record as a completed result |
| DC-015 | Concurrent first use of one idempotency key is not arbitrated in current source | Route performs unlocked SELECT then INSERT and has no upsert/retry or unique-violation mapping | Define one-winner behavior and map the losing request to deterministic replay/conflict rather than an unhandled DB error |
| DC-016 | Route price normalization is not single-source or reconciliation-safe | JSON snapshot/response rounds with Python formatting, reservation uses the original arbitrary-scale Decimal, and `orders.price` is independently coerced to `NUMERIC(12,2)` | Reject non-two-decimal inputs or quantize once with an approved rounding rule before payload comparison, reservation and order persistence |
| DC-017 | Post-core Rails market-data contracts are approved only at the logical level | Dashboard/plan define ownership, required semantics, logical uniqueness and failure behavior, but no Rails project, physical table names, migrations, exact types or tests exist | In R1, choose the physical table split/names, decimal precision, nullability, enum domains, timestamps, revision history and ingestion-run persistence before describing any market table as implemented |
| DC-018 | Initial nested-account GET contract verified; item11 complete | Exact pair2passed including account identity, cash100000/31000/69000, original order fields and missing404 | Preserve this contract; later-mutation freshness remains a separate evidence boundary, not a reason to reopen the completed initial slice |
| DC-019 | **RESOLVED 2026-09-10:** flow document reconciled under Andrew’s explicit retrospective-scan request | project_flow.html now matches current transaction/reservation/idempotency/initial-event/GET sources, inventory and70-case collection; outdated runtime snapshots and dead links removed | Recheck source plus approved decisions when related files change; code-document consistency inventory records the scan. The scheduled automation still edits only this spec; it must flag cross-file drift for the interactive task rather than silently change other files |

## 8. Verification sources

Primary current-state evidence used for this cumulative spec:

- `migrations/versions/2026_08_12_c6c622f0b972_create_accounts_table.py`
- `migrations/versions/2026_08_21_f14b8c2e7d90_create_orders_table.py`
- `migrations/versions/2026_08_26_8c2f39a71d4e_add_idempotency_outbox_schema.py`
- `migrations/versions/2026_09_03_d3f7a4c91e20_add_outbox_event_type_domain.py`
- isolated test DB `information_schema`, `pg_constraint`, `pg_indexes`, Alembic revision `d3f7a4c91e20`
- `app/routers/accounts.py`, `app/routers/orders.py`, `app/database.py`, `app/main.py`
- current constraint/API tests; collect-only on 2026-09-09 found 69 tests, while the latest full-suite execution evidence is the dashboard/plan's recorded2026-09-10 `70 passed` and the last focused schema regression remains the recorded `27 passed` idempotency/transition/outbox run
- `job_search/de_transition_daily_dashboard.html` for progress truth
- `job_search/de_transition_plan.md` for approved future architecture
- `docs/project_flow.html` for current-versus-planned naming warnings

The 2026-09-09 read-only database check found the isolated `simulate_trading_test` at Alembic revision `d3f7a4c91e20`, with the same five application tables, 36 application columns and 40 constraints; all five business tables contained zero rows at the check boundary. The Ruby/Rails market-data extension exists only in the dashboard/plan and has no current database objects.

### 8.1 2026-09-07 資料字典核對證據

- 從現有 migration AST 擷取 table／Column，與 §3 逐欄比對：5 張業務 table、36 個欄位完全對應；4 個 JSONB 欄位都有明確的字典入口。沒有新增 schema。
- 以 CreateOrderRequest 的 6 個欄位核對 request 字典；成功 response 是該 6 keys 加 order_id；錯誤HTTP body是detail（9/7起拒絕不保存，取代當時保存錯誤的假設）；transition／outbox 的共同 7 keys 及 3 個條件式 key 定義一致。
- 6 組 fenced JSON 範例均可解析，keys 與相應字典相符；Kafka data 等於所示 outbox payload。14 個 anchor 唯一，24 個內部連結皆能解析。
- 用相同 CreateOrderRequest 在獨立、只做 validation 的記憶體 FastAPI route 驗證 quantity=0：回 422，錯誤項有 type／loc／msg／input／ctx，loc 為 body → quantity。沒有呼叫專案業務 route 或連線 DB；ctx 等 framework keys 仍不是新增的固定業務契約。
- 額外執行既有 `test_architecture_semantics_are_decision_complete`，停在未修改的 `job_search/de_transition_plan.md` 不含 `payload_version` 字串的 assertion。這是跨文件測試限制，不能回報整套驗證全綠；本次沒有為了通過該字串檢查而改 plan、dashboard、test 或新增內層版本欄位。
- 本支線由單執行緒核對欄位完整性、語意與範例、契約一致性、主線隔離；沒有啟動 agents，沒有 DB mutation 或新的 Day 3 完成判定。

### 8.2 2026-09-08 增量核對證據（歷史快照）

- 當時dashboard為2/56、Day3 11/12；此為9/8歷史快照。9/9末題已由Andrew明確授權放行，Day3已完成，不重開此門檻；目前Days1–4完成、Day5 active。
- Current `app/routers/orders.py` implements the nested-account authoritative GET, and `tests/test_orders_api.py` includes the existing/missing GET pair plus the initial zero-fill BUY reservation reconciliation. No new table, column, enum or JSON key was introduced.
- In-memory AST compile passed for 18 Python files; collect-only found 69 tests. This automation did not execute DB-writing pytest targets and relies on the dashboard/plan's already-recorded full-suite `69 passed` evidence for runtime acceptance.
- A read-only test-DB transaction verified revision `d3f7a4c91e20`, five business tables, 36 columns, 40 constraints and zero rows in all five tables. No migration or data mutation was executed.
- 當時project_flow的POST/GET敘述過期，記為DC-019；已於9/10依明確授權同步並結案，見§8.4。

### 8.3 2026-09-09 驗證及2026-09-10進度補記

- 2026-09-10進度補記：dashboard為4/56，Day4委託交付10/10完成；Day5 manifest active 0/5。下方19檔／69例為9/9歷史驗證，不能當成9/10重新執行。
- Day4 HTML/CSS/browserJS and UI/API/test-DB verification completed; existing public APIs and all table/JSON contracts remain unchanged.
- Current app/static/index.html provides account/BUY/order lookup/recovery; GET / is mounted and homepage tests pass. See day4_browser_acceptance.md for actual evidence and transaction limits.
- In-memory AST parsing passed for 19 Python files and collect-only found 69 tests. The isolated test database was queried in a read-only transaction at revision `d3f7a4c91e20`; it still has five business tables, 36 columns and 40 constraints, with zero rows in all five tables.
- DC-012 is corrected so the completed/waived Day 3 gate is not listed as pending. Broader failpoints, cross-connection durability, fill/cancel reconciliation, concurrent idempotency ownership, price canonicalization and the separate SELL position path remain unresolved or approved-but-not-implemented as already classified above.

### 8.4 2026-09-10 回溯文件一致性掃描

- 本次掃描26個implementation/test/migration artifacts，22個Python檔可解析；pytest collect-only為70 cases，其中order API13、browser入口1、virtual_user0。不是本次70-pass宣告。
- 遷移source共有4 revisions、5張業務表、36欄；本輪未連線DB，不更新DB驗收日期或row counts。
- 已依現有routes與9/10既有驗收修正flow正文：冪等、交易context、資金預留、初始transition/outbox、巢狀account GET、SQL順序／變數、測試與檔案清單、migration連結；DC-019結案。
- Day5本地manifest採用build_manifest(account_id,batch_id,seed)，三參數必填；兩種ID皆1–64字元字串，不額外限制空白或字元。這不是API input驗證的變更；API尚未落地的限制仍保留在§5.1。完整當前manifest見[契約](virtual_user_manifest.md)。
- 詳細修正與尚未完成範圍見[一致性盤點](code_document_consistency.md)。既有Day1–4完成及Day5 0/5不變。

2026-09-10最新Day5決定：Andrew明確要求保留現有程式並採用quantity1–100，100筆固定單價10.00的成本上限連動為100000.00；撤回本地manifest舊1–3／3000要求，先前待決已結案。seed42成本48910.00符合新契約。最新test為1 passed，原空清單／少筆／多欄缺口已補正；collection仍為71例，未重跑DB suite。未改public API／DB契約。後續HTTP100筆成功驗收需先確認隔離帳戶available_cash覆蓋該批實際總額，不保證原70000足以支付任意合法批次。現行完整證據見[manifest](virtual_user_manifest.md)。

2026-09-11測試證據更新：manifest已有兩例，精確2 passed、collect-only72；跨批次比較只驗同索引不等，整批key隔離仍需補驗收。以key循環位移的記憶體替代輸出證明目前會漏抓100個重疊key；正式Python與DB未改。契約、Day5 0/5及1-1均不變；詳見manifest最新證據。

2026-09-11最新修正版：manifest tests為2 passed，第38行已正確檢查third key不在第一批完整清單；循環位移重複key案例已能抓到，可重現與批次隔離缺口結案。接續seed邊界，1-1未完成；不變更契約／後端／DB，詳見manifest最新證據。

2026-09-11 seed測試草稿最新狀態：pytest import與拼錯的parameterize裝飾器被放在build_manifest上，精確pytest為1 collection error，未執行tests。需移到tests/test_virtual_user.py的新test函式並改parametrize；七個非法seed值選擇正確。原輸入契約、先前重現／隔離完成證據及Day5 0/5不變。

2026-09-11 seed第二版最新狀態：production已移除pytest，parametrize拼字及檔案位置已修；既有重現性test無seed參數而回報function uses no argument seed，仍1 collection error。需另建接收seed並驗ValueError的test，保留既有成功／重現性tests；契約未變。

2026-09-11 seed第三版最新狀態：已正確收集並執行九例，7 failed、2 passed；非法seed均由內部拋ValueError，test缺pytest.raises，需在既有呼叫外宣告預期例外。不是production錯誤；當時要求的正常seed兩端點tests後續已依Andrew決定撤回。契約未變。

2026-09-11 seed第四版最新狀態：精確9 passed，非法seed7例正確使用pytest.raises；第32行訊息assert位於with內拋例外後，未執行。不同ValueError訊息的記憶體替代案例仍PASS，需將訊息assert移至with外。已完成拒絕行為保留，不增加API契約，Day5 1-1仍未完成。

2026-09-11 seed第五版最新狀態：9 passed，訊息assert已移出with且錯誤訊息替代案例被拒絕，非法seed驗收完成。當時提出的正常清單test參數化0／2**32-1要求已依Andrew後續糾正撤回，保留原正常test與9 passed。Day5仍0/5、1-1。

2026-09-11現行seed驗收決定：依Andrew糾正，不新增正常seed兩端點測試，不把正常test改為參數化，也不要求10 passed。現有正常清單／重現與七個非法seed案例共9 passed保留，seed驗收依此完成；seed合法範圍0..2**32-1、內部驗證及API／DB均不變。舊兩端點待辦退休，Day5 1-1剩餘ID／random／成本驗收。

2026-09-11接續核對：精確pytest重新取得9 passed（0.02s），seed驗收維持完成。當前1-1先補兩種ID的輸入契約測試：分別改account_id或batch_id，另一ID與seed保持合法；當時要求的空字串、65字元及非字串拒絕已驗證；1／64字元與空白／Unicode／底線合法值額外測試要求後續已撤回。這是既定ID驗收，不新增seed正常端點要求。正式Python由Andrew修改；完成後由Codex跑同一test檔。global random獨立性與Decimal成本仍待後續驗收。測試組織澄清：不要求seed、account_id、batch_id各自新增test函式；可擴充既有test_invalid_manifest，以同一parametrize函式承接三種輸入的獨立案例。每列只讓一個參數非法，其餘合法；若檢查錯誤訊息，預期訊息需隨案例變化。全部manifest行為也可放同一函式，但需正確區分成功與預期例外，單一未參數化test的首個失敗會中止後續檢查。函式数量不是驗收門檻，原seed案例覆蓋與既定契約保留。

2026-09-11三參數修正版：精確pytest為22 passed（0.04s）；直接逐列核對錯誤來源為seed7例、account_id7例、batch_id6例，全部符合各組目的。batch案例已使用合法整數seed，兩種ID的65字元拒絕均通過；先前遮蔽問題已解決，不重開。非法輸入這一段完成；in集合寫法保留，不強制拆test或改訊息欄位。2026-09-11 Andrew最新驗收決定：不再新增合法account_id／batch_id測試，撤回1字元、64字元及空白／Unicode／底線原值保留的額外測試要求；不得要求參數化改寫既有正常清單test。保留現有22例（seed7、account7、batch6拒絕案例與原正常清單／重現性2例），seed與ID輸入驗收依目前範圍完成。兩種ID的合法範圍與保留原值契約不變；這是省略額外測試的決定，不能將非法輸入被拒絕記成已證明所有合法輸入成功。先前正常seed端點豁免維持；剩餘global random獨立性與Decimal成本驗收，不取消既有輸出／重現性測試。全局4/56、Day5 0/5、1-1第1/5項；本次完成ID驗收範圍確認，關卡+0。合法ID額外測試已撤回；global random獨立性及Decimal成本仍待完成；全局4/56、Day5 0/5、1-1第1/5項，本次關卡+0，新增6個batch與1個account長度拒絕有效證據。Codex未改Python。

2026-09-11當前切片仍為Day5 1-1，接續Decimal總成本驗收：在既有tests/test_virtual_user.py的test_build_manifest保留所有assert，於for之前建立Decimal零總額、每筆累加quantity乘Decimal(price)，於for結束後檢查總額不超過Decimal的100000.00；不新增函式或正常seed／ID案例。使用工時乘費率的不同業務範例引導。當輪只讀核算seed42之100筆總额為48910.00，符合上限；教學類比亦執行通過。這不是正式新增成本assert已完成，存檔後由Codex跑tests/test_virtual_user.py，沿用原test時預期仍22 passed。random已有兩項行為探針證據及教學結論，依Andrew糾正不再重講；正式random test尚未新增的事實保留，不自行宣稱豁免。仍在同一1-1內推進可獨立完成的成本部分，未進2-1。全局4/56、Day5 0/5、1-1第1/5項，本次關卡+0，未改Python。

2026-09-11 Andrew糾正：global random獨立性已討論，停止重複getstate／setstate／first與second插入位置等同一段教學。前輪已給完整抽色類比及局部映射，且實際記憶體探針已確認兩項獨立性行為PASS；這些成果必須沿用，不因正式test存檔未變而再次把同一教學當成新工作。正式test是否落地另作事實記錄，不能混同為概念尚未講過；本句糾正不自行推定取消random驗收或完成整個1-1。後續若有新的具體疑問才針對差異回答。

前輪random教學已交付：已說明局部Random與全域random互不影響、狀態快照及恢復，並給過不同業務類比；依最新糾正不再重播。合法seed／ID額外測試豁免維持。

2026-09-11 1-1行為驗收完成：最新精確pytest為22 passed（0.03s），已包含每筆quantity乘Decimal(price)累加與迴圈後100000.00上限assert。cost以整數0初始化可精確與Decimal相加，第一筆後成為Decimal，不必為形式改寫。100筆、payload、批次隔離、重現性、輸入拒絕與成本由正式22例覆蓋；random雙向獨立性沿用已實跑2項探針證據，未宣稱納入永久pytest。合法seed／ID額外測試依Andrew決定省略。依當前已驗證行為結束1-1，不再將同一random教學或證據形式作重複關卡；驗證方式與永久回歸覆蓋的差異明列為限制。當時Day5為1/5、active2-1；現行進度見本頁最新驗收與子任務地圖。此段記錄9/11完成1-1的歷史成果。

2026-09-14 2-1行為驗收完成：最新test_manifest_response已以非201計rejected、201計succeeded；精確manifest pytest22 passed（0.04s），另6組離線sender案例全部PASS。涵蓋空清單、3筆201、201／409／timeout、404後201、timeout後201、100筆201；混合3筆正確回attempted3／succeeded1／failed2。URL、payload、header、順序、沒有重試及未改輸入均核對通過。6組是離線探針，不宣稱納入永久pytest或已送真實API。固定長度及狀態分類問題結案，不再重開；該輪2-1完成，當時Day5 2/5、active2-2第3/5項；現行進度见本頁最新驗收。

2026-09-14 2-2教學補正：上一則驗收後銜接只給文字步驟、漏附既定的不同業務完整範例，本輪補上工單POST→ID→GET範例。不得預設所有POST成功：先檢查status_code，僅201分支讀JSON的非空字串ID；非201、RequestError或缺ID不發GET。本段為9/14的歷史教學；其POST-only計數要求已於9/15退休。現行取order_id仍以POST201為前提，succeeded則依Andrew正向流程在整段通過後增加。範例以MockTransport驗證8種情況全通過，包括POST拒絕／timeout／缺ID／非物件JSON、GET成功／404／timeout／ID不符；沒有網路呼叫，未修改專案Python。後續自動銜接新切片也要附文字控制流與不同業務完整範例，不能只列outcome當引導。

2026-09-15 最新決定：Andrew確認只保留results裡每筆total_cost，不另外提供整批總額；撤回manifest_summary物件及其total_cost/count要求。回傳report只含attempted、succeeded、failed、results；每筆result保留total_cost，沿用現有單筆計算與原生Decimal，不因缺少全批加總或JSON序列化擋關。只需return report，不要求save_summary、output_path、JSON檔案或round-trip。先前整批加總與保存指引已退休，不再重播；已有單筆金額成果保留。這是回傳內容與輸出範圍的決定，不自行豁免其他POST→GET行為驗收，不宣稱2-2全部完成。Day5 1-1既有manifest成本上限測試與3-1隔離資金/SQL對帳責任不變。既有artifacts/virtual_user_summary.json占位檔不再使用、不列驗收，未刪除檔案。

前輪2-2分支引導已交付：包裹查回類比6組離線驗證通過；這是範例證據，專案現況依本頁最新檢查，不重播相同教學。

2026-09-15 GET例外捕捉範圍驗證完成：最新107行版本在79行try內解析JSON並於81行讀get_order_id，86行捕捉KeyError/TypeError，94行改比較已取出的變數。此次同一離線探針4/4 PASS：正常回attempted2/succeeded2/failed0；GET200回{}／null／[]皆回2/1/1，保留兩筆results、首筆verified=False且有error、第二筆verified=True，全部送出2筆POST。前輪取值在try外的問題已修正並結案，不再重開同一教學。重跑入口為simulate_trading目錄下.venv/bin/python /tmp/mini_get_response_probe.py；這是暫存離線探針，不是正式tests，無網路或DB操作。前輪manifest22 passed及其他report/GET驗證為原有證據，本輪未重跑。此次只確認當前GET取值修正，不宣稱整個2-2或真實100筆整合已完成；POST ID既有討論不重播、不因此自動豁免其他契約。Python及正式tests由Andrew修改，Codex未代寫。

2026-09-15 2-2及3-1驗收完成：最新115行版本74行保留str與非空判斷，原有空字串誤發GET與文字ID額外排除均結案；同一離線report探針21/21 PASS。接續既有FastAPI public routes與真實本機_test PostgreSQL，用seed42生成100筆，attempted100/succeeded100/failed0、100筆GET確認，orders/transition/outbox/idempotency各100筆且逐筆payload、ID、狀態與版本一致；保留資金增量48910.00、可用51090.00，與manifest及SQL成本一致。隔離帳戶起始total100000.00/reserved0；本輪帳戶與相關資料已rollback、殘留全0。測試使用TestClient與共用外層transaction/savepoints，不宣稱真實網路、跨連線commit durability、效能或fill/cancel驗證。證據為simulate_trading/docs/references/day5_api_sql_evidence_20260915.json；重跑入口在simulate_trading目錄下.venv/bin/python /tmp/mini_report_contract_probe.py及.venv/bin/python /tmp/mini_day5_integration_probe.py。探針屬驗證工具，不是正式pytest；原manifest22 passed為前輪證據，本轮未重跑。Python及正式tests由Andrew實作，Codex未修改。Day5 4/5，active4-1第5/5項；本次及今日完成+2（2-2、3-1），待Andrew完成資料流與成果界線說明。

2-2當前契約：在scripts/virtual_user.py擴充既有manifest_response(client, manifest)回傳完整report，只以return report回傳Python dict，不要求save_summary、輸出路徑或JSON檔案。依2026-09-15 Andrew採用的正向流程，頂層attempted統計實際嘗試筆數，succeeded統計POST與GET確認整段成功，failed統計其餘已處理失敗；每筆恰計一次且attempted=succeeded+failed。依2026-09-15 Andrew最新決定，report頂層只含attempted、succeeded、failed、results；筆數沿用attempted，不新增manifest_summary或整批總額。每個輸入依原順序保留一筆result，恰含idempotency_key、post_status（HTTP整數或未收到回應時null）、order_id（POST201回傳的非空字串，否則null）、get_status（HTTP整數或未取得時null）、verified（布林）、error（null或錯誤代碼）、total_cost（單筆金額，可保留原生Decimal）。單筆金額沿用既有計算位置；目前成功流程填quantity乘Decimal(price)，未計算時保留0占位，不代表已成交金額。仅POST201且取得有效order_id時，以同一同步client呼叫GET /v1/orders/{order_id}；200且JSON的order_id相符才verified=true。不能拿idempotency_key代替order_id；不讀DB、不重送POST或重試GET。HTTP失敗、RequestError、JSON無法解析或缺ID皆記錄結果並繼續；error記錄原因，成功為null；依Andrew明確忽略命名差異，接受目前post_json_error等標籤，不再以固定字串清單擋關。JSON解析失敗已有continue時可保留目前判斷順序。POST與GET完整通過才計succeeded，任一已處理失敗計failed；GET失敗可使整段failed，但不能據此認定訂單未建立。依2026-09-15最新決定，不要求存檔或JSON序列化；以離線client直接驗證回傳report的內容、mixed POST只查成功ID、GET成功／404／timeout／ID不符仍續行。不要求重驗GET回應的所有業務欄位或DB對帳；3-1才做真實隔離環境100筆。程式與正式tests由Andrew寫，Codex安全驗證。

2-1 **歷史驗證（有界 client 切片，2026-09-14；現行2-2以上方契約為準）**：當時 source 的實際函式名是 `manifest_response(client, manifest)`；先前建議的 `send_manifest` 不是 API 或函式命名契約。函式沿 manifest 實際長度依序送 `POST /v1/orders`，JSON 只送 `row.payload`，`Idempotency-Key` header 使用 `row.idempotency_key`；`201`（含成功重播）計入 `succeeded`，其他 HTTP status 或 `httpx.RequestError` 計入 `failed` 並繼續。它不自行重試、修改 manifest、建立／關閉外部 client 或讀 DB。回傳恰含 `attempted`、`succeeded`、`failed`，其中 `attempted = succeeded + failed`；空清單三項皆 0。`failed` 表示未確認成功，timeout 不證明伺服器未建單。dashboard／plan 記錄六組離線 sender 案例通過；本次另以離線 client 重驗空清單及 `201`／`409`／timeout 混合計數通過。正式 `tests/test_virtual_user.py` 的 22 例只覆蓋 manifest，sender 案例尚未成為永久 pytest。該段為9/14的階段證據；9/15已有逐筆results與POST→GET整段計數，現行進度及驗收以上方2-2契約為準，檔案持久化已取消。隔離環境 100 筆與對帳仍留 3-1；本切片不變更後端 API、table 或 JSONB 契約。

## 9. Daily update rule

The scheduled automation updates this file only when actual project evidence changes. Every update must:

1. re-read applicable `AGENTS.md`;
2. verify dashboard progress and current saved source;
3. compare migration source with the isolated applied schema when relevant;
4. keep CURRENT, APPROVED and UNRESOLVED claims separate;
5. never convert a fixture or proposed example into a formal payload contract without approval;
6. preserve existing unresolved items until evidence closes or supersedes them;
7. avoid modifying code, migrations, tests, database state or other documents.

### 9.1 欄位字典的維護驗收（2026-09-07 起）

- 每個已建立業務 table 都要列全量 columns，逐欄寫中文意義、型別／NULL／預設、來源與限制；不得只用用途段落取代欄位表。
- 每個 JSONB column 都要從 table 欄位列連到自己的 JSON 資料字典。逐 key 寫名稱、型別、必填／條件式、中文意義與來源，並有完整內容範例；不得只列 key 名或只寫同另一份 payload。
- request、成功 response、錯誤 response、transition payload、outbox payload、Kafka envelope 必須分開；條件式欄位要說明適用事件。response_payload 等查找詞必須導到實際名稱，不新增不存在的 schema。
- 核對範例 keys 與字典完全對應；維持 migration columns 全覆蓋，以及 transition/outbox payload 定義一致。JSON SQL NULL、JSON null、缺 key 與空 object 不混稱。
- 定義缺口標成 UNRESOLVED，已核准但未實作標成 APPROVED；不可從測試 fixture 猜成新契約。本節取代「只列 payload 名稱、範例或 key 清單就算規格完整」的做法。
- 本次只補文件可查閱性與既有欄位意義；沒有新增 table／column／JSON key、沒有推進 Day 3、沒有修改主線程式與測試。資料庫驗收日期仍沿用上方原始證據，未把 source 靜態核對說成新 DB PASS。

Day4 COMPLETE2026-09-10: root HTML, account/BUY/order lookup/recovery, actual test-DB browser validation and delegated explanation delivered. Active Day5 Python; no new public API contract or independent frontend mastery claimed.
