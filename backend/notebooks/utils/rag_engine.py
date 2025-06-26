from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document
import os

class RAGChatbot:
    def __init__(self, kb_items, chat_history=None):
        openai_key = os.getenv("OPENAI_API_KEY")
        # openai_key = "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"
        self.llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=openai_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
        self.chat_history = chat_history or []

        # Convert KB files into LangChain Documents
        docs = []
        for item in kb_items:
            docs.append(
                Document(
                    page_content=item["content"],
                    metadata={"title": item.get("title", "Document")},
                )
            )

        # Text splitting
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_documents(docs)

        # Create FAISS vector store
        self.vectordb = FAISS.from_documents(chunks, self.embeddings)
        self.retriever = self.vectordb.as_retriever()

        # Set up RetrievalQA chain
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=False,
        )

    def ask(self, query: str) -> str:
        try:
            print("key!!!", os.getenv("OPENAI_API_KEY"))
            # Optional: flatten chat history into preamble
            history_text = "\n".join(
                f"{role.title()}: {msg}" for role, msg in self.chat_history[-10:]
            )
            prompt = f"{history_text}\nUser: {query}\nAssistant:"

            result = self.qa.invoke({"query": prompt})
            return result.get("result", "I apologize, but I couldn't generate a response. Please try again.")
        except Exception as e:
            return f"Sorry, I encountered an error while processing your question: {str(e)}"
