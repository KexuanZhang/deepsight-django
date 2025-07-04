#!/usr/bin/env python3
import os
import re
import json
import argparse
from pathlib import Path

from pymilvus import connections
from PyPDF2 import PdfReader
from langchain_community.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_milvus import Milvus

# — Summarization prompts —
map_prompt = PromptTemplate(
    input_variables=["text"],
    template=(
        "Summarize the following paper content *focusing on technical details*, "
        "*methods*, *results*, and *implications*:\n\n{text}"
    )
)
combine_prompt = PromptTemplate(
    input_variables=["summaries"],
    template=(
        "Combine these partial summaries into a single, concise, technical-focused summary:\n\n{summaries}"
    )
)

def extract_text_until_references(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    full = "\n".join(page.extract_text() or "" for page in reader.pages)
    # cut off at References (case insensitive)
    return re.split(r'(?mi)^\s*References\b', full)[0].strip()

def ingest_papers(
    root_dir: Path,
    milvus_host: str,
    milvus_port: str,
    collection_name: str,
    openai_api_key: str,
    model_name: str,
    chunk_size: int,
    chunk_overlap: int
):
    # 1) Connect to Milvus
    connections.connect(host=milvus_host, port=milvus_port)
    print(f"[Milvus] Connected to {milvus_host}:{milvus_port}")

    # 2) Build summarizer
    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        model_name=model_name,
        temperature=0
    )
    summarizer = load_summarize_chain(
        llm=llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
        combine_document_variable_name="summaries"
    )

    # 3) Walk rag/input/<conf>/<year>/*.pdf
    raw_docs = []
    for conf_dir in sorted(root_dir.iterdir()):
        if not conf_dir.is_dir(): continue
        for year_dir in sorted(conf_dir.iterdir()):
            if not year_dir.is_dir(): continue
            for pdf_file in sorted(year_dir.glob("*.pdf")):
                print(f"[{conf_dir.name}/{year_dir.name}] Summarizing {pdf_file.name}")
                text    = extract_text_until_references(pdf_file)
                summary = summarizer.run([Document(page_content=text)]).strip()
                raw_docs.append(Document(
                    page_content=summary,
                    metadata={
                        "conference": conf_dir.name,
                        "year":       year_dir.name,
                        "title":      pdf_file.stem
                    }
                ))

    print(f"[Summaries] Generated for {len(raw_docs)} papers")

    # 4) Chunk summaries
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(raw_docs)
    print(f"[Chunking] Produced {len(chunks)} chunks")

    # 5) Embed & ingest into Milvus (wiping old collection)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    Milvus.from_documents(
        documents       = chunks,
        embedding       = embeddings,
        collection_name = collection_name,
        connection_args = {"host": milvus_host, "port": milvus_port},
        drop_old        = True
    )
    print(f"[Milvus] Ingested chunks into '{collection_name}'")

    # 6) Save flat JSON of summaries
    out = [
        {"conference": d.metadata["conference"],
         "year":       d.metadata["year"],
         "title":      d.metadata["title"],
         "summary":    d.page_content}
        for d in raw_docs
    ]
    with open("papers_summaries.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("[Output] Written papers_summaries.json")

if __name__ == "__main__":
    here = Path(__file__).parent
    default_root = here.parent / "rag" / "input"

    p = argparse.ArgumentParser(
        description="Summarize & ingest PDFs under rag/input/<conference>/<year>"
    )
    p.add_argument(
        "--root", "-r",
        type=Path,
        default=default_root,
        help=f"Root folder (default: {default_root})"
    )
    p.add_argument(
        "--host", "-H",
        default=os.getenv("MILVUS_HOST","localhost"),
        help="Milvus host"
    )
    p.add_argument(
        "--port", "-P",
        default=os.getenv("MILVUS_PORT","19530"),
        help="Milvus port"
    )
    p.add_argument(
        "--collection", "-c",
        default=os.getenv("MILVUS_COLLECTION_NAME","papers_summary_collection"),
        help="Milvus collection name"
    )
    p.add_argument(
        "--api_key", "-k",
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key"
    )
    p.add_argument(
        "--model", "-m",
        default="gpt-4o-mini",
        help="OpenAI model for summarization"
    )
    p.add_argument(
        "--chunk_size",
        type=int,
        default=1000,
        help="Characters per chunk"
    )
    p.add_argument(
        "--chunk_overlap",
        type=int,
        default=100,
        help="Overlap between chunks"
    )
    args = p.parse_args()

    if not args.api_key:
        p.error("Missing OpenAI API key; use --api_key or set OPENAI_API_KEY")

    ingest_papers(
        root_dir        = args.root,
        milvus_host     = args.host,
        milvus_port     = args.port,
        collection_name = args.collection,
        openai_api_key  = args.api_key,
        model_name      = args.model,
        chunk_size      = args.chunk_size,
        chunk_overlap   = args.chunk_overlap
    )
