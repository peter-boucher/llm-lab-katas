from pydantic import BaseModel, Field
import pytest

from llm_client import LLMClient

class MockSQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

mock_response_format = {"type": "json_object"}
client = LLMClient()

@pytest.mark.vcr()
def test_chat_completion():
    messages = [{"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": """
    Which seller has delivered the most orders to customers in Rio de Janeiro?"
    Provide a JSON response with the following fields:
    - "seller_id": string containing the seller_id from sellers table
    - "sql_query": string containing the generated SQL code
    - "steps": list of strings containing the reasoning steps
    """}]
    response = client.chat_completion(messages, mock_response_format)
    assert "SELECT" in response.choices[0].message.content

@pytest.mark.vcr()
def test_chat_completion_parsed():
    messages = [{"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"}]
    response = client.chat_completion_parsed(messages, MockSQLGeneration)
    assert "SELECT" in response.choices[0].message.parsed.sql_query