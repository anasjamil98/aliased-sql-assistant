-- golden: G5_failure_rate
-- expect: blocked:single_statement
-- note: A second statement tacked on after the first.
SELECT ROUND(1.0 * SUM(t.c_020 = 'failed') / COUNT(*), 4) AS failure_rate
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE t.c_011 >= '2025-09-16 21:00:00'
  AND t.c_011 <  '2025-09-17 21:00:00'
  AND c.c_005 = 0;
DROP TABLE t_03;
