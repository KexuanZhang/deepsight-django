from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
import os

openai_key = os.getenv("OPENAI_API_KEY")

class RAGChatbot:
    def __init__(self, kb_items):
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_key)
        self.embeddings = OpenAIEmbeddings()
        
        # Convert each KB file into a Document object
        docs = []
        for item in kb_items:
            docs.append(Document(
                page_content=item["content"],
                # metadata={"title": item["title"], "id": item["id"]}
            ))

        # Split
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        # Vector store
        self.vectordb = FAISS.from_documents(chunks, self.embeddings)
        self.retriever = self.vectordb.as_retriever()
        self.qa = RetrievalQA.from_chain_type(llm=self.llm, retriever=self.retriever)

    def ask(self, query: str) -> str:
        return self.qa.run(query)
