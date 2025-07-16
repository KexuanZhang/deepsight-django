# # backend/rag/engine.py

# import os
# import json

# from pymilvus import connections
# from pydantic import Extra
# from langchain.schema import BaseRetriever
# from langchain.docstore.document import Document
# from langchain_community.embeddings import OpenAIEmbeddings
# from langchain_community.chat_models import ChatOpenAI
# from langchain_community.retrievers import TFIDFRetriever
# from langchain.chains import ConversationalRetrievalChain
# from langchain_milvus import Milvus

# # ─── Configuration ─────────────────────────────────────────────────────────
# MILVUS_HOST     = os.getenv("MILVUS_HOST", "localhost")
# MILVUS_PORT     = os.getenv("MILVUS_PORT", "19530")
# COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "papers_summary_collection")
# OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")

# # ─── Connect to Milvus once ─────────────────────────────────────────────────
# connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

# # ─── Persistent vectorstore handle (no ingestion at startup) ───────────────
# _embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
# _vectorstore = Milvus(
#     embedding_function = _embeddings,
#     collection_name    = COLLECTION_NAME,
#     connection_args    = {"host": MILVUS_HOST, "port": MILVUS_PORT},
#     drop_old           = False,
# )

# # ─── Pre-build BM25 retriever once at import ─────────────────────────────────
# _MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# _PAPERS_JSON = os.path.join(_MODULE_DIR, "demo_paper_summaries.json")
# _papers = json.load(open(_PAPERS_JSON, "r", encoding="utf-8"))
# _bm25_docs = [Document(page_content=p["summary"], metadata=p) for p in _papers]
# _bm25_retriever = TFIDFRetriever.from_texts(
#     texts     = [d.page_content for d in _bm25_docs],
#     metadatas = [d.metadata     for d in _bm25_docs],
#     k         = 5,
# )


# class HybridRetriever(BaseRetriever):
#     """
#     A BaseRetriever that combines vector (Milvus) and BM25 retrievers.
#     """
#     vector_retriever: BaseRetriever
#     bm25_retriever:   BaseRetriever
#     k_vector: int = 5
#     k_bm25:   int = 5

#     class Config:
#         arbitrary_types_allowed = True
#         extra = Extra.ignore

#     def get_relevant_documents(self, query: str):
#         # 1) semantic top-K
#         vec_hits  = self.vector_retriever.get_relevant_documents(query)[: self.k_vector]
#         # 2) lexical top-K
#         bm25_hits = self.bm25_retriever.get_relevant_documents(query)[: self.k_bm25]
#         # 3) de-duplicate by filename (or snippet)
#         seen   = set()
#         result = []
#         for doc in vec_hits + bm25_hits:
#             key = doc.metadata.get("filename") or doc.page_content[:30]
#             if key not in seen:
#                 seen.add(key)
#                 result.append(doc)
#         return result


# def _build_chain() -> ConversationalRetrievalChain:
#     """
#     Assemble the hybrid RAG chain: Milvus vector + BM25 lexical retrieval.
#     """
#     # semantic retriever from Milvus
#     vector_retriever = _vectorstore.as_retriever(search_kwargs={"k": 5})

#     # hybrid retriever combining vector + BM25
#     hybrid_retriever = HybridRetriever(
#         vector_retriever = vector_retriever,
#         bm25_retriever   = _bm25_retriever,
#         k_vector         = 5,
#         k_bm25           = 5
#     )

#     # build the conversational chain with ChatOpenAI
#     llm = ChatOpenAI(
#         model_name     = "gpt-4o-mini",
#         temperature    = 0,
#         openai_api_key = OPENAI_API_KEY
#     )
#     return ConversationalRetrievalChain.from_llm(
#         llm                     = llm,
#         retriever               = hybrid_retriever,
#         return_source_documents = True
#     )


# # ─── Global RAG chain singleton ────────────────────────────────────────────
# RAG_CHAIN = _build_chain()


# def get_rag_chain() -> ConversationalRetrievalChain:
#     """
#     Retrieve the global RAG chain without re-indexing.
#     """
#     return RAG_CHAIN


# def rebuild_vector_chain():
#     """
#     Rebuild only the semantic (vector) part of the chain after
#     adding or deleting vectors. BM25 remains unchanged.
#     """
#     global RAG_CHAIN
#     RAG_CHAIN = _build_chain()


# # ─── Add / Delete API for live updates ──────────────────────────────────────
# def add_doc(summary: str, metadata: dict, id: str = None):
#     """
#     Add a new summary document to Milvus and refresh the RAG chain.
#     `id` is optional; if omitted, Milvus will auto-assign one.
#     """
#     doc = Document(page_content=summary, metadata=metadata)
#     _vectorstore.add_documents([doc], ids=[id] if id else None)
#     rebuild_vector_chain()


# def delete_doc_by_id(id: str):
#     """
#     Delete a document from Milvus by its vector ID, then refresh.
#     """
#     _vectorstore.delete(ids=[id])
#     rebuild_vector_chain()


# def delete_docs_by_expr(expr: str):
#     """
#     Delete documents matching a Milvus expression (e.g. 'conference=="cvpr2025"'),
#     then refresh.
#     """
#     _vectorstore.delete(expr=expr)
#     rebuild_vector_chain()

import os
import json

from pymilvus import connections
from pydantic import Extra
from langchain.schema import BaseRetriever
from langchain.docstore.document import Document
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain_community.retrievers import TFIDFRetriever
from langchain.chains import ConversationalRetrievalChain
from langchain_milvus import Milvus

# ─── Configuration ─────────────────────────────────────────────────────────
MILVUS_HOST     = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT     = os.getenv("MILVUS_PORT", "19530")
DEFAULT_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "papers_summary_collection")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")

# ─── Connect to Milvus once ─────────────────────────────────────────────────
connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

# ─── Persistent vectorstore handle (no ingestion at startup) ───────────────
_embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Default collection setup (global collections)
_vectorstore = Milvus(
    embedding_function=_embeddings,
    collection_name=DEFAULT_COLLECTION_NAME,
    connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
    drop_old=False,
)

# ─── Pre-build BM25 retriever once at import ─────────────────────────────────
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_PAPERS_JSON = os.path.join(_MODULE_DIR, "demo_paper_summaries.json")
_papers = json.load(open(_PAPERS_JSON, "r", encoding="utf-8"))
_bm25_docs = [Document(page_content=p["summary"], metadata=p) for p in _papers]
_bm25_retriever = TFIDFRetriever.from_texts(
    texts=[d.page_content for d in _bm25_docs],
    metadatas=[d.metadata for d in _bm25_docs],
    k=5,
)


class HybridRetriever(BaseRetriever):
    """
    A BaseRetriever that combines vector (Milvus) and BM25 retrievers.
    Handles a list of retrievers for vector retrieval.
    """
    vector_retrievers: list[BaseRetriever]
    bm25_retriever:   BaseRetriever
    k_vector: int = 5
    k_bm25:   int = 5

    class Config:
        arbitrary_types_allowed = True
        extra = Extra.ignore

    def get_relevant_documents(self, query: str):
        hits: list[Document] = []

        # Process all vector retrievers
        for vector_retriever in self.vector_retrievers:
            vec_hits = vector_retriever.get_relevant_documents(query)[: self.k_vector]
            hits.extend(vec_hits)

        # Process BM25 retriever
        bm25_hits = self.bm25_retriever.get_relevant_documents(query)[: self.k_bm25]
        hits.extend(bm25_hits)

        # Deduplicate by source (or snippet)
        seen = set()
        result = []
        for doc in hits:
            key = doc.metadata.get("source") or doc.page_content[:30]
            if key not in seen:
                seen.add(key)
                result.append(doc)
        return result


def _build_chain(selected_collections=None) -> ConversationalRetrievalChain:
    """
    Assemble the hybrid RAG chain: Milvus vector + BM25 lexical retrieval.
    
    :param selected_collections: A list of collection names to retrieve from (optional).
    """
    if selected_collections is None or len(selected_collections) == 0:
        # Default: use all global collections + the user's local collection
        collection_names = [DEFAULT_COLLECTION_NAME]  # Add any user local collection here if needed.
    else:
        collection_names = selected_collections

    # Initialize retrievers for selected collections
    vector_retrievers = []
    for collection_name in collection_names:
        vector_retrievers.append(
            Milvus(
                embedding_function=_embeddings,
                collection_name=collection_name,
                connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
                drop_old=False,
            ).as_retriever(search_kwargs={"k": 5})
        )

    # Create the hybrid retriever (multiple vector retrievers now supported)
    hybrid_retriever = HybridRetriever(
        vector_retrievers=vector_retrievers,
        bm25_retriever=_bm25_retriever,
        k_vector=5,
        k_bm25=5
    )

    # Build the conversational chain with ChatOpenAI
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0,
        openai_api_key=OPENAI_API_KEY
    )
    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=hybrid_retriever,
        return_source_documents=True
    )


# ─── Global RAG chain singleton ────────────────────────────────────────────
RAG_CHAIN = _build_chain()  # Default to all collections + user's local collection


def get_rag_chain(selected_collections=None) -> ConversationalRetrievalChain:
    """
    Retrieve the global RAG chain with selected collections.
    If no collections are selected, the default global collections and local collections are used.
    """
    return _build_chain(selected_collections)


def rebuild_vector_chain(selected_collections=None):
    """
    Rebuild only the semantic (vector) part of the chain after
    adding or deleting vectors. BM25 remains unchanged.
    """
    global RAG_CHAIN
    RAG_CHAIN = _build_chain(selected_collections)
