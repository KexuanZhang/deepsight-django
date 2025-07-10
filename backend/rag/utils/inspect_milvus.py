#!/usr/bin/env python
import os
from pymilvus import connections, utility, Collection

# 1) Connect to your Milvus server (use the same host/port you’ve been)
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)

# 2) List all collections
collections = utility.list_collections()
print("Collections in Milvus:")
if not collections:
    print("  (none found)")
else:
    for name in collections:
        print(f"\n▶ Collection: {name}")
        coll = Collection(name)

        # 2a) Inspect schema fields
        print("  Schema:")
        for fld in coll.schema.fields:
            print(f"    • {fld.name} (type={fld.dtype.name}, primary={fld.is_primary})")

        # 2b) How many vectors are stored?
        print(f"  Num entities: {coll.num_entities}")

        # 2c) List any indexes on each field
        idxs = utility.list_indexes(name)
        if idxs:
            print("  Indexes:")
            for idx in idxs:
                print(f"    • {idx}")
        else:
            print("  (no indexes)")

# 3) Disconnect
connections.disconnect("default")
