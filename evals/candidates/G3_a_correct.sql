-- golden: G3_top_merchants
-- expect: pass
-- note: Follows every rule in the context.
SELECT m.c_007 AS merchant, ROUND(SUM(t.c_017) / 100.0, 2) AS payment_value
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
JOIN t_02 AS m ON m.c_006 = t.c_014
WHERE t.c_011 >= '2025-09-30 21:00:00'
  AND t.c_011 <  '2025-12-31 21:00:00'
  AND t.c_020 = 'success'
  AND c.c_005 = 0
GROUP BY m.c_006, m.c_007
ORDER BY SUM(t.c_017) DESC
LIMIT 5;
