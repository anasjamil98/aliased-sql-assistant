-- golden: G1_active_customers
-- expect: pass
-- note: Follows every rule in the context.
SELECT COUNT(DISTINCT t.c_012) AS active_customers
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE t.c_011 >= '2025-05-31 21:00:00'
  AND t.c_011 <  '2025-06-30 21:00:00'
  AND t.c_020 = 'success'
  AND c.c_005 = 0;
