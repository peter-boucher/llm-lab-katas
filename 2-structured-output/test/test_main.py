import pytest

import main

def test_setup():
    main.setup()
    assert main.data is not None

def test_build_prompt():
    question = "Which seller has delivered the most orders to customers in Rio de Janeiro? [string: seller_id]"
    result = main.build_prompt(question)
    assert "Which seller has delivered the most orders to customers in Rio de Janeiro?" in result[0]["content"]

@pytest.mark.vcr()
def test_completion():
    messages = [{"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"}]
    result = main.completion(messages)
    assert "SELECT" in result.choices[0].message.parsed.sql_query

@pytest.mark.vcr()
def test_generate_fix():
    last_query = "SELECT * FROM orderers WHERE order_status = 'delivered'"
    error = f"pandas.errors.DatabaseError: Execution failed on sql '{last_query}': no such table: orderers"
    original_prompt = "Which orders have been delivered?"
    result = main.generate_fix(error, last_query, original_prompt)
    assert "SELECT * FROM orders" in result.choices[0].message.parsed.sql_query

def test_get_context():
    result = main.get_context()
    assert "dataset from Olist Store" in result

def test_evaluate_answer_question():
    question = "Which seller has delivered the most orders to customers in Rio de Janeiro? [string: seller_id]"
    result = main.answer_question(question)
    assert "4a3ca9315b744ce9f8e9374361493884" in str(result)

@pytest.mark.vcr()
def test_evaluate_sql_simple():
    generated_sql = "SELECT * FROM orders"
    correct_sql = "SELECT * FROM orders WHERE order_status = 'delivered'"
    query_description = "Which orders have been delivered?"
    result = main.evaluate_sql(generated_sql, correct_sql, query_description)
    assert result["is_correct"] == False

@pytest.mark.vcr()
def test_evaluate_sql_valid():
    generated_sql = "SELECT * FROM orders WHERE order_status = 'delivered'"
    correct_sql = "SELECT total_order_value, customer_city FROM orders JOIN customers WHERE order_status = 'delivered' ORDER BY total_order_value DESC"
    query_description = "What cities are the highest value orders shipped to?"
    result = main.evaluate_sql(generated_sql, correct_sql, query_description)
    assert "is_correct" in result
    assert "errors" in result
    assert "correction" in result
    assert "explanation" in result