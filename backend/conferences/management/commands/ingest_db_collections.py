import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from dotenv import load_dotenv
from pymilvus import connections, utility, Collection
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_milvus import Milvus
from conferences.models import Publication

load_dotenv()


def log(message: str):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {message}")


def parse_specs(specs_str: str) -> list[tuple[str, QuerySet]]:
    """
    Parse a comma-separated string like 'global,CVPR:2021' into collection names and querysets.
    """
    specs = []
    for part in specs_str.split(','):
        part = part.strip()
        if not part:
            continue
        if part.lower() == 'global':
            specs.append(('global', Publication.objects.all()))
        elif ':' in part:
            venue, year = part.split(':', 1)
            col_name = f"{venue.lower()}_{year}"
            qs = Publication.objects.filter(
                instance__venue__name__iexact=venue,
                instance__year=int(year)
            )
            specs.append((col_name, qs))
        else:
            raise ValueError(f"Invalid spec '{part}'. Use 'global' or 'Venue:Year'")
    return specs


def ingest_collection(name: str, queryset: QuerySet, host: str, port: str,
                      api_key: str, chunk_size: int, chunk_overlap: int, drop_old: bool):
    """
    Convert queryset to Documents and ingest into Milvus collection.
    """
    docs = []
    total = queryset.count()
    log(f"[{name}] Found {total} publications")

    for idx, pub in enumerate(queryset, 1):
        log(f"[{name}] {idx}/{total}: '{pub.title[:40]}...'")
        abstract = pub.abstract or ''
        if not abstract.strip():
            log(f"[{name}] ⚠️ Skipping empty abstract (ID: {pub.pk})")
            continue
        metadata = {
            'id': pub.pk,
            'title': pub.title,
            'conference': pub.instance.venue.name,
            'year': pub.instance.year,
        }
        docs.append(Document(page_content=abstract, metadata=metadata))

    if not docs:
        log(f"[{name}] ⚠️ No valid documents to ingest.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(docs)
    log(f"[{name}] Split into {len(chunks)} chunks")

    connections.connect(host=host, port=port)
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)
    Milvus.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=name,
        connection_args={"host": host, "port": port},
        drop_old=drop_old
    )
    coll = Collection(name)
    coll.flush()
    coll.load()
    log(f"[{name}] ✅ Ingested {len(chunks)} chunks into Milvus")


class Command(BaseCommand):
    help = "Embed publication abstracts into Milvus collections, one per venue-year or global."

    def add_arguments(self, parser):
        parser.add_argument(
            '--collections', '-c', required=True,
            help="Comma-separated list like 'global' or 'CVPR:2022,NeurIPS:2023'"
        )
        parser.add_argument('--host', default=os.getenv("MILVUS_HOST", "localhost"))
        parser.add_argument('--port', default=os.getenv("MILVUS_PORT", "19530"))
        parser.add_argument('--drop-old', action='store_true',
                            help="Drop old collection before ingesting")
        parser.add_argument('--chunk-size', type=int, default=1000,
                            help="Characters per chunk")
        parser.add_argument('--chunk-overlap', type=int, default=100,
                            help="Overlap between chunks")

    def handle(self, *args, **options):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.stderr.write("❌ Missing OPENAI_API_KEY in environment or .env")
            return

        try:
            specs = parse_specs(options['collections'])
        except ValueError as e:
            self.stderr.write(f"❌ {str(e)}")
            return

        for name, qs in specs:
            ingest_collection(
                name=name,
                queryset=qs,
                host=options['host'],
                port=options['port'],
                api_key=api_key,
                chunk_size=options['chunk_size'],
                chunk_overlap=options['chunk_overlap'],
                drop_old=options['drop_old'],
            )
