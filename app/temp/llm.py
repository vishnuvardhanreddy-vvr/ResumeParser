import os
from dotenv import load_dotenv
from openai import AzureOpenAI, AsyncAzureOpenAI

load_dotenv()

deployment_model = os.getenv("gptmodel").split('/')[-1]


def get_llm():
    endpoint = os.getenv("gptendpoint")
    deployment = deployment_model
    apikey = os.getenv("gptkey")
    client = AsyncAzureOpenAI(
        api_key=apikey,
        api_version=os.getenv("gptversion"),
        base_url=f"{endpoint}/openai/deployments/{deployment}",

    )
    return client, deployment
