import os, glob
from dotenv import load_dotenv
from azure.identity import AzureCliCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile)
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
    # model= is the DEPLOYMENT name ("embed"), not the real model name
    return aoai.embeddings.create(model="embed", input=text).data[0].embedding

# Index structure: id, source file, text, and the vector (1536 numbers)
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchField(name="vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, vector_search_dimensions=1536,
                vector_search_profile_name="p"),
]
vs = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="h")],
    profiles=[VectorSearchProfile(name="p", algorithm_configuration_name="h")])

SearchIndexClient(SEARCH, cred).create_or_update_index(
    SearchIndex(name=INDEX, fields=fields, vector_search=vs))

# Split each file into chunks (1 paragraph = 1 chunk), embed, collect
docs, i = [], 0
for path in glob.glob("docs/*.md"):
    with open(path, encoding="utf-8") as f:
        for chunk in f.read().split("\n\n"):
            if chunk.strip():
                docs.append({"id": str(i),
                             "source": os.path.basename(path),
                             "content": chunk,
                             "vector": embed(chunk)})
                i += 1

SearchClient(SEARCH, INDEX, cred).upload_documents(docs)
print(f"{len(docs)} chunks indexed")