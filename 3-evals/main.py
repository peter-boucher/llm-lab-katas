import json
from pathlib import Path
from pydantic import BaseModel, Field
import logging
import sys

# Add the parent directory of "2-structured-output" to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "2-structured-output"))

# Now import the module
from sample_db_queries import examples

from db_client import Olist
from llm_client import LLMClient

llm_client = LLMClient()

logger = logging.getLogger(__name__)
try:
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='logs/app.log',
        filemode='w'
    )
except FileNotFoundError as e:
    logger.error(f"Couldn't find a logfile: {e}")
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )


def setup():
    global data
    data = Olist()

def build_prompt(question):
    messages = []
    messages.append(
        {"role": "user", "content": question}
    )
    logger.info(f"Constructed prompt: {messages}")
    return messages

def completion(messages):
    response = llm_client.chat_completion(
        messages=messages,
        response_format=SQLGeneration,
        include_history=True,
        parsed=True
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

def get_examples():
    output = []
    for example in examples:
        for message in example:
            if message['role'] == 'assistant':
                output.append(message['content'])
    return output

def answer_question(question):
    try: 
        assert data.connected
    except NameError:
        logger.info("Setting up the database connection")
        setup()
    
    response = completion(build_prompt(question))
    parsed_json = response.choices[0].message.parsed
    try:
        answer = data.execute_sql_query(parsed_json.sql_query)
        if answer.empty:
            logger.warning(f"Query returned an empty result set")
            raise ValueError("Query returned an empty result set")
        return answer
    except ValueError as e:
        logger.error(f"Query failed: {e}")
        answer = "Sorry, I'm afriad I cant't do that."
    except Exception as e:
        logger.info(f"Trying to recover by generating a fix for the query causing an error")
        improved_sql = generate_fix(e, parsed_json.sql_query, question)
        try:
            answer = data.execute_sql_query(improved_sql.choices[0].message.parsed.sql_query, iteration=1)
        except ValueError as e:
            logger.error(f"Query failed again: {e}")
            answer = "Sorry, I'm afriad I cant't do that."
    return answer

def evaluate_sql(generated_sql, correct_sql, query_description):
    """Evaluate the generated SQL against the correct SQL using an LLM"""
    eval_prompt = f"""
    As a SQL expert, evaluate the generated SQL query against the correct SQL query.
    
    Query task: {query_description}
    
    Generated SQL: {generated_sql}
    
    Correct SQL: {correct_sql}
    
    Provide a JSON response with the following fields:
    - "is_correct": boolean (true if functionally equivalent, false otherwise)
    - "errors": list of string errors if any (empty list if correct)
    - "correction": string with corrected SQL if needed (empty string if correct)
    - "explanation": string explaining what was wrong and how it was fixed
    """
    
    response = llm_client.chat_completion(
        messages=[{"role": "system", "content": "You are a SQL expert evaluator."},
                 {"role": "user", "content": eval_prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result


class SQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description=get_context() + json.dumps(examples))
    
    
if __name__ == "__main__":
    question = "Which seller has delivered the most orders to customers in Rio de Janeiro? [string: seller_id]"
    answer = answer_question(question)
    print(answer)
    # generated = 'SELECT ROUND((AVG(r.review_score * ov.order_value) - AVG(r.review_score) * AVG(ov.order_value)) / (STDEV(r.review_score) * STDEV(ov.order_value)), 2) AS correlation\nFROM (\n    SELECT order_id, SUM(price + freight_value) AS order_value\n    FROM order_items\n    GROUP BY order_id\n) ov\nJOIN order_reviews r ON ov.order_id = r.order_id;'
    # correct = 'WITH order_values AS (\n    SELECT order_id, SUM(price + freight_value) AS order_value\n    FROM order_items\n    GROUP BY order_id\n)\nSELECT r.review_score,\n       ROUND(AVG(ov.order_value), 2) AS avg_order_value\nFROM order_reviews r\nJOIN order_values ov ON r.order_id = ov.order_id\nGROUP BY r.review_score\nORDER BY r.review_score;'
    # print(data.execute_sql_query(correct))
    # validate_response = evaluate_sql(generated_sql=generated, correct_sql=correct, query_description=query_description)
    # print(validate_response)
    # => {"steps": ["Join reviews, filter...","Compute average score..."], "sql_query":"SELECT p.product_category_name ..."}
    # print(response.model_dump_json(indent=2))
    # try:
    #    iteration = 0
    #    output = data.execute_sql_query(parsed_json.sql_query)
    # except Exception as e:
    #     improved_sql = generate_fix(e, parsed_json.sql_query, question)
    #     improved_sql_json = improved_sql.choices[0].message.parsed
    #     output = data.execute_sql_query(improved_sql_json.sql_query, iteration+1)
    # last_query = "SELECT * FROM orderers WHERE order_status = 'delivered'"
    # print(data.execute_sql_query(last_query))
    # print(output)
    # print(llm_client.chat_history)