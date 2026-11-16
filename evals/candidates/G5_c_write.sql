-- golden: G5_failure_rate
-- expect: blocked:read_only
-- note: Tries to change data.
DELETE FROM t_03
WHERE c_020 = 'failed'
  AND c_011 >= '2025-09-16 21:00:00';
