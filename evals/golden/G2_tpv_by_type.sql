-- question: What was TPV by transaction type in September 2025?
SELECT t.txn_type, ROUND(SUM(t.amount_minor) / 100.0, 2)
FROM transactions AS t
JOIN customers AS c ON c.customer_id = t.customer_id
WHERE c.is_test_account = 0
  AND t.status = 'success'
  AND t.txn_type IN ('p2p_transfer', 'merchant_payment', 'card_payment', 'bill_payment')
  AND strftime('%Y-%m', t.txn_ts, '+3 hours') = '2025-09'
GROUP BY t.txn_type;
