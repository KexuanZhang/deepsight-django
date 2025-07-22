#!/usr/bin/env python3
import os
import argparse
from pymilvus import connections, utility

def get_collection_name(user_id: str) -> str:
    """
    Build the per-user collection name, matching your add_user_files logic.
    Now expects a full collection name like 'user_files_62fc70fd44b7481f812eb5f6db6f975b'.
    """
    return user_id  # user_id is now the full collection name

def main():
    parser = argparse.ArgumentParser(
        description="Drop a user's Milvus collection (and all their vectors)."
    )
    parser.add_argument(
        "--collection", "-c",
        required=True,
        type=str,
        help="The full collection name to drop (e.g. user_files_62fc70fd44b7481f812eb5f6db6f975b)"
    )
    parser.add_argument(
        "--host", "-H",
        default=os.getenv("MILVUS_HOST", "localhost"),
        help="Milvus host (default from MILVUS_HOST)"
    )
    parser.add_argument(
        "--port", "-P",
        default=os.getenv("MILVUS_PORT", "19530"),
        help="Milvus port (default from MILVUS_PORT)"
    )
    args = parser.parse_args()

    # 1) Connect to Milvus
    connections.connect(alias="default", host=args.host, port=args.port)
    print(f"Connected to Milvus at {args.host}:{args.port}")

    # 2) Determine the collection name
    coll_name = get_collection_name(args.collection)
    print("Target collection:", coll_name)

    # 3) Check if it exists
    existing = utility.list_collections()
    if coll_name not in existing:
        print(f"❌ Collection '{coll_name}' does not exist. Nothing to delete.")
        return

    # 4) Drop the collection
    print(f"🗑  Dropping collection '{coll_name}' …")
    utility.drop_collection(coll_name)
    print("✅ Dropped successfully.")

    # 5) Cleanup
    connections.disconnect("default")

if __name__ == "__main__":
    main()
