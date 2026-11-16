-- question: How many customers were active in June 2025?
SELECT COUNT(DISTINCT t.customer_id)
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
WHERE c.is_test_account = 0
  AND t.status = 'success'
  AND strftime('%Y-%m', t.txn_ts, '+3 hours') = '2025-06';
