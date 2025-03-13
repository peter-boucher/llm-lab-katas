import logging
from openai import AzureOpenAI
import os
import dotenv

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

class LLMClient:
    def __init__(self):
        # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.client = AzureOpenAI(
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
            api_version=API_VER
        )

    def chat_completion(self, messages, response_format):
        logger.info(f"Sending query to LLM: {messages}")
        return self.client.beta.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=response_format
        )
