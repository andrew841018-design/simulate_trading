# 工程難題紀錄

只記錄實作時真正卡住、且日後值得重用的問題。所有日期共用這一份檔案，不必每天新增文件。

## 紀錄格式

```text
## YYYY-MM-DD — 問題名稱
- 現象：看到什麼錯誤
- 原因：真正的根因
- 解法：最後採用的做法
- 驗證：如何證明已解決
```

## 2026-08-13 — PostgreSQL constraint 測試的 rollback 迴圈

- 現象：預期中的 SQL constraint 錯誤發生後，同一 transaction 再執行 `SELECT` 會得到 `InFailedSqlTransaction`。
- 原因：PostgreSQL statement 失敗後，transaction 會進入 aborted 狀態；必須 rollback 才能繼續使用。但 rollback 後再查不到資料，只能證明 transaction 被撤銷，不能單獨證明 constraint 正確。
- 解法：
  - 負向測試用 try/except/else做條件式區分，錯誤直接被except抓到，若意外正確則去讀table,並用assert卡死。
  - 正向測試，如果是錯的會被pytest.raise抓到（pytest特性），繼續往前走因此可以被assert卡死，而知道錯在哪個規則；若沒錯，則pytest內部assert卡死。
  - Session fixture 只在整套測試開始前清空一次，每個測試仍自行 rollback／close。
- 驗證：完整測試 `7 passed`，Ruff 通過，測試後 `accounts` 表為 0 筆。
