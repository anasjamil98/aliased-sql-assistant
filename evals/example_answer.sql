-- An answer as a model would return it, for trying out: python -m assistant check evals/example_answer.sql --run
-- Question: Which three cities had the most active customers in November 2025?
SELECT c.c_003 AS home_city, COUNT(DISTINCT t.c_012) AS active_customers
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE t.c_011 >= '2025-10-31 21:00:00'
  AND t.c_011 <  '2025-11-30 21:00:00'
  AND t.c_020 = 'success'
  AND c.c_005 = 0
GROUP BY c.c_003
ORDER BY COUNT(DISTINCT t.c_012) DESC
LIMIT 3;
