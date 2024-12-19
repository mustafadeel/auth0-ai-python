import logging
import os
import ssl
import certifi
from dotenv import load_dotenv
import httpx
from termcolor import colored
from retriever import create_retriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.openai import OpenAI
import logging

load_dotenv()

# Unlike requests, the httpx package does not automatically pull in the environment
# variables SSL_CERT_FILE or SSL_CERT_DIR. If you want to use these they need to be enabled explicitly.
# https://www.python-httpx.org/advanced/ssl/#working-with-ssl_cert_file-and-ssl_cert_dir
ctx = ssl.create_default_context(
    cafile=os.environ.get("SSL_CERT_FILE", certifi.where()),
    capath=os.environ.get("SSL_CERT_DIR"),
)
http_client = httpx.Client(verify=ctx)

llm = OpenAI(
    model="gpt-4o-mini",
    http_client=http_client
)

def query(user: str, question: str):
    print(colored(f"{user}: {question}", 'blue'))
    retriever = create_retriever(user)

    query_engine = RetrieverQueryEngine.from_args(
        retriever=retriever,
        llm=llm
    )
    response = query_engine.query("What is the forecast for ZEKO?")

    print(response)


def main():
    openai_logger = logging.getLogger('openai')
    openai_logger.setLevel(logging.DEBUG)

    print("llama_index RAG with FGA demo")
    question = """what is the forecast for ZEKO?"""

    print("--------------------------")
    query("manuel", question)

    print("--------------------------")
    query("user1", question)


if __name__ == "__main__":
    main()
