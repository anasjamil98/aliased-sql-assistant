-- golden: G4_signups_by_month
-- expect: blocked:known_identifiers
-- note: Uses a column alias that does not exist.
SELECT substr(c.c_045, 1, 7) AS signup_month, COUNT(*) AS new_customers
FROM t_01 AS c
WHERE c.c_045 >= '2025-01-01'
  AND c.c_005 = 0
GROUP BY substr(c.c_045, 1, 7);
