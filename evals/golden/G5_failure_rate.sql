-- question: What was the failure rate on 17 September 2025?
SELECT ROUND(1.0 * SUM(t.status = 'failed') / COUNT(*), 4)
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
WHERE c.is_test_account = 0
  AND date(t.txn_ts, '+3 hours') = '2025-09-17';
