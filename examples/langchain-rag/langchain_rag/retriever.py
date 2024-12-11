import os
from langchain_community.docstore import InMemoryDocstore
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import faiss


def create_retriever():
    # Crear un modelo de embeddings
    embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")

    # Crear un FAISS index en memoria
    index = faiss.IndexFlatL2(1536)

    # Crear un docstore en memoria
    docstore = InMemoryDocstore({})

    # Crear un índice para mapear IDs de documentos
    index_to_docstore_id = {}

    # Crear el vector store utilizando FAISS e InMemoryDocstore
    vector_store = FAISS(embedding_model,
                         index, docstore, index_to_docstore_id)

    # Get the directory of the current file
    current_dir = os.path.dirname(__file__)

    # Construct the full path to the target file
    public_doc_path = os.path.join(current_dir, '../assets/docs/public-doc.md')
    private_doc_path = os.path.join(
        current_dir, '../assets/docs/private-doc.md')

    # Open and read the files
    with open(public_doc_path, 'r', encoding='utf-8') as file:
        public_doc_content = file.read()

    with open(private_doc_path, 'r', encoding='utf-8') as file:
        private_doc_content = file.read()

    # Agregar documentos al vector store
    documents = [
        Document(page_content=public_doc_content,
                 metadata={"id": 1, "access": "public"}),
        Document(page_content=private_doc_content,
                 metadata={"id": 2, "access": "private"}),
    ]

    for doc in documents:
        vector_store.add_documents([doc])

    return vector_store


__all__ = ["create_retriever"]
