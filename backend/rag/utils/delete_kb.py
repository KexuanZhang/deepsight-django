#!/usr/bin/env python3
import os
import argparse
from pymilvus import connections, utility

def get_collection_name(user_id: int) -> str:
    """
    Build the per-user collection name, matching your add_user_files logic.
    """
    base = os.getenv("MILVUS_LOCAL_COLLECTION", "user_files")
    return f"{base}_{user_id}"

def main():
    parser = argparse.ArgumentParser(
        description="Drop a user's Milvus collection (and all their vectors)."
    )
    parser.add_argument(
        "--user-id", "-u",
        required=True,
        type=int,
        help="The numeric user ID whose collection should be dropped."
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
    coll_name = get_collection_name(args.user_id)
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
