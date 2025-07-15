import os
import json
import queue
import threading
import re
from typing import List, Tuple, Optional, Generator

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
from langchain.prompts import PromptTemplate
from langchain.schema import BaseRetriever, Document, SystemMessage, HumanMessage
from langchain.callbacks.base import BaseCallbackHandler
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_milvus import Milvus
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Import your engine's HybridRetriever and global chain
from rag.engine import get_rag_chain, HybridRetriever
from pymilvus import connections, utility, CollectionSchema, FieldSchema, DataType, Collection
import logging

logger = logging.getLogger(__name__)
# ─── Configuration ─────────────────────────────────────────────────────────
MILVUS_HOST      = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT      = os.getenv("MILVUS_PORT", "19530")
# Base name for per-user collections; each user will get its own suffix
BASE_COLLECTION  = os.getenv("MILVUS_LOCAL_COLLECTION", "user_files")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")

connections.connect(
    alias="default",
    host=MILVUS_HOST,
    port=MILVUS_PORT,
)

def ensure_user_collection(coll_name: str):
    """Ensure the Milvus collection exists; create and index via Collection constructor if missing."""
    exists = utility.has_collection(coll_name, using="default")
    logger.debug("Checking Milvus collection %r exists? %s", coll_name, exists)
    if not exists:
        logger.info("Creating Milvus collection %r via Collection constructor", coll_name)
        # Define schema fields
        fields = [
            FieldSchema(name="pk",        dtype=DataType.INT64,        is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            FieldSchema(name="user_id",   dtype=DataType.INT64),
            FieldSchema(name="source",    dtype=DataType.VARCHAR,     max_length=512),
        ]
        schema = CollectionSchema(fields, description="Per-user file embeddings")
        # Create collection using the ORM Collection constructor
        coll = Collection(name=coll_name, schema=schema, using="default")
        # Create index on the embedding field for efficient similarity search
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        coll.create_index(field_name="embedding", index_params=index_params, using="default")
        # Load the collection into memory
        coll.load()
        logger.info("Collection %r created, indexed, and loaded", coll_name)

# Helper to derive a user-specific collection name
def user_collection(user_id: int) -> str:
    return f"{BASE_COLLECTION}_{user_id}"

# SSE-based streaming helper
def _pdf_to_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except PdfReadError:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

class SSEStreamer(BaseCallbackHandler):
    def __init__(self):
        self._queue = queue.Queue()
        self._stop = False
        self._last_norm = None

    def on_llm_new_token(self, token: str, **kwargs):
        norm = re.sub(r"\s+", " ", token).strip()
        if not norm or norm == self._last_norm:
            return
        self._queue.put(token)
        self._last_norm = norm

    def end_stream(self):
        self._stop = True

    def tokens(self):
        while not self._stop or not self._queue.empty():
            try:
                yield self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
        yield None

# Ingest helper (called on file upload, kept here if needed)
def add_user_content_documents(user_id: int, docs: List[Document]) -> None:
    coll_name = user_collection(user_id)
    ensure_user_collection(coll_name)

    # split into chunks
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100
    ).split_documents(docs)

    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        collection_name=coll_name,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
        auto_id=True,
    )
    store.add_documents(chunks)

    # flush + load
    coll = Collection(coll_name, using="default")
    coll.flush()
    coll.load()

def add_user_files(
    user_id: int,
    kb_items: List,  # now take model instances, not paths
) -> None:
    print("!!!Add")
    coll_name = user_collection(user_id)
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        collection_name=coll_name,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
        auto_id=True,
    )

    docs = []
    for item in kb_items:
        # Use the model's get_file_content method which handles both MinIO and local storage
        text = item.get_file_content()
        
        # If no processed content, try to get from inline content field
        if not text:
            text = item.content
            
        if not text:
            # Skip items without any content
            print(f"!!!Skipping item {item.id} - no content available")
            continue

        # Get source name from metadata or title
        source_name = item.title
        if item.file_metadata and 'original_filename' in item.file_metadata:
            source_name = item.file_metadata['original_filename']
        elif item.metadata and 'original_filename' in item.metadata:
            source_name = item.metadata['original_filename']
        elif item.metadata and 'filename' in item.metadata:
            source_name = item.metadata['filename']

        docs.append(Document(
            page_content=text,
            metadata={
                "user_id": user_id,
                "source": source_name,
                "kb_item_id": item.id,
            }
        ))

    print("!!!docs", docs)
    
    # Only proceed if we have documents
    if not docs:
        print("!!!No documents to add to Milvus")
        return
    
    # split into chunks and add
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    ).split_documents(docs)
    
    # Only add to Milvus if we have chunks
    if chunks:
        store.add_documents(chunks)
        print(f"!!!Added {len(chunks)} chunks to Milvus")
    else:
        print("!!!No chunks generated from documents")

    # make sure Milvus is up to date
    coll = Collection(coll_name)
    coll.flush()
    coll.load()


# Remove helper to delete vectors by source
def delete_user_file(user_id: int, source: str) -> None:
    coll_name = user_collection(user_id)
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        collection_name=coll_name,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
        auto_id=True,
    )
    expr = f'user_id=={user_id} && source=="{source}"'
    store.delete(expr=expr)


from typing import List, Optional
from langchain.schema import BaseRetriever, Document

class CombinedRetriever(BaseRetriever):
    """
    Combines local and global retrievers per-call.
    mode: 'local', 'global', or 'hybrid'
    filter_sources: optional list of source filenames
    """

    # Declare fields with defaults so Pydantic won’t complain
    local_retriever: BaseRetriever
    global_retriever: BaseRetriever
    k_local: int = 7
    k_global: int = 3
    mode: str = "hybrid"
    filter_sources: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        local_retriever: BaseRetriever,
        global_retriever: BaseRetriever,
        k_local: int = 7,
        k_global: int = 3,
        mode: str = "hybrid",
        filter_sources: Optional[List[str]] = None,
    ):
        # Pass everything into super so Pydantic sees all fields
        super().__init__(
            local_retriever=local_retriever,
            global_retriever=global_retriever,
            k_local=k_local,
            k_global=k_global,
            mode=mode,
            filter_sources=filter_sources,
        )

        assert mode in ("local", "global", "hybrid"), \
            "mode must be 'local', 'global', or 'hybrid'"

        # And keep your own easy-to-reference attributes
        self.local_retriever  = local_retriever
        self.global_retriever = global_retriever
        self.k_local          = k_local
        self.k_global         = k_global
        self.mode             = mode
        self.filter_sources   = filter_sources or []

    def get_relevant_documents(self, query: str) -> List[Document]:
        hits: List[Document] = []

        if self.mode in ("local", "hybrid"):
            hits.extend(self.local_retriever.get_relevant_documents(query)[: self.k_local])
        if self.mode in ("global", "hybrid"):
            hits.extend(self.global_retriever.get_relevant_documents(query)[: self.k_global])

        # filter by source if requested
        if self.filter_sources:
            hits = [d for d in hits if d.metadata.get("source") in self.filter_sources]

        # dedupe by source
        seen, results = set(), []
        for d in hits:
            key = d.metadata.get("source") or d.page_content[:30]
            if key not in seen:
                seen.add(key)
                results.append(d)

        return results



class RAGChatbot:
    """
    Hybrid local+global RAG with streaming via .stream().
    Each user has its own Milvus collection.
    """
    def __init__(
        self,
        user_id: int,
        k_local: int = 7,
        k_global: int = 3,
    ):
        self.user_id = user_id
        self.k_local = k_local
        self.k_global = k_global

        # persistent Milvus store per user
        coll_name = user_collection(user_id)
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.store = Milvus(
            embedding_function=self.embeddings,
            collection_name=coll_name,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
            drop_old=False,
        )

        # global retriever from engine
        self.global_retriever = get_rag_chain().retriever

        # LLM + SSE
        self.streamer = SSEStreamer()
        self.llm = ChatOpenAI(
            model_name     = "gpt-4o-mini",
            openai_api_key = OPENAI_API_KEY,
            streaming      = True,
            callbacks      = [self.streamer],
        )

    def stream(
        self,
        question: str,
        history: Optional[List[Tuple[str, str]]] = None,
        mode: str = "hybrid",
        filter_sources: Optional[List[str]] = None,
    ) -> Generator[str, None, None]:
        history = history or []
        # build local retriever with Milvus expr including filter_sources
        clauses = [f"user_id=={self.user_id}"]
        if filter_sources:
            quoted = ",".join(f'\"{s}\"' for s in filter_sources)
            clauses.append(f"source in [{quoted}]")
        expr = " and ".join(clauses)
        print("!!!expr!!!", expr)
        local_ret = self.store.as_retriever(search_kwargs={"k": self.k_local, "expr": expr})
        # combine with global
        combined = CombinedRetriever(
            local_retriever=local_ret,
            global_retriever=self.global_retriever,
            k_local=self.k_local,
            k_global=self.k_global,
            mode=mode,
            filter_sources=filter_sources,
        )
        docs = combined.get_relevant_documents(question)

        # emit metadata
        meta = {"type": "metadata", "docs": [
            {"source": d.metadata.get("source"), "snippet": d.page_content[:200].replace("\n", " ")}
            for d in docs
        ]}
        yield f"data: {json.dumps(meta)}\n\n"

        # prepare context
        context = "\n\n---\n\n".join(
            f"Source: {d.metadata.get('source')}\n{d.page_content[:500]}" for d in docs
        )
        system_prompt = (
            "You are an expert research assistant. Use the following snippets to answer the question:\n\n"
            f"{context}\n\nHistory:\n{history}\n\nQuestion:\n{question}\n\nAnswer:"  
        )

        # stream LLM tokens
        def _run():
            self.llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=question),
            ])
            self.streamer.end_stream()
        threading.Thread(target=_run, daemon=True).start()

        for token in self.streamer.tokens():
            if token is None:
                break
            yield f"data: {json.dumps({'type':'token','text':token})}\n\n"
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
