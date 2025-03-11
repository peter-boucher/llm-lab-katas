
# {"role": "user", "content": original_prompt},
# {"role": "assistant", "content": last_query},
examples = [
    {
        {"role": "user", "content": 'What is the average review score for each product category?'},
        {"role": "assistant", "content": 'SELECT \n    p.product_category_name, \n    ROUND(AVG(r.review_score), 2) AS avg_review_score\nFROM products p\nJOIN order_items oi ON p.product_id = oi.product_id\nJOIN order_reviews r ON oi.order_id = r.order_id\nGROUP BY p.product_category_name;'}
    },
    {
        {"role": "user", "content": 'What cities are the highest value orders shipped to?'},
        {"role": "assistant", "content": 'SELECT c.customer_city, SUM(oi.price + oi.freight_value) AS total_order_value\nFROM orders o\nJOIN order_items oi ON o.order_id = oi.order_id\nJOIN customers c ON o.customer_id = c.customer_id\nWHERE o.order_status = \'delivered\'\nGROUP BY c.customer_city\nORDER BY total_order_value DESC;'}
    },
    {
        {"role": "user", "content": 'How many orders were made in each month?'},
        {"role": "assistant", "content": 'SELECT strftime(\'%Y-%m\', order_purchase_timestamp) AS month, COUNT(*) AS order_count\nFROM orders\nGROUP BY month\nORDER BY month;'}
    },
    {
        {"role": "user", "content": 'Is there a correlation between review score and order value?'},
        {"role": "assistant", "content": 'WITH order_values AS (\n    SELECT order_id, SUM(price + freight_value) AS order_value\n    FROM order_items\n    GROUP BY order_id\n)\nSELECT r.review_score,\n       ROUND(AVG(ov.order_value), 2) AS avg_order_value\nFROM order_reviews r\nJOIN order_values ov ON r.order_id = ov.order_id\nGROUP BY r.review_score\nORDER BY r.review_score;'}
    },
    {
        {"role": "user", "content": ''},
        {"role": "assistant", "content": ''}
    }
]