import os
from dotenv import load_dotenv
from fastapi import FastAPI
from azure.identity import (AzureCliCredential, ManagedIdentityCredential,
                            ChainedTokenCredential, get_bearer_token_provider)
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

# Read the .env file if present (on your PC). In Azure there is no .env:
# the endpoints are passed as environment variables instead.
load_dotenv()

# Identity: try your "az login" first (your PC),
# otherwise use the app's Managed Identity (in Azure).
cred = ChainedTokenCredential(
    AzureCliCredential(process_timeout=60),
    ManagedIdentityCredential())

# Client to call the AI models (chat + embed), keyless
aoai = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview",
    azure_ad_token_provider=get_bearer_token_provider(
        cred, "https://cognitiveservices.azure.com/.default"))

# Client to query the Search index created by ingest.py
search = SearchClient(os.environ["SEARCH_ENDPOINT"], "docs", cred)

SYSTEM = ("You are the internal assistant of Lumiere Bank. "
          "Answer ONLY from the SOURCES. "
          "Cite the source in square brackets. "
          "If the answer is not in the SOURCES, say: I don't know.")

def embed(text):
    # Turn text into a vector using the "embed" deployment
    return aoai.embeddings.create(model="embed", input=text).data[0].embedding

# Create the API
app = FastAPI()

# Route 1: GET /health -> simple check that the app is running
@app.get("/health")
def health():
    return {"status": "ok"}

# Route 2: GET /ask?q=... -> same logic as ask.py
@app.get("/ask")
def ask(q: str):
    # 1. Hybrid search: keywords + vector
    results = search.search(
        search_text=q,
        vector_queries=[VectorizedQuery(vector=embed(q),
                                        k_nearest_neighbors=3, fields="vector")],
        top=3)
    context = "\n\n".join(f"[{r['source']}] {r['content']}" for r in results)

    # 2. Ask the chat model, grounded on the sources
    r = aoai.responses.create(
        model="chat",
        instructions=SYSTEM,
        input=f"SOURCES:\n{context}\n\nQUESTION: {q}")

    # 3. Return JSON
    return {"question": q, "answer": r.output_text}