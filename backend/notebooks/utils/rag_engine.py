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
        self.llm = ChatOpenAI(model_name="gpt-4o-mini", openai_api_key=openai_key)
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


# class RAGChatbot:
#     def __init__(self, kb_items, chat_history=None):
#         openai_key = os.getenv("OPENAI_API_KEY")
#         # openai_key = "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"
#         self.llm = ChatOpenAI(model_name="gpt-4o", openai_api_key=openai_key)
#         self.embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
#         self.chat_history = chat_history or []

#         # Convert KB files into LangChain Documents
#         docs = []
#         for item in kb_items:
#             docs.append(Document(
#                 page_content=item["content"],
#                 metadata={"title": item.get("title", "Document")}
#             ))


#         # Text splitting
#         splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#         chunks = splitter.split_documents(docs)

#         # Create FAISS vector store
#         self.vectordb = FAISS.from_documents(chunks, self.embeddings)
#         self.retriever = self.vectordb.as_retriever()

#         # Set up RetrievalQA chain
#         self.qa = RetrievalQA.from_chain_type(
#             llm=self.llm,
#             chain_type="stuff",
#             retriever=self.retriever,
#             return_source_documents=False
#         )

#     def ask(self, query: str) -> str:
#         try:
#             sample_docs = self.retriever.get_relevant_documents(query)
#             history_text = "\n".join(
#                 f"{role.title()}: {msg}" for role, msg in self.chat_history[-10:]
#             )
#             print("!!!history", history_text)
#             result = self.qa.invoke({"query": query})
#             # prompt = f"{history_text}\nUser: {query}\nAssistant:"
#             # print("!!!prompt", prompt)
#             # result = self.qa.invoke({"query": prompt})
#             return result.get("result", "I apologize, but I couldn't generate a response. Please try again.")
#         except Exception as e:
#             return f"Sorry, I encountered an error while processing your question: {str(e)}"



class SuggestionRAGAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7)

    def generate_suggestions(self, chat_history: str):
        prompt = PromptTemplate.from_template("""
        You are a helpful AI research assistant. Based on the following conversation history between a user and assistant, suggest 3 helpful, relevant follow-up questions the user might ask next.

        Conversation History:
        {chat_history}

        Suggested Questions:
        1.
        2.
        3.
        """)
        try:
            response = self.llm.invoke(prompt.format(chat_history=chat_history))
            raw_output = response.content.strip()
            lines = raw_output.split("\n")
            cleaned = [line.split(".", 1)[-1].strip() for line in lines if line.strip()]
            return cleaned
        except Exception as e:
            return ["Summarize the conversation", "What are the next steps?", "Can you clarify the key findings?", "What insights stand out?"]
