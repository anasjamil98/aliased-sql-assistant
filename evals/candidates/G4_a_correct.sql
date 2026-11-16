-- golden: G4_signups_by_month
-- expect: pass
-- note: Follows every rule in the context.
SELECT substr(c.c_002, 1, 7) AS signup_month, COUNT(*) AS new_customers
FROM t_01 AS c
WHERE c.c_002 >= '2025-01-01'
  AND c.c_002 <  '2026-01-01'
  AND c.c_005 = 0
GROUP BY substr(c.c_002, 1, 7);
