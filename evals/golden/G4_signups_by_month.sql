-- question: How many new customers signed up in each month of 2025?
SELECT substr(signup_date, 1, 7), COUNT(*)
FROM customers
WHERE is_test_account = 0
  AND signup_date BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY substr(signup_date, 1, 7);
