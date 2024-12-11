from langchain_rag.retriever import create_retriever
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
load_dotenv()


def main():
    vector_store = create_retriever()
    # Define a system prompt that tells the model how to use the retrieved context
    system_prompt = """You are an assistant for question-answering tasks.
    Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know.
    Use three sentences maximum and keep the answer concise.
    Context: {context}:"""

    # Define a question
    question = """Show me forecast for ZEKO"""

    # Retrieve relevant documents
    docs = vector_store.similarity_search(question, k=2)

    # Combine the documents into a single string
    docs_text = "".join(d.page_content for d in docs)

    # Populate the system prompt with the retrieved context
    system_prompt_fmt = system_prompt.format(context=docs_text)

    # Create a model
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    # Generate a response
    questions = model.invoke([SystemMessage(content=system_prompt_fmt),
                              HumanMessage(content=question)])

    # Print the response
    print(questions.content)
