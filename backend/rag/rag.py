import os
import json
import queue
import threading
import re
import uuid
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
from rag.engine import get_rag_chain, HybridRetriever, DEFAULT_COLLECTION_NAME

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
    exists = utility.has_collection(coll_name, using="default")
    logger.debug("Checking Milvus collection %r exists? %s", coll_name, exists)
    if not exists:
        logger.info("Creating Milvus collection %r via Collection constructor", coll_name)
        fields = [
            FieldSchema(name="pk",        dtype=DataType.INT64,        is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            FieldSchema(name="user_id",   dtype=DataType.VARCHAR, max_length=64),  # <-- changed
            FieldSchema(name="source",    dtype=DataType.VARCHAR,     max_length=512),
        ]
        schema = CollectionSchema(fields, description="Per-user file embeddings")
        coll = Collection(name=coll_name, schema=schema, using="default")
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        coll.create_index(field_name="embedding", index_params=index_params, using="default")
        coll.load()
        logger.info("Collection %r created, indexed, and loaded", coll_name)

# Helper to derive a user-specific collection name
def user_collection(user_id: str) -> str:
    # Ensure only numbers, letters, and underscores
    safe_user_id = str(user_id).replace("-", "_")
    return f"{BASE_COLLECTION}_{safe_user_id}"

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
    )
    store.add_documents(chunks)

    # flush + load
    coll = Collection(coll_name, using="default")
    coll.flush()
    coll.load()

def add_user_files(
    user_id: int,
    kb_items: List,  # KnowledgeBaseItem model instances
) -> None:
    coll_name = user_collection(user_id)
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        collection_name=coll_name,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
    )

    docs = []
    for item in kb_items:
        text = None
        source_name = None

        # Use inline content if present (from extracted markdown)
        if getattr(item, "content", None):
            print(f"[DEBUG] Ingesting inline content for item {item.id}")
            text = item.content
            source_name = f"inline_{item.id}"
        # Fallback to extracted markdown file if present
        elif getattr(item, "extracted_md_object_key", None):
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                content = backend.get_file(item.extracted_md_object_key)
                print(f"[DEBUG] Ingesting extracted markdown for item {item.id}: key={item.extracted_md_object_key}")
                print(f"[DEBUG] Extracted markdown content (first 200 chars): {content[:200] if isinstance(content, bytes) else str(content)[:200]}")
                text = content.decode('utf-8') if isinstance(content, bytes) else content
                source_name = item.extracted_md_object_key.rsplit("/", 1)[-1]
            except Exception as e:
                print(f"[ERROR] Error reading extracted markdown for item {item.id}: {e}")
                continue
        # Fallback to processed file
        elif getattr(item, "file_object_key", None):
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                content = backend.get_file(item.file_object_key)
                print(f"[DEBUG] Ingesting processed file for item {item.id}: key={item.file_object_key}")
                text = content.decode('utf-8') if isinstance(content, bytes) else content
                source_name = item.file_object_key.rsplit("/", 1)[-1]
            except Exception as e:
                print(f"[ERROR] Error reading processed file for item {item.id}: {e}")
                continue
        elif getattr(item, "original_file_object_key", None):
            try:
                from notebooks.utils.storage import get_minio_backend
                backend = get_minio_backend()
                content = backend.get_file(item.original_file_object_key)
                print(f"[DEBUG] Ingesting original file for item {item.id}: key={item.original_file_object_key}")
                text = content.decode('utf-8') if isinstance(content, bytes) else content
                source_name = item.original_file_object_key.rsplit("/", 1)[-1]
            except Exception as e:
                print(f"[ERROR] Error reading original file for item {item.id}: {e}")
                continue
        else:
            print(f"[WARN] Skipping item {getattr(item, 'id', None)}: no file or content attached.")
            continue

        docs.append(Document(
            page_content=text,
            metadata={
                "user_id": str(user_id),
                "source": source_name,
                "kb_item_id": str(item.id),
            }
        ))

    print(f"[DEBUG] Total docs to ingest for user {user_id}: {len(docs)}")
    if not docs:
        print("[WARN] No valid files or content to add for user", user_id)
        return

    # split into chunks and add
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    ).split_documents(docs)

    print(f"[DEBUG] Total chunks to ingest for user {user_id}: {len(chunks)}")
    
    # Generate unique IDs for each chunk
    chunk_ids = [str(uuid.uuid4()) for _ in chunks]
    
    # Add documents with explicit IDs
    store.add_documents(chunks, ids=chunk_ids)

    # make sure Milvus is up to date
    coll = Collection(coll_name)
    coll.flush()
    coll.load()
    print(f"[DEBUG] Milvus collection '{coll_name}' flushed and loaded after ingest.")


# Remove helper to delete vectors by source
def delete_user_file(user_id: int, source: str) -> None:
    coll_name = user_collection(user_id)
    store = Milvus(
        embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        collection_name=coll_name,
        connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
        drop_old=False,
    )
    expr = f'user_id=={user_id} && source=="{source}"'
    store.delete(expr=expr)


from typing import List, Optional
from langchain.schema import BaseRetriever, Document

class CombinedRetriever(BaseRetriever):
    """
    Combines local and global retrievers per-call.
    filter_sources: optional list of source filenames
    """

    local_retriever: BaseRetriever
    global_retriever: BaseRetriever
    k_local: int = 7
    k_global: int = 3
    filter_sources: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        local_retriever: BaseRetriever,
        global_retriever: BaseRetriever,
        k_local: int = 7,
        k_global: int = 3,
        filter_sources: Optional[List[str]] = None,
    ):
        super().__init__(
            local_retriever=local_retriever,
            global_retriever=global_retriever,
            k_local=k_local,
            k_global=k_global,
            filter_sources=filter_sources,
        )

        self.local_retriever  = local_retriever
        self.global_retriever = global_retriever
        self.k_local          = k_local
        self.k_global         = k_global
        self.filter_sources   = filter_sources or []

    def get_relevant_documents(self, query: str) -> List[Document]:
        hits: List[Document] = []

        hits.extend(self.local_retriever.get_relevant_documents(query)[: self.k_local])
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
    RAG with streaming via .stream().
    Each user has its own Milvus collection.
    Supports specifying additional collections for retrieval.
    """
    def __init__(
        self,
        user_id: int,
        k_local: int = 7,
        k_global: int = 3,
        extra_collections: Optional[List[str]] = None,
    ):
        self.user_id = str(user_id)
        self.k_local = k_local
        self.k_global = k_global
        self.extra_collections = extra_collections or []

        # persistent Milvus store per user
        coll_name = user_collection(user_id)
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.store = Milvus(
            embedding_function=self.embeddings,
            collection_name=coll_name,
            connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
            drop_old=False,
        )

        # Build list of collections to retrieve from
        self.selected_collections = [coll_name]
        # If extra_collections specified, add them; else default to 'global'
        if self.extra_collections:
            self.selected_collections.extend(self.extra_collections)
        else:
            self.selected_collections.append(DEFAULT_COLLECTION_NAME)

        # global retriever from engine, using selected collections
        self.global_retriever = get_rag_chain(self.selected_collections).retriever

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
        file_ids: Optional[List[str]] = None,
    ) -> Generator[str, None, None]:
        history = history or []

        clauses = [f'user_id=="{self.user_id}"']
        if file_ids:
            quoted = ",".join(f'"{fid}"' for fid in file_ids)
            clauses.append(f"kb_item_id in [{quoted}]")
        expr = " and ".join(clauses)
        local_ret = self.store.as_retriever(search_kwargs={"k": self.k_local, "expr": expr})

        # Retrieve local and global docs separately
        local_docs = local_ret.get_relevant_documents(question)[:self.k_local]
        global_docs = []
        if not file_ids:
            combined = CombinedRetriever(
                local_retriever=local_ret,
                global_retriever=self.global_retriever,
                k_local=self.k_local,
                k_global=self.k_global,
                filter_sources=None,
            )
            docs = combined.get_relevant_documents(question)
        else:
            # If file_ids are set, only retrieve global docs for reference
            global_docs = self.global_retriever.get_relevant_documents(question)[:self.k_global]
            docs = local_docs + global_docs

        print(f"Retrieved {len(docs)} documents for question: {question}")
        print("Retrieved kb_item_ids:", [d.metadata.get("kb_item_id") for d in docs])
        print("Selected file_ids:", file_ids)

        # emit metadata
        meta = {"type": "metadata", "docs": [
            {"source": d.metadata.get("source"), "snippet": d.page_content[:200].replace("\n", " ")}
            for d in docs
        ]}
        yield f"data: {json.dumps(meta)}\n\n"

        # prepare context with emphasis
        local_context = "\n\n---\n\n".join(
            f"Source: {d.metadata.get('source')} (User Selected)\n{d.page_content[:500]}" for d in local_docs
        )
        global_context = "\n\n---\n\n".join(
            f"Source: {d.metadata.get('source')} (Global Reference)\n{d.page_content[:500]}" for d in global_docs
        )

        if local_context and global_context:
            context = (
                "USER SELECTED FILES (PRIORITIZE THESE):\n"
                f"{local_context}\n\n"
                "GLOBAL/REFERENCE DOCUMENTS (FOR ADDITIONAL CONTEXT ONLY):\n"
                f"{global_context}"
            )
        elif local_context:
            context = f"USER SELECTED FILES:\n{local_context}"
        else:
            context = f"GLOBAL/REFERENCE DOCUMENTS:\n{global_context}"

        system_prompt = (
            "You are an expert research assistant. Use the following snippets to answer the question.\n"
            "Give highest priority to information from USER SELECTED FILES. Use GLOBAL/REFERENCE DOCUMENTS only if needed for additional context or clarification.\n\n"
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