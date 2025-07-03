#!/usr/bin/env python3
import os
import re
import json
import argparse
from PyPDF2 import PdfReader
from pymilvus import connections
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_milvus import Milvus

# ——— Summarization prompts ———
map_prompt = PromptTemplate(
    input_variables=["text"],
    template=(
        "Summarize the following content *focusing on technical details*, "
        "*methods*, *results*, and *implications*:\n\n{text}"
    )
)
combine_prompt = PromptTemplate(
    input_variables=["summaries"],
    template=(
        "Combine these partial summaries into a single, concise, technical-focused summary:\n\n{summaries}"
    )
)

def extract_text_until_references(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return re.split(r'(?mi)^\s*References\b', full_text)[0].strip()

def initialize_and_ingest(
    root_dir: str,
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
    print(f"✅ Connected to Milvus at {milvus_host}:{milvus_port}")

    # 2) Set up summarization chain
    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        temperature=0,
        model_name=model_name
    )
    summarizer = load_summarize_chain(
        llm,
        chain_type="map_reduce",
        map_prompt=map_prompt,
        combine_prompt=combine_prompt,
        combine_document_variable_name="summaries"
    )

    # 3) Walk directory: conference/year/*.pdf
    raw_docs = []
    conferences = sorted(os.listdir(root_dir))
    for conf in conferences:
        conf_path = os.path.join(root_dir, conf)
        if not os.path.isdir(conf_path):
            continue
        for year in sorted(os.listdir(conf_path)):
            year_path = os.path.join(conf_path, year)
            if not os.path.isdir(year_path):
                continue
            pdfs = sorted(f for f in os.listdir(year_path) if f.lower().endswith(".pdf"))
            for i, fname in enumerate(pdfs, 1):
                pdf_path = os.path.join(year_path, fname)
                print(f"[{conf}/{year}] ({i}/{len(pdfs)}) Summarizing {fname}")
                # extract and summarize
                content = extract_text_until_references(pdf_path)
                summary = summarizer.run([Document(page_content=content)]).strip()
                # collect summary doc
                raw_docs.append(Document(
                    page_content=summary,
                    metadata={
                        "conference": conf,
                        "year":       year,
                        "filename":   fname
                    }
                ))

    print(f"✅ Summarized {len(raw_docs)} papers.")

    # 4) Chunk summaries
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    docs = splitter.split_documents(raw_docs)
    print(f"✅ Split into {len(docs)} chunks.")

    # 5) Embed & ingest into Milvus (wipe & start fresh)
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    Milvus.from_documents(
        documents       = docs,
        embedding       = embeddings,
        collection_name = collection_name,
        connection_args = {"host": milvus_host, "port": milvus_port},
        drop_old        = True
    )
    print(f"✅ Ingested into Milvus collection '{collection_name}'.")

    # 6) Optionally save the summaries for record
    out_path = "papers_summaries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump([
            {"conference": d.metadata["conference"],
             "year":       d.metadata["year"],
             "filename":   d.metadata["filename"],
             "summary":    d.page_content}
            for d in raw_docs
        ], f, indent=2, ensure_ascii=False)
    print(f"✅ Saved summaries to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Walk conference/year PDFs, summarize, and ingest into Milvus"
    )
    parser.add_argument("root_dir", help="Root folder containing conference/year PDFs")
    parser.add_argument("--host", "-H", default=os.getenv("MILVUS_HOST", "localhost"),
                        help="Milvus host")
    parser.add_argument("--port", "-P", default=os.getenv("MILVUS_PORT", "19530"),
                        help="Milvus port")
    parser.add_argument("--collection", "-c",
                        default=os.getenv("MILVUS_COLLECTION_NAME", "papers_summary"),
                        help="Milvus collection name")
    parser.add_argument("--api_key", "-k", default=os.getenv("OPENAI_API_KEY"),
                        help="OpenAI API key")
    parser.add_argument("--model", "-m", default="gpt-4o-mini",
                        help="OpenAI model for summarization")
    parser.add_argument("--chunk_size", type=int, default=1000,
                        help="Characters per chunk")
    parser.add_argument("--chunk_overlap", type=int, default=100,
                        help="Overlap between chunks")

    args = parser.parse_args()
    if not args.api_key:
        parser.error("OpenAI API key must be provided via --api_key or OPENAI_API_KEY env var")

    initialize_and_ingest(
        root_dir        = args.root_dir,
        milvus_host     = args.host,
        milvus_port     = args.port,
        collection_name = args.collection,
        openai_api_key  = args.api_key,
        model_name      = args.model,
        chunk_size      = args.chunk_size,
        chunk_overlap   = args.chunk_overlap
    )
