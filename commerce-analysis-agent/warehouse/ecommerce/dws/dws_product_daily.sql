CREATE OR REPLACE TABLE dws_product_daily AS
SELECT
    pay_date,
    product_id,
    SUM(quantity) AS quantity,
    SUM(quantity * unit_price) AS amount
FROM dwd_order_detail
WHERE status = 'paid' AND COALESCE(is_test, 0) = 0
GROUP BY 1, 2
