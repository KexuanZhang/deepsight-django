from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
import os

openai_key = os.getenv("OPENAI_API_KEY")

class RAGChatbot:
    def __init__(self, kb_items):
        self.llm = ChatOpenAI(model_name="gpt-4.1-mini", openai_api_key=openai_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
        
        # Convert each KB file into a Document object
        docs = []
        for item in kb_items:
            docs.append(Document(
                page_content=item["content"],
                metadata={"title": item.get("title", "Document")}
            ))

        # Split
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        # Vector store
        self.vectordb = FAISS.from_documents(chunks, self.embeddings)
        self.retriever = self.vectordb.as_retriever()
        
        # Initialize RetrievalQA with FAISS vectorstore (simpler and more reliable)
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm, 
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=False
        )

    def ask(self, query: str) -> str:
        try:
            result = self.qa.invoke({"query": query})
            return result.get("result", "I apologize, but I couldn't generate a response. Please try again.")
        except Exception as e:
            return f"Sorry, I encountered an error while processing your question: {str(e)}"
