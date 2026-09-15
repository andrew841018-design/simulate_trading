# Day 4 — browser delivery and verification

2026-09-10：10/10子任務完成。前端由Codex依授權完成；4-1為委託操作／資料流說明交付，不是Andrew閉卷驗收。Python、SQL與正式Python tests未由Codex修改。

## 操作與資料流（4-1交付）

1. 填入已存在的帳戶ID並載入。UI呼叫`GET /v1/accounts/{account_id}`；FastAPI讀PostgreSQL，回傳總現金、預留現金與可用現金。畫面只格式化回應，沒有自行扣款。
2. 填入大寫商品代碼、正整數數量及兩位小數限價。新下單先保存本次key與六欄payload，再以`POST /v1/orders`送出；key在header。API檢查資金、處理冪等，並在交易中更新accounts、orders、transitions、outbox與idempotency結果。
3. 收到201代表已收到成功建立結果；UI再GET訂單與帳戶，顯示後端當下資料。重新整理成功結果只發GET，不建立第二張訂單。
4. 手動輸入訂單ID或按列表「查看」，只GET該訂單。訂單的巢狀帳戶與上方下單帳戶分開；本分頁列表不是完整歷史，重整後不保證保留列表。
5. 不足現金或可判定拒絕保留表單。若回應遺失／timeout，UI無法因此知道後端有無完成；保留原key＋payload並鎖住新請求。重整後按「確認原請求結果」，仍使用相同請求身分。不要把同一意圖改成新key重送。

## 驗證證據

- `node --test scripts/check_browser_buy.cjs`：22項PASS。涵蓋payload/header、重複點擊、金額輸入、權威GET、查詢與列表去重、帳戶隔離、慢回應、404/409/422/500、無效JSON、timeout、pending reload、暫存讀寫／清除失敗及恢复。
- `.venv/bin/python -m pytest -q --tb=line`：70 passed in1.21s。第一次sandbox阻擋PostgreSQL socket；同runner獲准後通過。
- 實際瀏覽器使用原FastAPI routes與隔離`_test` PostgreSQL：5次POST中3筆新單、1次原key重播、1次不足現金409。SQL最終orders／transitions／outbox／idempotency各3筆；帳戶A reserved32100.00、available67900.00，帳戶B未受影響。
- 先買10×100.00，再模擬第二筆成功回應遺失；重整確認後僅兩筆訂單。第三筆1×100.00成功後故障注入GET503，畫面仍保留下單成功；恢復後重新整理僅GET。
- 瀏覽器missing order清除舊明細、列表查看不更換BUY帳戶、missing account停用新單；停止server後查詢顯示斷線。桌面及390px全頁截圖已在任務中核對，窄螢幕documentWidth375≤viewport390。
- [本輪合成資料的request與SQL摘要](references/day4_browser_sql_evidence_20260910.json)。狀態碼記原route回應，fixture另丟棄一次成功POST回應／故障注入GET；不可誤讀為網路實際交付的狀態碼。
- 結束時rollback所有本輪資料，`cleanup_accounts_remaining=0`。驗證服務已關閉。沒有Git staging、commit或push。

## 驗證界線

瀏覽器使用原routes與真實測試DB，但fixture共用外層交易，route成功退出的是savepoint。證據涵蓋本輪UI/API/SQL一致、重送無重複效果與錯誤呈現，不宣稱跨連線durability、真實commit後斷線、併發冪等或完整fill/cancel已通過。那些仍按原課表驗收。瀏覽器暫存限本分頁；關閉分頁後恢復、跨裝置同步及完整歷史API不是本輪功能。

## Day4交付當時的後端入口（2026-09-10歷史）

Day5 `1-1`：Andrew實作[可重現manifest](virtual_user_manifest.md)，Codex執行安全驗證。HTML/CSS/瀏覽器JavaScript後續仍由Codex接手。Dashboard實際瀏覽器確認顯示4/56、Day5、0/5及完整固定子任務地圖；HTML scripts語法與唯一ID檢查通過。

目前進度（2026-09-15）：Day5 4/5，active4-1資料流與成果界線說明。manifest、循序POST→GET及隔離100筆API/SQL對帳已驗收，詳見[Day5契約與最新證據](virtual_user_manifest.md)。
