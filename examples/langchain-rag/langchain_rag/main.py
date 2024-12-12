from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from termcolor import colored
from retriever import create_retriever
from langchain.prompts import PromptTemplate
load_dotenv()


def query(user: str, question: str):
    print(colored(f"{user}: {question}", 'blue'))
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    retriever = create_retriever(user)

    system_prompt = """
    Answer the user's question: {input} based on the following context {context}.
    Only use the information provided in the context. If you need more information, ask for it."""

    retrieval_qa_chat_prompt = PromptTemplate(
        template=system_prompt,
        input_variables=["context", "input"]
    )

    combine_docs_chain = create_stuff_documents_chain(
        llm, retrieval_qa_chat_prompt
    )
    chain = create_retrieval_chain(retriever, combine_docs_chain)


    result = chain.invoke({"input": question})

    print(result.get('answer'))


def main():
    print("Langchain RAG with FGA demo")
    question = """what is the forecast for ZEKO?"""
    print("--------------------------")
    query("manuel", question)
    print("--------------------------")
    query("user1", question)


if __name__ == "__main__":
    main()
