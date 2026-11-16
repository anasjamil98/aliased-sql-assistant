-- golden: G6_p2p_senders
-- expect: pass
-- note: Follows every rule in the context.
SELECT COUNT(DISTINCT t.c_012) AS senders, ROUND(AVG(t.c_017) / 100.0, 2) AS average_amount
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE t.c_011 >= '2025-11-30 21:00:00'
  AND t.c_011 <  '2025-12-31 21:00:00'
  AND t.c_020 = 'success'
  AND t.c_015 = 'p2p_transfer'
  AND c.c_005 = 0;
