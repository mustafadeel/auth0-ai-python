import os
from langchain_community.docstore import InMemoryDocstore
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain_auth0_ai import FGARetriever
from openfga_sdk.client.models import ClientCheckRequest
from openfga_sdk import ClientConfiguration
from openfga_sdk.credentials import CredentialConfiguration, Credentials

import faiss


def create_retriever(user: str):
    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

    index = faiss.IndexFlatL2(1536)

    docstore = InMemoryDocstore({})

    index_to_docstore_id = {}

    vector_store = FAISS(embedding_model,
                         index, docstore, index_to_docstore_id)

    current_dir = os.path.dirname(__file__)

    public_doc_path = os.path.join(current_dir, '../assets/docs/public-doc.md')
    private_doc_path = os.path.join(
        current_dir, '../assets/docs/private-doc.md')

    with open(public_doc_path, 'r', encoding='utf-8') as file:
        public_doc_content = file.read()

    with open(private_doc_path, 'r', encoding='utf-8') as file:
        private_doc_content = file.read()

    documents = [
        Document(page_content=public_doc_content,
                 metadata={"id": "public-doc", "access": "public"}),
        Document(page_content=private_doc_content,
                 metadata={"id": "private-doc", "access": "private"}),
    ]

    for doc in documents:
        vector_store.add_documents([doc])

    retriever = vector_store.as_retriever()

    return FGARetriever(
        retriever,
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
        build_query=lambda doc: ClientCheckRequest(
            user=f'user:{user}',
            object=f'doc:{doc.metadata.get("id")}',
            relation="viewer",
        ))


__all__ = ["create_retriever"]
