# from langchain.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain.prompts import PromptTemplate
import os

from langchain.chains import ConversationalRetrievalChain

class RAGChatbot:
    def __init__(self, kb_items, chat_history=None):
        openai_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model_name="gpt-4.1-mini", openai_api_key=openai_key)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
        self.chat_history = chat_history or []

        # Load docs and split
        docs = [
            Document(page_content=item["content"], metadata={"title": item.get("title", "Document")})
            for item in kb_items
        ]
        chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(docs)
        
        # Vector store
        vectordb = FAISS.from_documents(chunks, self.embeddings)
        retriever = vectordb.as_retriever()
        self.retriever = retriever

        # Conversational chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            return_source_documents=False
        )
        print(f"[DEBUG] Total documents: {len(kb_items)}")
        print(f"[DEBUG] Total chunks created: {len(chunks)}")
        for i, chunk in enumerate(chunks[:5]):  # limit to first 5 for readability
            print(f"--- Chunk {i + 1} ---\n{chunk.page_content[:300]}\n")

    def ask(self, query: str) -> str:
        try:
            retrieved_docs = self.retriever.get_relevant_documents(query)
            print(f"[DEBUG] Retrieved {len(retrieved_docs)} documents for query: '{query}'")
            for i, doc in enumerate(retrieved_docs[:3]):  # show first 3 for brevity
                print(f"--- Retrieved Doc {i + 1} ---\n{doc.page_content[:300]}\n")

            result = self.chain.invoke({"question": query, "chat_history": self.chat_history})
            return result.get("answer", "I couldn’t generate a response.")
        except Exception as e:
            return f"Sorry, error during response: {str(e)}"


class SuggestionRAGAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-4.1-mini", temperature=0.7)

    def generate_suggestions(self, chat_history: str):
        prompt = PromptTemplate.from_template("""
        You are a helpful AI research assistant. Based on the following conversation history between a user and assistant, suggest 4 helpful, relevant follow-up questions the user might ask next.

        Conversation History:
        {chat_history}

        Suggested Questions:
        1.
        2.
        3.
        4.
        """)
        try:
            response = self.llm.invoke(prompt.format(chat_history=chat_history))
            raw_output = response.content.strip()
            lines = raw_output.split("\n")
            cleaned = [line.split(".", 1)[-1].strip() for line in lines if line.strip()]
            return cleaned
        except Exception as e:
            return ["What are the main themes across my documents?", "Can you identify key patterns or trends?", "How do these findings connect to my research goals?", "What should I explore next based on this analysis?"]