# 程式／文件一致性盤點

2026-09-10：依Andrew「不只這次，以前以後也要同步，可掃現有code」的要求，回溯simulate_trading現存實作與已確認決策。此文件記錄已確認的現況及同步界線，不是全專案正式code review，也不改學習完成數。

## 範圍與來源

- 掃描app、scripts、tests、migrations共26個實作／驗證artifact，其中22個Python檔可解析；包含HTML前端及Node檢查。
- 對照dashboard、plan、project_flow、data_contract_spec、manifest、wireframe、Day4驗證文件、工程筆記及相關question-memory。references目錄的舊示意頁是歷史參考，不是現行契約。
- [來源指紋與結構清單](references/code_document_snapshot_20260910.json)保存檔案SHA256、migration revisions、表欄位及本次test collection計數；不保存.env、DSN或資料庫內容。
- 決策優先於舊文件；source證明實作現況，但不自動把未核准差異變成契約。前端委託、安全建檔／驗證分工、Day3放行、Day5輸入變更均沿用已明確確認的決定。

## 已修正的矛盾

| ID | 過期或相反敘述 | 已核對的現況與處理 |
|---|---|---|
| DOC-01 | idempotency header未使用、沒有replay | orders.py已查JSONB payload、保存201、重播與409衝突；更新flow、變數字典與差距矩陣 |
| DOC-02 | dependency沒commit，因此整個下單沒有transaction／預留 | create_order內有transaction、FOR UPDATE與reserved_cash UPDATE；dependency只close並不否定route context。區分一般交易與fixture savepoint |
| DOC-03 | transition／outbox全部尚未寫入 | 初始ORDER_CREATED與共同七欄payload已在BUY交易內寫入；只有relay、後續event lifecycle等仍待完成 |
| DOC-04 | 訂單GET只有三欄、巢狀account待實作 | 現行GET JOIN accounts，回訂單三欄及account四欄；已有初始驗收，撤回舊pending |
| DOC-05 | SELECT *、row只判存在、INSERT順序與result變數 | 更新為鎖定兩欄cash、account tuple、真實INSERT tuple順序、order_request_payload／response_body／saved_response血緣 |
| DOC-06 | UI與VU都沒有檔案，route清單缺首頁／GET | 補齊首頁、四支API、已交付UI及本地manifest；HTTP VU sender仍待實作 |
| DOC-07 | 30 tests／單一order API test／2 migrations，與已完成驗收相反 | 本次collect-only70 cases，order API13；4 revisions。既有9/10的70 Python＋22 Node PASS標明為引用證據 |
| DOC-08 | 8/25 runtime/test revision與row counts被當現在 | 移除現況卡的過期值；runtime DB本輪未重查，test DB引用9/10已保存證據，不假造新DB PASS |
| DOC-09 | migration連結指向不存在的無日期檔名 | 改為現有含日期檔名，檢查本地連結與HTML anchors |
| DOC-10 | spec目錄／舊驗證句仍像在保存錯誤response；DC-019未結案 | 明確只保存成功201，404／不足409不保存；flow同步後將DC-019記為已解決。已實作初始JSON與未來驗證分開 |
| DOC-11 | plan要求所有實作Andrew先寫、Andrew自己跑驗證；Day11/12 UI同樣指派Andrew | 對齊後端由Andrew、前端由Codex、必要建檔與安全驗證由Codex；保留閉卷後端學習與已授權例外 |
| DOC-12 | 舊學習log的active／pending与現況混用，筆記有已過期order_id與測試敘述 | 歷史段落明確分界，已解決的ownership／collection／constraint狀態就地更正；保留首次錯誤脈絡。四筆過期現況replay退休 |
| DOC-13 | Day5新輸入契約未進入全域data spec入口 | 補本地manifest與API輸入的界線；batch_id、必填seed、ID1–64且原樣保留仍依Andrew新決定，不套回旧run_id／ASCII限制 |
| DOC-14 | README將專案描述成交易策略測試 | 改為訂單與交易一致性sandbox，連到現行進度、資料流、契約與此盤點 |

## 尚未完成但不是文件矛盾

- SELL仍走BUY現金路徑，核准的position reservation尚未實作；不能因request接受SELL就宣稱業務語意正確。
- pending idempotency row與並行首次key仲裁尚未完整處理。
- 嚴格request型別、任意輸入價格精度與其他API邊界仍有既定差距；Day5本地ID新契約不自動更改API。
- fill/cancel、後續版本／事件一致性、Kafka relay／projection、跨連線durability與完整故障窗口依原課表驗收。
- Day5正式test_virtual_user.py已有首例1 passed，但內容驗收待補；quantity1–100已由Andrew確認採用，成本上限100000.00；原空清單／少筆／多欄缺口已補正。HTTP100筆整合尚未完成。

以上仍在data_contract_spec與課表保留，沒有改程式去繞過它們，也沒有把文件更新算成學習過關。

## 本次驗證與未來重用

本輪執行AST解析、70-case collect-only、source結構與文件對照、HTML／連結／腳本檢查。沒有執行DB寫入suite或重查runtime資料；所有26個實作／test／migration artifact的SHA256與掃描前相同。

之後涉及此專案的實質變更，先核對來源清單及新增檔案，再重用既有`ops/question_memory.py fingerprint`與精確pytest collection入口，只對變更影響的文件／已確認決策做語意核對。指紋或字串檢查只能指出需要重查的範圍，不能替代契約判斷。

採用新決定後同回合同步HTML、plan、active spec、測試引導和question-memory；歷史矛盾也需回溯修正。規則已寫入AGENTS.md與agent_rules/mini_project.md。未新增排程或外部通知。

目前仍為全局4/56、Day5 0/5、1-1；本次學習關卡+0。

## 中斷後續驗證（2026-09-10）

本任務接續原任務末次文件同步：重新比對26個來源SHA256皆未變、22個Python AST解析通過；pytest collect-only重新收集70例。dashboard與project_flow的本地連結、HTML anchors及ID唯一性通過。補正data spec §8.2已結案狀態與§8.3跨日期補記，避免9/9的69例與9/10的70例證據混用。修復中斷留下的題庫INDEX過期並重新驗證；未執行DB suite。正式Python tests仍由Andrew完成，Day5 1-1不因文件同步而過關。

後續程式版本更新：manifest與正式test已由Andrew修改，上述26個SHA256未變是掃描當時的歷史證據。最新精確test為1 passed、collection為71例；內容測試缺口及數量契約差異見virtual_user_manifest.md最新段落。

2026-09-10後續採用：Andrew要求改契約、程式不變，數量差異結案。已同步manifest、plan、dashboard、flow及data spec；最新test 1 passed，原缺口已驗證被抓到。舊數量待決敘述與首版test缺口只代表歷史，不再作現行finding。
