# Day 5 — manifest, sequential sender and run summary

2026-09-14 2-1行為驗收完成：最新test_manifest_response已以非201計rejected、201計succeeded；精確manifest pytest22 passed（0.04s），另6組離線sender案例全部PASS。涵蓋空清單、3筆201、201／409／timeout、404後201、timeout後201、100筆201；混合3筆正確回attempted3／succeeded1／failed2。URL、payload、header、順序、沒有重試及未改輸入均核對通過。6組是離線探針，不宣稱納入永久pytest或已送真實API。固定長度及狀態分類問題結案，不再重開；該輪2-1完成，當時Day5 2/5、active2-2第3/5項；現行進度见本頁最新驗收。

2026-09-11 1-1行為驗收完成：最新精確pytest為22 passed（0.03s），已包含每筆quantity乘Decimal(price)累加與迴圈後100000.00上限assert。cost以整數0初始化可精確與Decimal相加，第一筆後成為Decimal，不必為形式改寫。100筆、payload、批次隔離、重現性、輸入拒絕與成本由正式22例覆蓋；random雙向獨立性沿用已實跑2項探針證據，未宣稱納入永久pytest。合法seed／ID額外測試依Andrew決定省略。依當前已驗證行為結束1-1，不再將同一random教學或證據形式作重複關卡；驗證方式與永久回歸覆蓋的差異明列為限制。當時Day5為1/5、active2-1；現行進度見本頁最新驗收與子任務地圖。此段記錄9/11完成1-1的歷史成果。

## 固定子任務地圖（4/5；active4-1）

| ID | Outcome | 驗收 |
|---|---|---|
| 1-1 | 已完成：可重現的100筆有效BUY清單與離線測試 | 相同輸入清單相同、100個唯一key、六欄payload合法、合計成本有上限；不發HTTP或連DB |
| 2-1 | 已完成：逐筆public API送單與結果計數 | concurrency=1、每筆等待回應；attempted/succeeded/failed清楚，沒有自動重試 |
| 2-2 | 已完成：依成功order ID查回並產出執行摘要 | GET確認存在、回傳計數與逐筆結果（含total_cost）；不靠直接讀DB決定成功 |
| 3-1 | 已完成：隔離環境100筆整合與SQL對帳 | attempted=100、succeeded=100，orders可查，reservation/transition/outbox/idempotency對帳 |
| 4-1 | 進行中：Python資料流與成果界線說明 | Andrew能解釋決策規則、可重現範圍，以及sequential100筆不是效能測試 |

1-1/2-1/2-2/3-1 completed; active4-1，待Andrew以自己的話說明資料流與成果界線。

## 2-1逐筆送單與計數契約

2026-09-14 2-1行為驗收完成：最新test_manifest_response已以非201計rejected、201計succeeded；精確manifest pytest22 passed（0.04s），另6組離線sender案例全部PASS。涵蓋空清單、3筆201、201／409／timeout、404後201、timeout後201、100筆201；混合3筆正確回attempted3／succeeded1／failed2。URL、payload、header、順序、沒有重試及未改輸入均核對通過。6組是離線探針，不宣稱納入永久pytest或已送真實API。固定長度及狀態分類問題結案，不再重開；該輪2-1完成，當時Day5 2/5、active2-2第3/5項；現行進度见本頁最新驗收。

2026-09-14 2-2教學補正：上一則驗收後銜接只給文字步驟、漏附既定的不同業務完整範例，本輪補上工單POST→ID→GET範例。不得預設所有POST成功：先檢查status_code，僅201分支讀JSON的非空字串ID；非201、RequestError或缺ID不發GET。本段為9/14的歷史教學；其POST-only計數要求已於9/15退休。現行取order_id仍以POST201為前提，succeeded則依Andrew正向流程在整段通過後增加。範例以MockTransport驗證8種情況全通過，包括POST拒絕／timeout／缺ID／非物件JSON、GET成功／404／timeout／ID不符；沒有網路呼叫，未修改專案Python。後續自動銜接新切片也要附文字控制流與不同業務完整範例，不能只列outcome當引導。

2026-09-15 最新決定：Andrew確認只保留results裡每筆total_cost，不另外提供整批總額；撤回manifest_summary物件及其total_cost/count要求。回傳report只含attempted、succeeded、failed、results；每筆result保留total_cost，沿用現有單筆計算與原生Decimal，不因缺少全批加總或JSON序列化擋關。只需return report，不要求save_summary、output_path、JSON檔案或round-trip。先前整批加總與保存指引已退休，不再重播；已有單筆金額成果保留。這是回傳內容與輸出範圍的決定，不自行豁免其他POST→GET行為驗收，不宣稱2-2全部完成。Day5 1-1既有manifest成本上限測試與3-1隔離資金/SQL對帳責任不變。既有artifacts/virtual_user_summary.json占位檔不再使用、不列驗收，未刪除檔案。

前輪2-2分支引導已交付：包裹查回類比6組離線驗證通過；這是範例證據，專案現況依本頁最新檢查，不重播相同教學。

2026-09-15 GET例外捕捉範圍驗證完成：最新107行版本在79行try內解析JSON並於81行讀get_order_id，86行捕捉KeyError/TypeError，94行改比較已取出的變數。此次同一離線探針4/4 PASS：正常回attempted2/succeeded2/failed0；GET200回{}／null／[]皆回2/1/1，保留兩筆results、首筆verified=False且有error、第二筆verified=True，全部送出2筆POST。前輪取值在try外的問題已修正並結案，不再重開同一教學。重跑入口為simulate_trading目錄下.venv/bin/python /tmp/mini_get_response_probe.py；這是暫存離線探針，不是正式tests，無網路或DB操作。前輪manifest22 passed及其他report/GET驗證為原有證據，本輪未重跑。此次只確認當前GET取值修正，不宣稱整個2-2或真實100筆整合已完成；POST ID既有討論不重播、不因此自動豁免其他契約。Python及正式tests由Andrew修改，Codex未代寫。

2026-09-15 2-2及3-1驗收完成：最新115行版本74行保留str與非空判斷，原有空字串誤發GET與文字ID額外排除均結案；同一離線report探針21/21 PASS。接續既有FastAPI public routes與真實本機_test PostgreSQL，用seed42生成100筆，attempted100/succeeded100/failed0、100筆GET確認，orders/transition/outbox/idempotency各100筆且逐筆payload、ID、狀態與版本一致；保留資金增量48910.00、可用51090.00，與manifest及SQL成本一致。隔離帳戶起始total100000.00/reserved0；本輪帳戶與相關資料已rollback、殘留全0。測試使用TestClient與共用外層transaction/savepoints，不宣稱真實網路、跨連線commit durability、效能或fill/cancel驗證。證據為simulate_trading/docs/references/day5_api_sql_evidence_20260915.json；重跑入口在simulate_trading目錄下.venv/bin/python /tmp/mini_report_contract_probe.py及.venv/bin/python /tmp/mini_day5_integration_probe.py。探針屬驗證工具，不是正式pytest；原manifest22 passed為前輪證據，本轮未重跑。Python及正式tests由Andrew實作，Codex未修改。Day5 4/5，active4-1第5/5項；本次及今日完成+2（2-2、3-1），待Andrew完成資料流與成果界線說明。

2-2當前契約：在scripts/virtual_user.py擴充既有manifest_response(client, manifest)回傳完整report，只以return report回傳Python dict，不要求save_summary、輸出路徑或JSON檔案。依2026-09-15 Andrew採用的正向流程，頂層attempted統計實際嘗試筆數，succeeded統計POST與GET確認整段成功，failed統計其餘已處理失敗；每筆恰計一次且attempted=succeeded+failed。依2026-09-15 Andrew最新決定，report頂層只含attempted、succeeded、failed、results；筆數沿用attempted，不新增manifest_summary或整批總額。每個輸入依原順序保留一筆result，恰含idempotency_key、post_status（HTTP整數或未收到回應時null）、order_id（POST201回傳的非空字串，否則null）、get_status（HTTP整數或未取得時null）、verified（布林）、error（null或錯誤代碼）、total_cost（單筆金額，可保留原生Decimal）。單筆金額沿用既有計算位置；目前成功流程填quantity乘Decimal(price)，未計算時保留0占位，不代表已成交金額。仅POST201且取得有效order_id時，以同一同步client呼叫GET /v1/orders/{order_id}；200且JSON的order_id相符才verified=true。不能拿idempotency_key代替order_id；不讀DB、不重送POST或重試GET。HTTP失敗、RequestError、JSON無法解析或缺ID皆記錄結果並繼續；error記錄原因，成功為null；依Andrew明確忽略命名差異，接受目前post_json_error等標籤，不再以固定字串清單擋關。JSON解析失敗已有continue時可保留目前判斷順序。POST與GET完整通過才計succeeded，任一已處理失敗計failed；GET失敗可使整段failed，但不能據此認定訂單未建立。依2026-09-15最新決定，不要求存檔或JSON序列化；以離線client直接驗證回傳report的內容、mixed POST只查成功ID、GET成功／404／timeout／ID不符仍續行。不要求重驗GET回應的所有業務欄位或DB對帳；3-1才做真實隔離環境100筆。程式與正式tests由Andrew寫，Codex安全驗證。

2-1已完成階段契約（僅供歷史；現行2-2計數依本頁新契約）：在既有scripts/virtual_user.py新增send_manifest(client, manifest)，client為呼叫端提供且已設定base_url與有限timeout的同步httpx.Client；函式不建立或關閉外部client。逐筆POST /v1/orders，JSON只送row.payload，Idempotency-Key header使用row.idempotency_key；每筆送出均計入attempted，可由succeeded+failed等價計算。201（含既有成功重播）算succeeded，其他HTTP status或httpx.RequestError算failed，並繼續下一筆；不自動重試、不改manifest、不直接連DB。failed代表未確認成功，timeout不證明伺服器沒有建立訂單。回傳恰含attempted、succeeded、failed的計數dict，總有attempted=succeeded+failed；空清單三項皆0。先以離線client替身驗證201／409／timeout混合結果及送出順序、URL、payload與header；不發真實HTTP。成功order ID查回／回傳摘要留2-2，隔離環境100筆與對帳留3-1。正式Python及tests由Andrew實作，檔案已存在，Codex負責安全驗證。此為client端工作切片，不改後端API契約。

## 1-1輸入與輸出契約（2026-09-10最新確認）

build_manifest(account_id, batch_id, seed)：三參數必填；account_id與batch_id均為1–64字元字串，保留原值，不額外限制首尾空白、ASCII或字元種類；seed為0至2**32-1整數，拒絕bool。

- 檔案scripts/virtual_user.py；正式tests為tests/test_virtual_user.py。Python實作與tests由Andrew完成，檔案均已存在。
- account_id與batch_id不做trim或其他正規化；空字串、超過64字元或非字串為非法，空白／Unicode／底線本身不是非法條件。
- 相同seed決定同一組數量，使用函式內Random而非全域亂數狀態。
- 回傳100筆list，每筆精確兩欄：idempotency_key與payload。key沿用batch_id和序號，非空、批內唯一、不同batch_id不碰撞、相同輸入可重現；目前格式至多67字元，可以含非ASCII。撤回舊key必須ASCII的manifest要求，避免與新batch_id契約衝突。
- payload精確六欄：account_id（原輸入）、action="BUY"、order_type="LIMIT"、symbol="DEMO"、quantity（1–100整數）、price="10.00"（字串）。不含order_id、status或batch_id。order_id由既有API產生。
- Decimal加總委託金額最多100000.00（100筆 × 每筆最多100 × 單價10.00）；無效輸入ValueError；純函式不讀.env／DB／HTTP、不寫檔。
- 此為本地manifest契約。函式接受字串不保證帳戶存在或HTTP header可傳送；後續2-1示範使用有效既存帳戶及ASCII batch_id，不改後端API／DB契約。

## 1-1驗證與目前證據

2026-09-11 1-1行為驗收完成：最新精確pytest為22 passed（0.03s），已包含每筆quantity乘Decimal(price)累加與迴圈後100000.00上限assert。cost以整數0初始化可精確與Decimal相加，第一筆後成為Decimal，不必為形式改寫。100筆、payload、批次隔離、重現性、輸入拒絕與成本由正式22例覆蓋；random雙向獨立性沿用已實跑2項探針證據，未宣稱納入永久pytest。合法seed／ID額外測試依Andrew決定省略。依當前已驗證行為結束1-1，不再將同一random教學或證據形式作重複關卡；驗證方式與永久回歸覆蓋的差異明列為限制。當時Day5為1/5、active2-1；現行進度見本頁最新驗收與子任務地圖。此段記錄9/11完成1-1的歷史成果。

### 以下為1-1完成前的歷史驗證與指引

2026-09-11當前切片仍為Day5 1-1，接續Decimal總成本驗收：在既有tests/test_virtual_user.py的test_build_manifest保留所有assert，於for之前建立Decimal零總額、每筆累加quantity乘Decimal(price)，於for結束後檢查總額不超過Decimal的100000.00；不新增函式或正常seed／ID案例。使用工時乘費率的不同業務範例引導。當輪只讀核算seed42之100筆總额為48910.00，符合上限；教學類比亦執行通過。這不是正式新增成本assert已完成，存檔後由Codex跑tests/test_virtual_user.py，沿用原test時預期仍22 passed。random已有兩項行為探針證據及教學結論，依Andrew糾正不再重講；正式random test尚未新增的事實保留，不自行宣稱豁免。仍在同一1-1內推進可獨立完成的成本部分，未進2-1。全局4/56、Day5 0/5、1-1第1/5項，本次關卡+0，未改Python。

2026-09-11 Andrew糾正：global random獨立性已討論，停止重複getstate／setstate／first與second插入位置等同一段教學。前輪已給完整抽色類比及局部映射，且實際記憶體探針已確認兩項獨立性行為PASS；這些成果必須沿用，不因正式test存檔未變而再次把同一教學當成新工作。正式test是否落地另作事實記錄，不能混同為概念尚未講過；本句糾正不自行推定取消random驗收或完成整個1-1。後續若有新的具體疑問才針對差異回答。

前輪random教學已交付：已說明局部Random與全域random互不影響、狀態快照及恢復，並給過不同業務類比；依最新糾正不再重播。合法seed／ID額外測試豁免維持。

2026-09-11三參數修正版：精確pytest為22 passed（0.04s）；直接逐列核對錯誤來源為seed7例、account_id7例、batch_id6例，全部符合各組目的。batch案例已使用合法整數seed，兩種ID的65字元拒絕均通過；先前遮蔽問題已解決，不重開。非法輸入這一段完成；in集合寫法保留，不強制拆test或改訊息欄位。2026-09-11 Andrew最新驗收決定：不再新增合法account_id／batch_id測試，撤回1字元、64字元及空白／Unicode／底線原值保留的額外測試要求；不得要求參數化改寫既有正常清單test。保留現有22例（seed7、account7、batch6拒絕案例與原正常清單／重現性2例），seed與ID輸入驗收依目前範圍完成。兩種ID的合法範圍與保留原值契約不變；這是省略額外測試的決定，不能將非法輸入被拒絕記成已證明所有合法輸入成功。先前正常seed端點豁免維持；剩餘global random獨立性與Decimal成本驗收，不取消既有輸出／重現性測試。全局4/56、Day5 0/5、1-1第1/5項；本次完成ID驗收範圍確認，關卡+0。合法ID額外測試已撤回；global random獨立性及Decimal成本仍待完成；全局4/56、Day5 0/5、1-1第1/5項，本次關卡+0，新增6個batch與1個account長度拒絕有效證據。Codex未改Python。

### 前次20例證據（歷史，batch遮蔽已修正）

2026-09-11三參數合併版：精確pytest為20 passed（18個參數化案例＋原正常清單及重現性2例）。單一test_manifest與in三種訊息語法正確。新增account六個拒絕案例已測到account檢查；batch五列的seed卻是字串「7」，逐列追查全部先拋seed ValueError，因此尚未驗證batch拒絕。當時指出的第43–47行字串seed及兩種ID的65字元缺口，現已修正並取得本頁最新22 passed證據。in只保證訊息屬允許集合，不保證案例對應；可按案例提供expected_message以精確辨識，函式合併本身不是問題。正常seed端點豁免維持，合法ID額外測試後續已撤回；random／成本仍待既定驗收。Python未修改，Day5仍0/5。

### 前次9例證據與引導（歷史）

2026-09-11接續核對：精確pytest重新取得9 passed（0.02s），seed驗收維持完成。當前1-1先補兩種ID的輸入契約測試：分別改account_id或batch_id，另一ID與seed保持合法；當時要求的空字串、65字元及非字串拒絕已驗證；1／64字元與空白／Unicode／底線合法值額外測試要求後續已撤回。這是既定ID驗收，不新增seed正常端點要求。正式Python由Andrew修改；完成後由Codex跑同一test檔。global random獨立性與Decimal成本仍待後續驗收。測試組織澄清：不要求seed、account_id、batch_id各自新增test函式；可擴充既有test_invalid_manifest，以同一parametrize函式承接三種輸入的獨立案例。每列只讓一個參數非法，其餘合法；若檢查錯誤訊息，預期訊息需隨案例變化。全部manifest行為也可放同一函式，但需正確區分成功與預期例外，單一未參數化test的首個失敗會中止後續檢查。函式数量不是驗收門檻，原seed案例覆蓋與既定契約保留。

2026-09-11 seed第五版：第32行訊息assert已與with同層，精確pytest為9 passed。改拋不同訊息ValueError的記憶體替代案例現在被AssertionError拒絕；非法seed七例與訊息驗證完成，不再重開先前縮排缺口。正式Python未改。

2026-09-11 Andrew糾正／現行驗收：正常seed不再新增兩端點檢查，也不要求把test_build_manifest改為0與2**32-1參數化。保留既有正常清單、重現性與七個非法seed測試，現有9 passed作為本段seed驗收證據；撤回先前預期10 passed及要求移除正常test隨機seed的指引。seed合法範圍0至2**32-1與內部驗證不變。此為驗收範圍決定，不表示正向測試在一般情境沒有用途。

此糾正須先同步再推進，後續不得援引舊邊界測試理由重開此要求。當時剩餘包含ID驗收；其後非法ID已通過且額外合法ID測試由Andrew撤回，目前僅剩global random獨立性與成本验收，1-1未全部完成。

### seed第四版（訊息assert已移出with，歷史）

2026-09-11 seed第四版：test_invalid_manifest的pytest.raises(ValueError)已正確包住呼叫，精確pytest為9 passed（原2例＋非法seed7例）。原先未宣告預期例外的问题已解決。Andrew自行新增的錯誤訊息assert在第32行，仍縮排於with內、位於第31行拋例外的呼叫之後，因此正常拒絕時永遠跳過。記憶體替代函式改拋不同訊息的ValueError，test(-1)仍PASS，證明訊息尚未驗證。

當前僅需將第32行訊息assert退一層、與with同層，讓raises context退出並捕捉例外後再讀error.value。保留已確認的拒絕與其他tests，不修改production。訊息為Andrew test主張，本輪只修其執行位置，不新增API錯誤字串契約。修正後預期仍9 passed，但錯誤訊息替代案例應FAIL；當時提出的正常seed兩端點驗收已依本頁最新決定撤回。Codex未改Python。

### seed第三版（已補raises，歷史）

2026-09-11 seed第三版：已新增test_invalid_manifest(seed)，正確套用七個非法seed，原重現性test恢復獨立。精確pytest為7 failed、2 passed；七例均在virtual_user.py第6行拋ValueError，證明內部拒絕行為有執行。test第30行直接呼叫且沒有pytest.raises，導致預期例外逸出而被pytest記失敗。這不是production應移除raise，也不是新的collection錯誤。

當前局部修正只在tests/test_virtual_user.py第30行：用pytest.raises(ValueError) context包住既有函式呼叫，保持傳入seed與合法ID。不要再加seed驗證if、吞掉任意例外或修改生成函式。修正後這份檔案預期9 passed；正常seed兩端點要求後續已撤回，Day5 1-1尚未完成。正式Python未改。

### seed第二版（已新增正確的獨立test，歷史）

2026-09-11 seed第二版：production中的pytest已移除，test檔import pytest與parametrize拼字已正確。decorator現在掛在test_repeatable_calling_manifest上，但它無seed參數；精確pytest回報function uses no argument seed，1 error during collection。原test第30行還會自行產生合法seed，因此不能只補函式參數後就宣称測到非法值。原重現性test的目的為成功生成後比較清單，應保留；它不是非法seed拒絕test。

同一責任修正：在tests/test_virtual_user.py末尾新增第三個test_函式接收seed；把現有decorator移到該新test上，直接在pytest.raises(ValueError)內呼叫build_manifest、傳入seed與兩個固定合法ID，不重新指定seed。原前兩個test恢復原有職責，不重寫production驗證。這仍是同一seed切片，七個非法值未改；正常seed兩端點要求後續已撤回。Codex未改Python。

### seed第一版（已修正位置與拼字，歷史）

2026-09-11 seed首次草稿：scripts/virtual_user.py第2行新增import pytest，第4–7行把@pytest.mark.parameterize放在build_manifest上。精確pytest在import時回報Unknown parameterize mark，1 error during collection，並非2 passed或seed案例通過。七個非法seed值已選對；正式test檔仍只有原兩個test。此次錯誤類型：流程／檔案責任與工具拼字。

同一seed切片修正：由Andrew將pytest import與參數化decorator移至tests/test_virtual_user.py，在新的test_函式上使用正確parametrize；該test接收seed並在pytest.raises(ValueError)內呼叫build_manifest，另外兩個ID固定合法。生成函式只保留原本業務與輸入驗證，不含pytest裝飾器；不是把驗證if搬去測試。正常seed兩端點要求後續已撤回。Codex未修改Python。

### 前次通過證據（本輪收集錯誤前）

2026-09-11最新修正版：第38行已使用third[i]的key檢查不在第一批完整清單。精確pytest為2 passed；第三批key循環位移成第一批的100個key時，測試現會AssertionError，跨位置重複缺口已解決。相同輸入逐筆key/payload相等、換批payload相等與整批key無交集已有證據。正式Python仍由Andrew修改，Codex只做安全驗證。

教學澄清（2026-09-11）：seed型別／範圍檢查已存在於build_manifest第4–5行，並非缺少實作。不得要求呼叫端或test重寫相同if驗證；此處原指以合法／非法輸入呼叫既有函式，觀察結果或ValueError的行為測試。當時僅釐清validation與test區別；後續Andrew已糾正正常seed不再加驗收項目，現以本頁最新決定為準。後續引導須先說明測的是既有拒絕行為。

該輪seed測試指引（正常兩端點要求後續已撤回）：無效-1、2**32、True、False、1.5、"42"、None皆應ValueError。兩種ID先用固定合法字串，只測seed責任。以pytest.mark.parametrize與pytest.raises寫在既有tests/test_virtual_user.py；以不同業務類比引導，不代寫當前project test。其後ID拒絕驗收已完成，合法ID額外測試已撤回；仍需全域random獨立性與成本驗收；1-1尚未完整完成。

### 前次9/11驗證（歷史）

2026-09-11：未找到本輪開始前的同切片當日紀錄，依9/10確認決策及當前存檔核對。精確pytest為2 passed；collect-only為72例，未執行DB suite。test_repeatable_calling_manifest第26–30行能比對相同參數產生的每筆key與payload；第32–35行只改batch且驗payload相同，方向正確。第34行同索引key不等不能證明整批不重疊：把第三批key設為第一批循環位移、payload保留，100個key全重疊，現有test仍PASS。此為記憶體替代驗證，正式Python檔未改。

前輪指引（現已完成，不重開）：以整批key做無交集檢查，或對第三批每個key檢查不在第一批完整key清單；不強制使用set。固定batch/seed仍是重現測試失敗的建議，不把目前兩次共用相同變數誤認為不同seed。

### 9/10歷史驗證（已由上述9/11結果更新）

2026-09-10最新確認：Andrew要求採用現有quantity1–100並只修改契約，撤回1–3／3000.00舊限制。固定seed42成本48910.00，在新上限100000.00內；最新精確test為1 passed。Andrew已補list/100筆、兩層欄位數及quantity精確int；六個必需payload key逐一存取加長度6、外層兩key存取加長度2，已能抓缺欄／多欄，不要求為形式改成set比較。記憶體替代回傳空list、1筆、多欄與duplicate均被現有test抓到。其餘完整1-1重現性、成本與輸入邊界正式tests尚待完成，仍為0/5。

9/10 test已改用assert檢查key未出現及非空，再append；精確pytest為1 passed。前版if加raise也能抓重複，現行已改正，不再要求重修。

正式tests依最新验收保留兩種ID的空字串、65字元及非字串拒絕；不新增1／64字元或特殊字元合法ID測試。合法範圍與原值保留仍是函式契約，不另作新增測試門檻。seed的0／2**32-1仍屬合法值，但不另列正式測試門檻；保留-1／2**32／bool／非整數ValueError案例。不要再寫舊run_id keyword、預設seed、32字元或ASCII拒絕的assertions。

已完成的1-1可重現與批次隔離測試：固定三個輸入重複呼叫，完整list應相等；只改batch_id，payload清單仍相等、兩批key無交集。key非空已補，字串型別assert可同檔補上，不另拆關卡。其後仍需全域random獨立性、Decimal成本及輸入邊界正式證據。

1-1已由精確pytest22 passed與random兩項獨立探針完成行為驗收，已進2-1。後續仍由Codex從project directory執行`.venv/bin/python -m pytest tests/test_virtual_user.py -q`。

## 決定與學習紀錄

- 2026-09-10最新明確採用：整個目前第4–10行版本，batch_id、seed必填，兩種ID皆1–64字元、不額外限制空白或字元；取代舊run_id、seed=42預設、run長度32、ASCII與account首尾空白限制。前輪「既有輸入契約差異待修」已撤回。
- 原先101筆、缺account_id、多order_id／payload.batch_id、不可重現等問題已由Andrew修正，保留其完成證據，不重開。
- 已學概念：manifest只生成命令；server-owned order_id由orders API生成、保存並回傳。使用者端seed使輸入可重現。
- 規則糾正已同步AGENTS、mini_project規則、dashboard、project flow、plan與本契約；所有衝突舊question-memory退休。已採用的變更必須在HTML與驗收中同步，不再口頭接受卻用舊規格阻擋。

## 首次內容test檢查與後續採用決定（2026-09-10）

首次test漏抓空清單／少筆／多欄，quantity1–100當時尚未核准；後續Andrew已補這些assertions並明確要求「更改契約，程式不變」。原數量待決狀態結案，已解決測試缺口不重提。現行結果以§1-1驗證為準。程式与正式tests由Andrew修改，Codex本次只同步文件及執行驗證。

後續HTTP100筆成功驗收仍需隔離帳戶起始available_cash足以支付該批manifest實際總額；若要涵蓋任意合法數量組合，上限為100000.00。不得假設原70000可用資金保證所有合法批次成功；本次未改seed、DB或API。
