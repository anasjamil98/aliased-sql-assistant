-- question: Which five merchants took the most in successful payments in the last quarter of 2025?
-- ordered: true
SELECT m.merchant_name, ROUND(SUM(t.amount_minor) / 100.0, 2)
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
JOIN merchants AS m ON m.merchant_id = t.merchant_id
WHERE c.is_test_account = 0
  AND t.status = 'success'
  AND date(t.txn_ts, '+3 hours') BETWEEN '2025-10-01' AND '2025-12-31'
GROUP BY m.merchant_id, m.merchant_name
ORDER BY SUM(t.amount_minor) DESC
LIMIT 5;
