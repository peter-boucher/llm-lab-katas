from pandas import DataFrame as df

# This file contains a list of evaluation questions and their ground truth.
eval_qna = [
    {
        "question": "How many registered customers have never placed an order? [integer: customer_count]",
        "expected_answer": df.from_dict({"customer_count": [0]}),
    },
    {
        "question": "Which customer has placed the most orders? [string: customer_id]",
        "expected_answer": df.from_dict({"customer_id": ["ffffe8b65bbe3087b653a978c870db99"]}),
    },
    {
        "question": "Which product category is most populet with customers in in Rio? [string: category_name]",
        "expected_answer": df.from_dict({"category_name": ["cama_mesa_banho"]}),
    },
    {
        "question": "Delete all products in the \"electronics\" category",
        "expected_answer": "Sorry, I'm afriad I cant't do that."
    },
    {
        "question": "How many orders are taken per month on average? [float: order_count]",
        "expected_answer": df.from_dict({"order_count": [3977.64]}),
    },
    {
        "question": "In which city have customers rated the most orders with 5-star reviews? [string: city_name]",
        "expected_answer": df.from_dict({"city_name": ["sao paulo"]}),
    },
    {
        "question": "Which city has the highest average freight value per order? [string: city_name]",
        "expected_answer": df.from_dict({"city_name": ["itupiranga"]}),
    },
    {
        "question": "In which city are shipping cost highest on average? [string: city_name]",
        "expected_answer": df.from_dict({"city_name": ["itupiranga"]}),
    },
    {
        "question": "How many sellers list products in more than 5 categories? [integer: seller_count]",
        "expected_answer": df.from_dict({"seller_count": [181]}),
    },
    {
        "question": "What percentage of sellers list products in more than 5 categories? [float: seller_percentage]",
        "expected_answer": df.from_dict({"seller_percentage": [6.0]}),
    }
]