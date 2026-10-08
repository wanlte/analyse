CREATE OR REPLACE TABLE ads_trade_daily_next AS
SELECT
    pay_date,
    channel,
    category,
    city,
    SUM(order_gmv) AS gmv,
    COUNT(*) AS orders
FROM (
    SELECT pay_date, channel, category, city, order_id, MAX(pay_amount) AS order_gmv
    FROM dwd_order_detail
    WHERE status = 'paid' AND COALESCE(is_test, 0) = 0
    GROUP BY 1, 2, 3, 4, 5
) AS one_order
GROUP BY 1, 2, 3, 4
