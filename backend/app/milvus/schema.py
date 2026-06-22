from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility
from app.config import settings
import structlog

logger = structlog.get_logger()

COLLECTION_NAME = "rag_chunks"

def get_collection() -> Collection:
    """Return the pymilvus Collection instance."""
    return Collection(COLLECTION_NAME)

def init_milvus_collection() -> Collection:
    """
    Check if the collection exists, otherwise create it.
    Define the fields, build HNSW index, and load it into memory.
    """
    # Ensure there is a default connection
    from app.milvus.client import connect_milvus
    connect_milvus()

    EXPECTED_DIM = 384

    if utility.has_collection(COLLECTION_NAME):
        collection = Collection(COLLECTION_NAME)
        # Check if the existing collection's embedding dimension matches
        existing_dim = None
        for field in collection.schema.fields:
            if field.name == "embedding":
                existing_dim = field.params.get("dim")
        
        if existing_dim == EXPECTED_DIM:
            logger.info("milvus_collection_exists", collection=COLLECTION_NAME, dim=existing_dim)
            collection.load()
            return collection
        else:
            logger.warning(
                "milvus_collection_dimension_mismatch_dropping", 
                collection=COLLECTION_NAME, 
                existing_dim=existing_dim, 
                expected_dim=EXPECTED_DIM
            )
            # Drop existing collection to recreate with correct dimension
            utility.drop_collection(COLLECTION_NAME)

    # Fields Definition
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),       # Postgres document UUID
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),      # Scoped retrieval (owner)
        FieldSchema(name="chunk_index", dtype=DataType.INT32),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=8192),       # Chunk text
        FieldSchema(name="source_page", dtype=DataType.INT32),
        FieldSchema(name="filename", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EXPECTED_DIM) # bge-small-en-v1.5 dim (384)
    ]

    schema = CollectionSchema(fields, description="Collection for RAG QA System Chunks")
    
    logger.info("creating_milvus_collection", collection=COLLECTION_NAME)
    collection = Collection(name=COLLECTION_NAME, schema=schema)

    # Index Configuration
    index_params = {
        "field_name": "embedding",
        "metric_type": "COSINE",
        "index_type": "HNSW",
        "params": {"M": 16, "efConstruction": 256},
    }
    
    logger.info("creating_milvus_index", collection=COLLECTION_NAME, index_params=index_params)
    collection.create_index(field_name="embedding", index_params=index_params)

    # Load collection into memory
    collection.load()
    logger.info("milvus_collection_loaded_after_creation", collection=COLLECTION_NAME)
    return collection
