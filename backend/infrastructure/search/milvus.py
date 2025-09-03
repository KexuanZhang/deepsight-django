"""
Milvus search implementation following the search interface.
"""

import logging
from typing import Dict, List, Optional
from django.conf import settings
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
from pymilvus.exceptions import MilvusException
from .base import SearchInterface


class MilvusSearch(SearchInterface):
    """
    Milvus vector search backend implementation.
    
    Implements the SearchInterface for Milvus vector database,
    providing efficient similarity search capabilities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._connected = False
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize connection to Milvus server."""
        try:
            milvus_settings = getattr(settings, 'MILVUS_SETTINGS', {})
            
            host = milvus_settings.get('HOST', 'localhost')
            port = milvus_settings.get('PORT', '19530')
            
            connections.connect(
                alias="default",
                host=host,
                port=port
            )
            
            self._connected = True
            self.logger.info(f"Connected to Milvus at {host}:{port}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Milvus: {e}")
            self._connected = False
            raise
    
    def _ensure_connected(self):
        """Ensure connection to Milvus is active."""
        if not self._connected:
            self._initialize_connection()
    
    def create_collection(self, collection_name: str, dimension: int, 
                         description: str = "") -> bool:
        """Create a new Milvus collection for vector storage."""
        try:
            self._ensure_connected()
            
            # Check if collection already exists
            if self.collection_exists(collection_name):
                self.logger.info(f"Collection {collection_name} already exists")
                return True
            
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535)
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description=description or f"Collection {collection_name}"
            )
            
            # Create collection
            collection = Collection(
                name=collection_name,
                schema=schema,
                using='default',
                shards_num=1
            )
            
            # Create index for vector field
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            
            collection.create_index(
                field_name="vector",
                index_params=index_params
            )
            
            self.logger.info(f"Created Milvus collection: {collection_name}")
            return True
            
        except MilvusException as e:
            self.logger.error(f"Failed to create collection {collection_name}: {e}")
            return False
    
    def insert_vectors(self, collection_name: str, vectors: List[List[float]], 
                      ids: List[str], metadata: List[Dict] = None) -> bool:
        """Insert vectors into a Milvus collection."""
        try:
            self._ensure_connected()
            
            collection = Collection(collection_name)
            
            # Prepare metadata as JSON strings
            metadata_strings = []
            if metadata:
                import json
                metadata_strings = [json.dumps(meta) for meta in metadata]
            else:
                metadata_strings = ["{}"] * len(vectors)
            
            # Prepare data for insertion
            data = [
                ids,
                vectors,
                metadata_strings
            ]
            
            # Insert data
            collection.insert(data)
            collection.flush()
            
            self.logger.info(f"Inserted {len(vectors)} vectors into {collection_name}")
            return True
            
        except MilvusException as e:
            self.logger.error(f"Failed to insert vectors into {collection_name}: {e}")
            return False
    
    def search_vectors(self, collection_name: str, query_vector: List[float], 
                      top_k: int = 10, filters: Dict = None) -> List[Dict]:
        """Search for similar vectors in Milvus collection."""
        try:
            self._ensure_connected()
            
            collection = Collection(collection_name)
            collection.load()
            
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 16}
            }
            
            # Perform search
            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["id", "metadata"]
            )
            
            # Process results
            search_results = []
            for hits in results:
                for hit in hits:
                    import json
                    try:
                        metadata = json.loads(hit.entity.get("metadata", "{}"))
                    except json.JSONDecodeError:
                        metadata = {}
                    
                    search_results.append({
                        "id": hit.entity.get("id"),
                        "score": float(hit.score),
                        "metadata": metadata
                    })
            
            self.logger.debug(f"Found {len(search_results)} similar vectors in {collection_name}")
            return search_results
            
        except MilvusException as e:
            self.logger.error(f"Failed to search vectors in {collection_name}: {e}")
            return []
    
    def delete_vectors(self, collection_name: str, ids: List[str]) -> bool:
        """Delete vectors by IDs from Milvus collection."""
        try:
            self._ensure_connected()
            
            collection = Collection(collection_name)
            
            # Build expression for deletion
            id_list_str = "', '".join(ids)
            expr = f"id in ['{id_list_str}']"
            
            collection.delete(expr)
            collection.flush()
            
            self.logger.info(f"Deleted {len(ids)} vectors from {collection_name}")
            return True
            
        except MilvusException as e:
            self.logger.error(f"Failed to delete vectors from {collection_name}: {e}")
            return False
    
    def update_vector(self, collection_name: str, vector_id: str, 
                     vector: List[float], metadata: Dict = None) -> bool:
        """Update an existing vector (delete + insert)."""
        try:
            # Milvus doesn't support direct updates, so we delete and re-insert
            if self.delete_vectors(collection_name, [vector_id]):
                return self.insert_vectors(
                    collection_name, 
                    [vector], 
                    [vector_id], 
                    [metadata] if metadata else None
                )
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update vector {vector_id}: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get information about a Milvus collection."""
        try:
            self._ensure_connected()
            
            if not self.collection_exists(collection_name):
                return None
            
            collection = Collection(collection_name)
            
            info = {
                "name": collection_name,
                "description": collection.description,
                "num_entities": collection.num_entities,
                "schema": {
                    "fields": [
                        {
                            "name": field.name,
                            "type": str(field.dtype),
                            "params": field.params
                        }
                        for field in collection.schema.fields
                    ]
                }
            }
            
            return info
            
        except MilvusException as e:
            self.logger.error(f"Failed to get info for collection {collection_name}: {e}")
            return None
    
    def list_collections(self) -> List[str]:
        """List all Milvus collections."""
        try:
            self._ensure_connected()
            
            from pymilvus import utility
            collections = utility.list_collections()
            
            return collections
            
        except MilvusException as e:
            self.logger.error(f"Failed to list collections: {e}")
            return []
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a Milvus collection exists."""
        try:
            self._ensure_connected()
            
            from pymilvus import utility
            return utility.has_collection(collection_name)
            
        except MilvusException as e:
            self.logger.error(f"Failed to check collection existence {collection_name}: {e}")
            return False