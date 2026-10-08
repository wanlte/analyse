CREATE OR REPLACE TABLE dwd_order_detail AS
SELECT
    order_id,
    user_id,
    product_id,
    pay_time,
    pay_date,
    status,
    pay_amount,
    quantity,
    unit_price,
    channel,
    category,
    city,
    is_test
FROM stg_order_line
