import logging
import time
from openai import AzureOpenAI
import os
import dotenv
from pydantic import BaseModel, Field

class LLMClient:
    dotenv.load_dotenv("../.env")
    ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    API_KEY = os.getenv("OPENAI_API_KEY")
    API_VER = os.getenv("AZURE_OPENAI_API_VERSION") # Support for structured outputs was first added in API version 2024-08-01-preview. It is available in the latest preview APIs as well as the latest GA API: 2024-10-21.
    MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    ## Supported models
    # gpt-4.5-preview version 2025-02-27
    # o3-mini version 2025-01-31
    # o1 version: 2024-12-17
    # gpt-4o-mini version: 2024-07-18
    # gpt-4o version: 2024-08-06
    # gpt-4o version: 2024-11-20

    logger = logging.getLogger(__name__)

    chat_history = []

    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=self.ENDPOINT,
            api_key=self.API_KEY,
            api_version=self.API_VER
        )

    def add_chat_history(self, messages):
        self.chat_history.append({'timestamp': time.time(), 'conversation': messages})

    def chat_completion_parsed(self, messages, response_format, include_history=True):
        if include_history:
            if len(self.chat_history) > 0:
                history = self.recall_chat_history()
                messages = history + messages
        self.logger.info(f"Sending query to LLM: {messages}")
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.MODEL,
                messages=messages,
                response_format=response_format
            )
            self.logger.info(f"Response: {response}")
            self.add_chat_history(messages)
            self.add_chat_history(response.choices[0].message)
            for step in response.choices[0].message.parsed.steps:
                self.logger.info(f"REASONING - Step: {step}") #TODO: client doesn't know about sturcture of response_format
            return response
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e

    def recall_chat_history(self):
        messages = []
        for item in self.chat_history:
            if not isinstance(item['conversation'], list):
                messages.append(item['conversation'])
            else:
                for message in item['conversation']:
                    if 'role' in message and message['role'] != 'system': # Add only the user and assistant messages
                        messages.append(message)
        return messages

    def chat_completion(self, messages, response_format, include_history=True):
        if include_history:
            if len(self.chat_history) > 0:
                history = self.recall_chat_history()
                messages = history + messages
        self.logger.info(f"Sending query to LLM: {messages}")
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                response_format=response_format
            )
            self.logger.info(f"Response: {response}")
            self.add_chat_history(messages)
            self.add_chat_history(response.choices[0].message)
            return response
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e

if __name__ == "__main__":
    class SQLGeneration(BaseModel):
        # role: str = Field(..., description="The role of the message")
        steps: list[str] = Field(..., description="Short chain-of-thought steps explaining the logic")
        sql_query: str = Field(..., description="The final SQL query to answer the user request")

    client = LLMClient()
    messages = [
        {"role": "system", "content": "You are an expert in Olist's DB. Provide 1-3 short reasoning steps, then a final SQL."},
        {"role": "user", "content": "Which seller has delivered the most orders to customers in Rio de Janeiro?"}
    ]
    response = client.chat_completion_parsed(messages, SQLGeneration)
    messages = [
        {"role": "user", "content": "How many orders did they deliver to customers in Rio de Janeiro?"}
    ]
    response = client.chat_completion_parsed(messages, SQLGeneration)
    pass