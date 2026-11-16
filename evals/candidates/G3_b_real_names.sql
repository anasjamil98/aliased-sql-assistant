-- golden: G3_top_merchants
-- expect: blocked:no_real_names
-- note: Correct logic, but written with real table and column names the model should never have seen.
SELECT m.merchant_name AS merchant, ROUND(SUM(t.amount_minor) / 100.0, 2) AS payment_value
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
JOIN merchants AS m ON m.merchant_id = t.merchant_id
WHERE t.txn_ts >= '2025-09-30 21:00:00'
  AND t.txn_ts <  '2025-12-31 21:00:00'
  AND t.status = 'success'
  AND c.is_test_account = 0
GROUP BY m.merchant_id, m.merchant_name
ORDER BY SUM(t.amount_minor) DESC
LIMIT 5;
