-- Day 2: seed one deterministic simulated account.
-- Andrew writes the first INSERT attempt before execution.
INSERT INTO accounts (account_id, total_cash, reserved_cash)
VALUES ('SIM-001', 100000.00, 30000.00)
ON CONFLICT (account_id) DO UPDATE SET
    total_cash = EXCLUDED.total_cash,
    reserved_cash = EXCLUDED.reserved_cash
;