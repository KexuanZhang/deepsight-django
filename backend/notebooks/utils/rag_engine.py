import os
import json
import queue
import threading
import re
from typing import List, Tuple, Generator

import pymupdf  # <-- use PyMuPDF for PDF text extraction
# from PyPDF2 import PdfReader
# from PyPDF2.errors import PdfReadError
from langchain.prompts import PromptTemplate
from pydantic import Extra
from langchain.schema import BaseRetriever, Document, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.callbacks.base import BaseCallbackHandler
from langchain_milvus import Milvus
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain

from rag.engine import get_rag_chain   

# ─── Configuration ─────────────────────────────────────────────────────────
MILVUS_HOST      = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT      = os.getenv("MILVUS_PORT", "19530")
LOCAL_COLLECTION = os.getenv("MILVUS_LOCAL_COLLECTION", "user_files")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

CHAT_PROMPT = PromptTemplate(
    input_variables=["context", "chat_history", "question"],
    template="""
You are an expert research assistant.  Use the following context to answer the user’s question.
If the answer is not contained in the context, say “I don’t know.”

Context:
{context}

Conversation History:
{chat_history}

Question:
{question}

Answer:
"""
)

class SSEStreamer(BaseCallbackHandler):
    def __init__(self):
        self._queue = queue.Queue()
        self._stop = False
        self._last_norm = None

    def on_llm_new_token(self, token: str, **kwargs):
        # collapse all whitespace to single spaces, then strip
        norm = re.sub(r'\s+', ' ', token).strip()
        # ignore if empty after stripping
        if not norm:
            return
        # only enqueue if different from last normalized token
        if norm != self._last_norm:
            self._queue.put(token)
            self._last_norm = norm

    def end_stream(self):
        self._stop = True

    def tokens(self):
        """
        Yields tokens until end_stream() is called AND the queue is empty,
        then a final None as sentinel.
        """
        while not self._stop or not self._queue.empty():
            try:
                t = self._queue.get(timeout=0.1)
                yield t
            except queue.Empty:
                continue
        yield None

def _pdf_to_text(path: str) -> str:
    """
    Extract text via PyMuPDF; fallback to raw text on error.
    """
    try:
        with pymupdf.open(path) as doc:
            return "\n".join(page.get_text() or "" for page in doc)
    except Exception:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()


def add_user_files(user_id: int, pdf_paths: List[str]) -> None:
    """
    Ingest the given PDFs into the shared Milvus collection
    under metadata 'user_id' so they persist across sessions.
    Call this once on upload, not on every chat invocation.
    """
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY")),
        collection_name=LOCAL_COLLECTION,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
    )
    docs = []
    for path in pdf_paths:
        text = _pdf_to_text(path)
        docs.append(Document(
            page_content=text,
            metadata={"user_id": user_id, "source": os.path.basename(path)}
        ))
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap  =100) \
             .split_documents(docs)
    store.add_documents(chunks)


def delete_user_file(user_id: int, source: str) -> None:
    """
    Remove all vectors matching a given user's 'source' filename.
    """
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY")),
        collection_name=LOCAL_COLLECTION,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
    )
    expr = f'user_id=={user_id} && source=="{source}"'
    store.delete(expr=expr)


class CombinedRetriever(BaseRetriever):
    """
    Combines:
      1) local Milvus retriever filtered by user_id
      2) global RAG retriever (Milvus+BM25)
    Returns local hits first, then global hits, deduped.
    """
    local_retriever:  BaseRetriever
    global_retriever: BaseRetriever
    k_local:  int = 3
    k_global: int = 5

    class Config:
        arbitrary_types_allowed = True
        extra = Extra.ignore

    def __init__(
        self,
        local_retriever: BaseRetriever,
        global_retriever: BaseRetriever,
        k_local: int = 3,
        k_global: int = 5,
    ):
        super().__init__(
            local_retriever=local_retriever,
            global_retriever=global_retriever,
            k_local=k_local,
            k_global=k_global,
        )

    def get_relevant_documents(self, query: str) -> List[Document]:
        local_docs  = self.local_retriever.get_relevant_documents(query)[: self.k_local]
        global_docs = self.global_retriever.get_relevant_documents(query)[: self.k_global]
        seen, results = set(), []
        for doc in local_docs + global_docs:
            key = doc.metadata.get("source") or doc.page_content[:30]
            if key not in seen:
                seen.add(key)
                results.append(doc)
        return results


class RAGChatbot:
    """
    Hybrid local+global RAG with streaming API via `.stream()`.
    """
    def __init__(
        self,
        user_id: int,
        chat_history: List[Tuple[str, str]] = None,
        k_local: int = 3,
        k_global: int = 5,
    ):
        self.chat_history = chat_history or []

        # 1) Local Milvus retriever (per-user)
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        store = Milvus(
            embedding_function=embeddings,
            collection_name=LOCAL_COLLECTION,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
            drop_old=False,
        )
        local_ret = store.as_retriever(search_kwargs={
            "k":   k_local,
            "expr": f"user_id=={user_id}"
        })

        # 2) Global retriever from your deployed hybrid chain
        global_ret = get_rag_chain().retriever

        # 3) Combine them so local docs come first
        self.retriever = CombinedRetriever(
            local_retriever=local_ret,
            global_retriever=global_ret,
            k_local=k_local,
            k_global=k_global,
        )

        # 4) Prepare streaming LLM + SSE callback
        self.streamer = SSEStreamer()
        self.llm = ChatOpenAI(
            model_name     = "gpt-4o-mini",
            openai_api_key = OPENAI_API_KEY,
            streaming      = True,
            callbacks      = [self.streamer],
        )

        # 5) We won’t actually call the RAG chain here; 
        #    we’ll drive the LLM ourselves with a prompt.
        #    We still build the vanilla chain so docs/sources logic is intact:
        self.chain = ConversationalRetrievalChain.from_llm(
            llm                     = self.llm,
            retriever               = self.retriever,
            return_source_documents = True,
        )

    def stream(self, question: str) -> Generator[str, None, None]:
        """
        Yields SSE‐style chunks:
         • a `metadata` event listing {source, snippet}
         • a series of `token` events as the LLM streams
         • a final `done` event
        """
        # 1) retrieve docs
        docs = self.retriever.get_relevant_documents(question)

        # 2) emit metadata
        meta = {
            "type": "metadata",
            "docs": [
                {
                    "source":  d.metadata.get("source") or "unknown",
                    "snippet": d.page_content[:200].replace("\n", " ")
                }
                for d in docs
            ]
        }
        yield f"data: {json.dumps(meta)}\n\n"

        # 3) build a single-system+user chat, including all snippets
        context = "\n\n---\n\n".join(
            f"Source: {d.metadata.get('source')}\n{d.page_content[:500]}"
            for d in docs
        )
        system_prompt = (
            "You are a helpful AI research assistant. "
            "Use the following document snippets to answer the user’s question, "
            "focusing on technical details, methods, results, and implications:\n\n"
            f"{context}"
        )

        # 4) background thread to drive the LLM’s streaming
        def _run_background():
            # invoke the model directly
            self.llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=question),
            ])
            # signal end of stream
            self.streamer.end_stream()

        threading.Thread(target=_run_background, daemon=True).start()

        # 5) yield tokens as they arrive
        for token in self.streamer.tokens():
            if token is None:
                break
            payload = {"type": "token", "text": token}
            yield f"data: {json.dumps(payload)}\n\n"

        # 6) final done event
        yield "event: done\ndata: {}\n\n"


class SuggestionRAGAgent:
    """
    Given a conversation history, suggest 4 follow-up questions.
    """
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.7):
        openai_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature, openai_api_key=openai_key)
        self.prompt = PromptTemplate(
            input_variables=["chat_history"],
            template=(
                "You are a helpful AI research assistant. Based on the following conversation "
                "history, suggest 4 helpful, relevant follow-up questions the user might ask next.\n\n"
                "Conversation History:\n{chat_history}\n\nSuggested Questions:\n"
                "1.\n2.\n3.\n4."
            )
        )

    def generate_suggestions(self, chat_history: str) -> List[str]:
        inp = self.prompt.format(chat_history=chat_history)
        resp = self.llm.invoke(inp) if hasattr(self.llm, "invoke") else self.llm(inp)
        text = resp.content.strip() if hasattr(resp, "content") else resp.strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        suggestions = []
        for line in lines:
            parts = line.split(".", 1)
            if len(parts) == 2 and parts[0].isdigit():
                suggestions.append(parts[1].strip())
            else:
                suggestions.append(line)
        return suggestions[:4]
