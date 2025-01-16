import os
from langchain.schema import Document


def read_documents():
    current_dir = os.path.dirname(__file__)
    public_doc_path = os.path.join(current_dir, "../assets/docs/public-doc.md")
    private_doc_path = os.path.join(current_dir, "../assets/docs/private-doc.md")

    with open(public_doc_path, "r", encoding="utf-8") as file:
        public_doc_content = file.read()

    with open(private_doc_path, "r", encoding="utf-8") as file:
        private_doc_content = file.read()

    documents = [
        Document(
            page_content=public_doc_content,
            metadata={"id": "public-doc", "access": "public"},
        ),
        Document(
            page_content=private_doc_content,
            metadata={"id": "private-doc", "access": "private"},
        ),
    ]

    return documents


__all__ = ["read_documents"]
