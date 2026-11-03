import os
from dotenv import load_dotenv
from azure.identity import (
    ClientSecretCredential,
    get_bearer_token_provider,
)
from openai import AzureOpenAI
load_dotenv()
credential = ClientSecretCredential(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"],
)
token_provider = get_bearer_token_provider(
    credential,
    "https://cognitiveservices.azure.com/.default",
)
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_ad_token_provider=token_provider,
    api_version="2025-04-01-preview",
)
previous_id = None

while(True) :
    question = input("-> : ")
    if question.lower() in ("exit", "quit", "q"):
        break
    response = client.responses.create(
    model="chat",
    input=question,
    previous_response_id=previous_id,
    )
    print (response.output_text)

    previous_id = response.id
    

