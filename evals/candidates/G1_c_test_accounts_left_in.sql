-- golden: G1_active_customers
-- expect: blocked:test_accounts
-- note: Never joins the customer table, so internal test accounts are counted.
SELECT COUNT(DISTINCT t.c_012) AS active_customers
FROM t_03 AS t
WHERE t.c_011 >= '2025-05-31 21:00:00'
  AND t.c_011 <  '2025-06-30 21:00:00'
  AND t.c_020 = 'success';
