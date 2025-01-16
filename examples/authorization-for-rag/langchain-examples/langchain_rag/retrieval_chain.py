from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class RetrievalChain:
    def __init__(self, engine):
        self.engine = engine

    @classmethod
    def create(cls, retriever):
        prompt = ChatPromptTemplate.from_template("""
            Answer the user's question: {input} based on the following context {context}.
            Only use the information provided in the context. If you need more information, ask for it.
        """)
        combine_docs_chain = create_stuff_documents_chain(
            llm=ChatOpenAI(temperature=0, model="gpt-4o-mini"), prompt=prompt
        )
        retrieval_chain = create_retrieval_chain(
            combine_docs_chain=combine_docs_chain, retriever=retriever
        )
        return cls(retrieval_chain)

    def query(self, query):
        response = self.engine.invoke({"input": query})
        return response
