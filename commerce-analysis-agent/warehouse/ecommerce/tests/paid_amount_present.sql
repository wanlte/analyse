SELECT COUNT(*) AS violations
FROM stg_order_line
WHERE order_id IS NULL
   OR (status = 'paid' AND pay_amount IS NULL)
