-- question: In December 2025, how many different customers sent a transfer to another person, and what was the average amount?
SELECT COUNT(DISTINCT t.customer_id), ROUND(AVG(t.amount_minor) / 100.0, 2)
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
WHERE c.is_test_account = 0
  AND t.status = 'success'
  AND t.txn_type = 'p2p_transfer'
  AND strftime('%Y-%m', t.txn_ts, '+3 hours') = '2025-12';
