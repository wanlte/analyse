CREATE OR REPLACE TABLE dws_user_daily AS
SELECT
    pay_date,
    user_id,
    COUNT(*) AS orders,
    SUM(order_gmv) AS gmv
FROM (
    SELECT pay_date, user_id, order_id, MAX(pay_amount) AS order_gmv
    FROM dwd_order_detail
    WHERE status = 'paid' AND COALESCE(is_test, 0) = 0
    GROUP BY 1, 2, 3
) AS one_order
GROUP BY 1, 2
