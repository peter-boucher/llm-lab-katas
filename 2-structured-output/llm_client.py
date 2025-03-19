import logging
from openai import AzureOpenAI
import os
import dotenv


class LLMClient:
    dotenv.load_dotenv("../.env")
    ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    API_KEY = os.getenv("OPENAI_API_KEY") # Support for structured outputs was first added in API version 2024-08-01-preview. It is available in the latest preview APIs as well as the latest GA API: 2024-10-21.
    API_VER = os.getenv("AZURE_OPENAI_API_VERSION")
    MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    ## Supported models
    # gpt-4.5-preview version 2025-02-27
    # o3-mini version 2025-01-31
    # o1 version: 2024-12-17
    # gpt-4o-mini version: 2024-07-18
    # gpt-4o version: 2024-08-06
    # gpt-4o version: 2024-11-20

    logger = logging.getLogger(__name__)

    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=self.ENDPOINT,
            api_key=self.API_KEY,
            api_version=self.API_VER
        )

    def chat_completion_parsed(self, messages, response_format):
        self.logger.info(f"Sending query to LLM: {messages}")
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.MODEL,
                messages=messages,
                response_format=response_format
            )
            self.logger.info(f"Response: {response}")
            for step in response.choices[0].message.parsed.steps:
                self.logger.info(f"REASONING - Step: {step}")
            return response
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e

    def chat_completion(self, messages, response_format):
        self.logger.info(f"Sending query to LLM: {messages}")
        try:
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=messages,
                response_format=response_format
            )
            self.logger.info(f"Response: {response}")
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            raise e
