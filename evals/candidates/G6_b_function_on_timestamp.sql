-- golden: G6_p2p_senders
-- expect: blocked:date_bounded
-- note: Gives the right answer, but wraps the timestamp in a function so the index goes unused. Blocked for cost, not correctness.
SELECT COUNT(DISTINCT t.c_012) AS senders, ROUND(AVG(t.c_017) / 100.0, 2) AS average_amount
FROM t_03 AS t
JOIN t_01 AS c ON c.c_001 = t.c_012
WHERE strftime('%Y-%m', t.c_011, '+3 hours') = '2025-12'
  AND t.c_020 = 'success'
  AND t.c_015 = 'p2p_transfer'
  AND c.c_005 = 0;
