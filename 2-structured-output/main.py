from pydantic import BaseModel, Field
from openai import AzureOpenAI
import dotenv
import os

dotenv.load_dotenv("../.env")
openai_api_key = os.getenv("OPENAI_API_KEY")
openai_base_url = os.getenv("AZURE_OPENAI_BASE_URL")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
azure_openai_model = os.getenv("AZURE_OPENAI_DEPLOYMENT")

client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=openai_api_key,
    api_version=azure_openai_api_version
)

class SQLGeneration(BaseModel):
    steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
    sql_query: str = Field(..., description="The final SQL query to answer the user request")

schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "SQLGeneration",
        "strict": True,
        "schema": SQLGeneration.model_json_schema()
    }
}

messages = [
    {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
    {"role": "user", "content": "Which product category has the highest average review score?"}
]

response = client.beta.chat.completions.parse(
    model=azure_openai_model,
    messages=messages,
    response_format=schema
)

parsed_json = response.choices[0].message.parsed
print(parsed_json)
# => {"steps": ["Join reviews, filter...","Compute average score..."], "sql_query":"SELECT p.product_category_name ..."}
print(response.model_dump_json(indent=2))
