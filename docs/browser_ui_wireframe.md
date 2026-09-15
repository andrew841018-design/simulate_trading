# Day 4 — 最小交易介面架構與 wireframe

2026-09-15進度：Day4 10/10完成，全局4/56；Day5 4/5，manifest、循序POST→GET與隔離100筆對帳已完成，active4-1資料流與成果界線說明。HTML/CSS/瀏覽器JavaScript由Codex依最新授權全權完成並驗證；操作與資料流說明亦由Codex交付，不再停在前端口試。驗證及界線見[Day4交付](day4_browser_acceptance.md)。下方為已實作的UI契約。

## 1. 使用者可以完成什麼

在同一個頁面查看模擬帳戶、送出一筆 LIMIT BUY、查看這筆訂單的最新狀態。首版只提供 BUY／LIMIT；不提供 SELL、成交、取消或全帳戶歷史列表。

帳戶 ID 預填範例 `SIM-001`，仍必須透過 API 查證存在與當下數值；查不到就顯示錯誤，不用假資料代替。價格與數量為使用者輸入，不預設已下單。

## 2. 頁面草圖

```text
┌─ 模擬交易 ─────────────────────────────────────────────┐
│ 帳戶 ID [SIM-001       ] [載入／重新整理]                │
│ 總現金：—       已預留：—       可用現金：—               │
│ 資料時間：尚未載入          帳戶訊息：—                  │
├─ 建立 LIMIT BUY ───────────────────────────────────────┤
│ 使用帳戶：—           方向：BUY        類型：LIMIT       │
│ 商品代碼 [          ]  數量 [        ]  限價 [         ] │
│ [送出買單]                                             │
│ 下單結果／錯誤訊息：—                                  │
│ （結果不明時）[確認原請求結果]                          │
├─ 本分頁已取得的訂單 ───────────────────────────────────┤
│ 訂單 ID                 最新查詢狀態     已成交數量      │
│ —                       —                —   [查看]    │
│ 此列表不是伺服器提供的完整歷史。                         │
├─ 查詢訂單 ─────────────────────────────────────────────┤
│ 訂單 ID [                                ] [查詢]      │
│ ID：—   狀態：—   已成交數量：—                         │
│ 所屬帳戶：—   總現金：—   已預留：—   可用：—            │
│ 訂單查詢訊息：—                                        │
└────────────────────────────────────────────────────────┘
```

桌面可將表單與訂單區並排，窄螢幕依上圖順序堆疊。首版不做報酬圖表、行情串流或視覺化交易績效。

## 3. 前後端責任

| 元件 | 負責 | 不承擔 |
|---|---|---|
| 瀏覽器 | 收集輸入、顯示載入／成功／錯誤、呼叫 public API、保存本次請求身分 | 決定資金是否足夠、修改預留現金、直接讀寫 DB |
| FastAPI | 檢查請求與資金、處理冪等、執行交易、回傳 authoritative 資料 | 依 UI 自算的餘額相信下單合法 |
| PostgreSQL | 保存帳戶與訂單等資料，以 constraints／transaction 保護資料一致性 | 接受瀏覽器直接連線 |

`available_cash` 直接顯示 API 回傳值。前端可以把金額格式化成兩位小數，但不自行扣款、增加 reserved cash 或推算新的帳戶餘額。前端的必填／格式檢查是輸入便利性，API 仍須負責業務判斷。

## 4. 每個操作對應的 API

| 操作 | 請求 | 成功後使用的資料 |
|---|---|---|
| 載入／重新整理帳戶 | `GET /v1/accounts/{account_id}` | `account_id`, `total_cash`, `reserved_cash`, `available_cash` |
| 送出 BUY | `POST /v1/orders` | `201`、`order_id` 與已保存的請求回應欄位；再查該 order |
| 輸入 ID 查詢／列表查看 | `GET /v1/orders/{order_id}` | `order_id`, `status`, `fill_quantity` 與巢狀 `account` 四欄 |
| 下單成功後刷新帳戶 | `GET /v1/accounts/{account_id}` | 重新顯示 API 回傳的帳戶金額 |

URL 中的 ID 必須編碼；UI 以文字節點顯示 API 內容，不把回應插入成任意 HTML。這裡沒有 `GET /v1/orders` 全列表 API；不得假裝現有後端已提供。

### BUY 輸入的來源

| 項目 | 來源／傳遞 |
|---|---|
| `account_id` | 已載入的選定帳戶；送出時鎖定這次請求的值。 |
| `action` | 本頁固定 `BUY`。 |
| `order_type` | 本頁固定 `LIMIT`。 |
| `symbol` | 使用者輸入；依既有契約使用大寫、非空、最多32字元。 |
| `quantity` | 使用者輸入正整數，以 JSON number 傳送。 |
| `price` | 使用者輸入正數、兩位小數，以 JSON string 傳送，例如 `"10.00"`；不先轉成浮點數再做金額計算。 |
| `Idempotency-Key` | 前端每個新邏輯請求產生一個 UUID，放 HTTP header；不是 JSON 第七個欄位。 |
| `order_id` | 由後端產生，前端只接收與查詢。 |

前端收集的六個 JSON keys 與回應欄位沿用 [資料契約](data_contract_spec.md)，不修改 API contract。現有後端對部分嚴格輸入格式尚未完整 enforcement；這份 UI 設計不宣称已修正那些後端缺口。

## 5. 送出、成功與後續查詢

```text
載入帳戶成功
→ 輸入商品／數量／價格
→ 基本格式檢查
→ 建立新請求 key，保存 key＋payload 快照
→ 停用送出按鈕與這筆請求的輸入，顯示「送出中」
→ POST /v1/orders
→ 收到201：顯示「下單成功」與 order_id
→ 依 order_id 去重，加入本分頁列表
→ GET 該 order，更新訂單明細與列表狀態
→ GET 原選定 account，更新帳戶金額
```

POST 回應目前沒有 `status`／`fill_quantity`；這兩項必須由 order GET 取得，不能從成功201自行補成固定值。後續 GET 失敗時保留「下單成功」與已知 order ID，顯示「資料更新失敗」，提供重新查詢；不能因此把成功訂單說成失敗，或再次以新 key POST。

切換帳戶時，清除或標示舊帳戶資料，不把上一帳戶數字留成新帳戶數字。手動查到不同帳戶的訂單時，其巢狀帳戶只顯示在該訂單明細，不悄悄更換上方目前選定帳戶。每個查詢區只接受最後一次請求的結果，避免慢回應覆蓋後來選定的 ID。

## 6. 拒絕、斷線與重送

| 結果 | 畫面與行為 |
|---|---|
| `409`＋`Insufficient cash` | 顯示「可用現金不足」，保留表單輸入；不加入成功訂單、不自行改金額。重新查詢帳戶；使用者修正表單後可建立新邏輯請求。 |
| POST `404`＋`Account not found` | 顯示帳戶不存在，保留其他輸入，要求重新載入正確帳戶。 |
| `422` | 將可辨識的欄位錯誤顯示在表單／訊息區；保留輸入，不清空整張表單。 |
| `409`＋`Idempotency key already exists` | 顯示請求識別衝突，不假稱現金不足，不自動換 key 重送。 |
| 訂單 GET `404` | 顯示查無該訂單；清除／標示該查詢區舊明細，不影響已知其他訂單。 |
| 網路失敗、timeout、無法解析的POST回應或非預期伺服器錯誤 | 顯示「尚未確認這筆下單結果」，保留原 key＋原 payload。不得直接當作未成交／未下單，也不自動建立第二個新請求。 |

首版只允許一筆尚未確認結果的 POST。前端在送出前用同一分頁的 `sessionStorage` 保存 pending key＋payload，重整後仍可提供「確認原請求結果」：手動使用同 key＋同 payload 重送。這個按鈕名稱不宣稱原請求失敗。pending 狀態時不允許修改該筆輸入後沿用同 key；直到拿到可判定回應，才解鎖新的下單。

`sessionStorage` 只保存此本機模擬交易的請求快照；不保存憑證或宣稱它是訂單真實資料庫。若暫存寫入失敗，先停止送出並顯示可重試的錯誤，避免送出後失去請求身分。關閉分頁會失去此暫存，跨分頁／跨裝置恢復、併發同 key 的完整驗收仍是後續切片。

已知成功後清除 pending，保留輸入但明確顯示成功 order ID；再次按「送出買單」代表另一個新邏輯請求，使用新 key。首版不做自動重送與背景輪詢。

## 7. 同源部署與檔案責任（已實作）

| 檔案 | 責任 |
|---|---|
| `app/static/index.html` | 首版單一HTML，包含最小CSS／JavaScript、表單與 API 呼叫；不含交易 SQL。 |
| `app/main.py` | 新增 `GET /` 提供該頁面，沿用現有 `/v1/accounts` 與 `/v1/orders` routes。 |
| `tests/test_browser_ui.py` | UI入口可取得HTML、必要頁面控制項／API使用邊界的基本測試。 |

HTML/CSS/瀏覽器JavaScript由Codex完成；root route與正式Python入口tests由Andrew實作。頁面與API在同一FastAPI origin，用相對`/v1/...` URL，不以file://開啟，不增加CORS或新前端框架。

## 8. 設計驗收與後續實作驗證

本切片已完成：三個使用區域、輸入／顯示來源、三支public API對照、成功／拒絕／結果不明流程、金額與交易責任邊界、預定實作位置均明確。已核對目前 mounted routes、OpenAPI request六欄與header，以及實際 route 的201/404/409/422行為；OpenAPI未完整列出所有手動拋出的錯誤，錯誤契約以route與既定tests為證。

已執行22項Node前端檢查與70項Python回歸，搭配原routes＋真實隔離test DB的瀏覽器操作／SQL對帳；成功、missing、不足、結果不明、重整重播、GET故障與斷線均通過。列表去重及不同帳戶隔離通過；desktop／390px畫面已驗證。

[驗證證據與4-1資料流說明](day4_browser_acceptance.md)。前端只使用既有契約；狀態合法值為OPEN／PARTIAL_FILLED／FILLED／CANCELLED，不能把execution profile的PARTIAL混作訂單狀態。真實DB驗證採外層transaction rollback，不宣稱跨連線commit／併發已通過。後續回到[Day5 Python manifest](virtual_user_manifest.md)。
