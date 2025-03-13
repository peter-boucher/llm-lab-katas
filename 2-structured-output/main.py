from pathlib import Path
from pydantic import BaseModel, Field
import dotenv
import os
import logging

from db_client import Olist
from sample_db_queries import examples
from llm_client import LLMClient

llm_client = LLMClient()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class SQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

# schema = {
#     "type": "json_schema",
#     "json_schema": {
#         "name": "SQLGeneration",
#         "strict": True,
#         "schema": SQLGeneration.model_json_schema()
#     }
# }

def setup():
    global data
    data = Olist()

def build_prompt(question):
    context = get_context()
    messages = [
        {"role": "system", "content": context},
        {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."}
    ]
    list(map(lambda example: list(map(lambda message: messages.append(message), example)), examples))
    messages.append(
        {"role": "user", "content": question}
    )
    print(messages)
    return messages

def completion(messages):
    response = llm_client.chat_completion(
        messages=messages,
        response_format=SQLGeneration
    )
    return response

def generate_fix(error, last_query='', original_prompt=''):
    context = get_context()
    messages = [{"role": "system", "content": context},
                {"role": "user", "content": original_prompt},
                {"role": "assistant", "content": last_query},         
                {"role": "user", "content": "When running the SQL I recieved the following error: \n"
                  + str(error) + "\nPlease change the SQL query to fix the error. Provide 1-3 short reasoning steps, then a final SQL."}]
    return completion(messages)

def get_context():
    context = Path('../1-entry-assignment/context_prompt.md').read_text()
    return context

def answer_question(question):
    setup()
    response = completion(build_prompt(question))
    parsed_json = response.choices[0].message.parsed
    output = data.execute_sql_query(parsed_json.sql_query)
    return output

if __name__ == "__main__":
    answer = answer_question(question = "Which product category has the shortest average delivery time? [string: category_name]")
    print(answer)
    # => {"steps": ["Join reviews, filter...","Compute average score..."], "sql_query":"SELECT p.product_category_name ..."}
    # print(response.model_dump_json(indent=2))
    # try:
    #    iteration = 0
    #    output = data.execute_sql_query(parsed_json.sql_query)
    # except Exception as e:
    #     improved_sql = generate_fix(e, parsed_json.sql_query, question)
    #     improved_sql_json = improved_sql.choices[0].message.parsed
    #     output = data.execute_sql_query(improved_sql_json.sql_query, iteration+1)
                
    # print(output)