# test_milvus.py
from pymilvus import connections, utility

HOST = "127.0.0.1"   # or “localhost”
PORT = "19530"

print(f"→ Testing connection to Milvus at {HOST}:{PORT}")
try:
    # open a connection
    connections.connect(alias="default", host=HOST, port=PORT, timeout=3)
    # list collections to confirm it’s talking to the right server
    cols = utility.list_collections()
    print("✅ Connected! Collections in this Milvus:", cols)
except Exception as e:
    print("❌ Failed to connect:", e)
