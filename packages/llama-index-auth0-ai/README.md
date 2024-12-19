```python
from llama_index.core import VectorStoreIndex, Document
from llama_index_auth0_ai import FGARetriever
from openfga_sdk.client.models import ClientCheckRequest
from openfga_sdk import ClientConfiguration
from openfga_sdk.credentials import CredentialConfiguration, Credentials

# Define some docs:
documents = [
    Document(text="This is a public doc",
              doc_id="public-doc"),
    Document(text="This is a private doc",
              doc_id="private-doc"),
]

# Create a vector store:
vector_store = VectorStoreIndex.from_documents(documents)

# Create a retriever:
base_retriever = vector_store.as_retriever()

# Create the FGA retriever wrapper:
retriever = FGARetriever(
    base_retriever,
    fga_configuration=ClientConfiguration(
        api_host=os.getenv('FGA_API_HOST'),
        store_id=os.getenv('FGA_STORE_ID'),
        credentials=Credentials(
            method="client_credentials",
            configuration=CredentialConfiguration(
                api_issuer=os.getenv('FGA_API_ISSUER'),
                api_audience=os.getenv('FGA_API_AUDIENCE'),
                client_id=os.getenv('FGA_CLIENT_ID'),
                client_secret=os.getenv('FGA_CLIENT_SECRET')
            )
        )
    ),
    build_query=lambda node: ClientCheckRequest(
        user=f'user:{user}',
        object=f'doc:{node.ref_doc_id}',
        relation="viewer",
    ))

# Create a query engine:
query_engine = RetrieverQueryEngine.from_args(
    retriever=retriever,
    llm=llm
)

# Query:
response = query_engine.query("What is the forecast for ZEKO?")

print(response)
```
