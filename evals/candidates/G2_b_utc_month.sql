-- golden: G2_tpv_by_type
-- expect: wrong_result
-- note: Passes every guardrail. Uses UTC month boundaries, so three hours at each end of the month land in the wrong month.
SELECT t.c_015 AS payment_type, ROUND(SUM(t.c_017) / 100.0, 2) AS tpv
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE t.c_011 >= '2025-09-01 00:00:00'
  AND t.c_011 <  '2025-10-01 00:00:00'
  AND t.c_020 = 'success'
  AND t.c_015 IN ('p2p_transfer', 'merchant_payment', 'card_payment', 'bill_payment')
  AND c.c_005 = 0
GROUP BY t.c_015;
