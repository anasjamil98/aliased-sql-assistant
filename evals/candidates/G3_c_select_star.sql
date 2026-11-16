-- golden: G3_top_merchants
-- expect: blocked:no_select_star
-- note: Pulls every column of every joined row.
SELECT *
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
JOIN t_02 AS m ON m.c_006 = t.c_014
WHERE t.c_011 >= '2025-09-30 21:00:00'
  AND t.c_011 <  '2025-12-31 21:00:00'
  AND t.c_020 = 'success'
  AND c.c_005 = 0;
