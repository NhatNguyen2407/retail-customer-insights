-- Run after: python scripts/prepare_data.py
-- SQLite revenue is positive completed sales, not net revenue after returns.

-- 1. Monthly sales and distinct orders
SELECT strftime('%Y-%m', invoice_date) AS month,
       ROUND(SUM(revenue), 2) AS revenue_gbp,
       COUNT(DISTINCT invoice_no) AS orders
FROM transactions
GROUP BY month
ORDER BY month;

-- 2. Ten best-performing countries
SELECT country, ROUND(SUM(revenue), 2) AS revenue_gbp,
       COUNT(DISTINCT invoice_no) AS orders
FROM transactions
GROUP BY country
ORDER BY revenue_gbp DESC
LIMIT 10;

-- 3. Repeat customer rate among identified customers
WITH customer_orders AS (
    SELECT customer_id, COUNT(DISTINCT invoice_no) AS orders
    FROM transactions
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT COUNT(*) AS known_customers,
       SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN orders >= 2 THEN 1 ELSE 0 END)
              / NULLIF(COUNT(*), 0), 2) AS repeat_rate_pct
FROM customer_orders;
