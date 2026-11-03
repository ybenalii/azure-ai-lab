import os, sys
from dotenv import load_dotenv
from azure.identity import AzureCliCredential, DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

load_dotenv()
cred = AzureCliCredential()
aoai = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2025-04-01-preview",
    azure_ad_token_provider=get_bearer_token_provider(
        cred, "https://cognitiveservices.azure.com/.default"))

SEARCH, INDEX = os.environ["SEARCH_ENDPOINT"], "docs"

def embed(text):
    return aoai.embeddings.create(model="embed", input=text).data[0].embedding

q = sys.argv[1]

# Hybrid search: keywords (search_text) + meaning (vector) at the same time
results = SearchClient(SEARCH, INDEX, cred).search(
    search_text=q,
    vector_queries=[VectorizedQuery(vector=embed(q),
                                    k_nearest_neighbors=3, fields="vector")],
    top=3)

context = "\n\n".join(f"[{r['source']}] {r['content']}" for r in results)

system = ("You are the internal assistant of Lumiere Bank. "
          "Answer ONLY from the SOURCES. "
          "Cite the source in square brackets. "
          "If the answer is not in the SOURCES, say: I don't know.")

r = aoai.responses.create(
    model="chat",
    instructions=system,
    input=f"SOURCES:\n{context}\n\nQUESTION: {q}")

print(r.output_text)