from pydantic import BaseModel, Field
import pytest

from llm_client import LLMClient

class MockSQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

mock_response_format = {"type": "json_object"}
client = LLMClient()

@pytest.fixture
def prompt_messages():
    return [
        {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
        {"role": "user", "content": """
        Which seller has delivered the most orders to customers in Rio de Janeiro?"
        Provide a JSON response with the following fields:
        - "seller_id": string containing the seller_id from sellers table
        - "sql_query": string containing the generated SQL code
        - "steps": list of strings containing the reasoning steps
        """}
    ]



@pytest.mark.vcr()
def test_chat_completion(prompt_messages):
    messages = prompt_messages
    response = client.chat_completion(messages, mock_response_format)
    assert "SELECT" in response.choices[0].message.content

@pytest.mark.vcr()
def test_chat_completion_history(prompt_messages):
    messages = prompt_messages

    response = client.chat_completion(messages, mock_response_format)
    chat_history = client.chat_history
    assert len(chat_history) > 0

@pytest.mark.vcr()
def test_chat_completion_followup_history(prompt_messages):
    messages = prompt_messages
    followup_messages = [{"role": "user", "content": """
    How many cystomers in Rio de Janeiro do they serve?"
    Provide a JSON response with the following fields:
    - "customers": integer containing the number of customers
    - "sql_query": string containing the generated SQL code
    - "steps": list of strings containing the reasoning steps
    """}]

    response = client.chat_completion(messages, mock_response_format)
    response = client.chat_completion(followup_messages, mock_response_format)
    assert len(client.chat_history) > 2

@pytest.mark.vcr()
def test_chat_completion_parsed():
    messages = [{"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"}]
    response = client.chat_completion(messages, MockSQLGeneration, parsed=True)
    assert "SELECT" in response.choices[0].message.parsed.sql_query

def test_recall_chat_history():
    client.chat_history = [{'conversation': [{'role': 'system', 'content': 'You are an expert in Olist\'s DB. Provide 1-3 short reasoning steps, then a final SQL.'},
    {'role': 'user', 'content': 'Which seller has delivered the most orders to customers in Rio de Janeiro?'}], 'timestamp': 1633046400}]

    recall = client.recall_chat_history()
    assert recall == [{'role': 'user', 'content': 'Which seller has delivered the most orders to customers in Rio de Janeiro?'}]

def test_recall_chat_history_not_contains_system_messages():
    client.chat_history = [{'conversation': [{'role': 'system', 'content': 'You are an expert in Olist\'s DB. Provide 1-3 short reasoning steps, then a final SQL.'},
    {'role': 'user', 'content': 'Which seller has delivered the most orders to customers in Rio de Janeiro?'}], 'timestamp': 1633046400}]

    recall = client.recall_chat_history()

    for message in recall:
        assert message['role'] != 'system'