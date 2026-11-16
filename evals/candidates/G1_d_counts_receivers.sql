-- golden: G1_active_customers
-- expect: wrong_result
-- note: Passes every guardrail. Counts people who only received a transfer as active.
WITH involved AS (
    SELECT t.c_012 AS person
    FROM t_03 AS t
    WHERE t.c_011 >= '2025-05-31 21:00:00' AND t.c_011 < '2025-06-30 21:00:00'
      AND t.c_020 = 'success'
    UNION
    SELECT t.c_013
    FROM t_03 AS t
    WHERE t.c_011 >= '2025-05-31 21:00:00' AND t.c_011 < '2025-06-30 21:00:00'
      AND t.c_020 = 'success'
      AND t.c_013 IS NOT NULL
)
SELECT COUNT(*) AS active_customers
FROM involved AS i
JOIN t_01 AS c ON c.c_001 = i.person
WHERE c.c_005 = 0;
