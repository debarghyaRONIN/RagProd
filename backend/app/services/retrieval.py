from typing import List
from app.config import settings
from app.milvus.schema import COLLECTION_NAME, get_collection, get_user_partition_name
from app.services.embedding import embed_texts
from app.schemas.chat import RetrievedChunk
import structlog

logger = structlog.get_logger()

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate the Jaccard similarity score between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

async def retrieve_chunks(
    query: str,
    user_id: str,
    top_k: int = 5,
    doc_ids: List[str] | None = None,
) -> List[RetrievedChunk]:
    """
    1. Embed the query with embedding service.
    2. Build Milvus filter expression.
    3. Search Milvus collection with top_k, return text + metadata.
    4. Deduplicate overlapping chunks (Jaccard similarity > 0.8 -> drop lower score).
    5. Return sorted by score descending.
    """
    if not query:
        return []

    # 1. Embed query
    query_embeddings = await embed_texts([query])
    if not query_embeddings:
        logger.error("retrieval_failed_no_query_embedding")
        return []
    query_emb = query_embeddings[0]

    # 2. Build Milvus filter expression
    # user_id scoping is mandatory for security
    expr = f'user_id == "{user_id}"'
    if doc_ids:
        # doc_ids is list of strings (UUIDs)
        formatted_ids = ", ".join(f'"{d_id}"' for d_id in doc_ids)
        expr += f' && doc_id in [{formatted_ids}]'

    # 3. Perform Milvus search
    try:
        collection = get_collection()
        partition_name = get_user_partition_name(user_id)
        
        # If partition doesn't exist, user has uploaded no docs
        if not collection.has_partition(partition_name):
            logger.info("user_has_no_milvus_partition_returning_empty", user_id=user_id, partition_name=partition_name)
            return []
            
        search_params = {"metric_type": "COSINE", "params": {"ef": 128}}
        
        logger.info("searching_milvus", expr=expr, partition_name=partition_name, top_k=top_k)
        results = collection.search(
            data=[query_emb],
            anns_field="embedding",
            param=search_params,
            limit=top_k * 2, # fetch a bit extra for deduplication overhead
            expr=expr,
            partition_names=[partition_name],
            output_fields=["doc_id", "user_id", "chunk_index", "text", "source_page", "filename"]
        )
    except Exception as e:
        logger.error("milvus_search_failed", error=str(e))
        return []

    if not results:
        return []

    # Parse results into RetrievedChunk objects
    chunks: List[RetrievedChunk] = []
    for hit in results[0]:
        chunks.append(
            RetrievedChunk(
                id=hit.id,
                doc_id=hit.entity.get("doc_id"),
                user_id=hit.entity.get("user_id"),
                chunk_index=hit.entity.get("chunk_index"),
                text=hit.entity.get("text"),
                source_page=hit.entity.get("source_page"),
                filename=hit.entity.get("filename"),
                score=hit.score
            )
        )

    # 4. Deduplicate overlapping chunks based on Jaccard Similarity > 0.8
    # Since they are retrieved sorted by score desc, we keep the first occurrences (highest score)
    deduplicated_chunks: List[RetrievedChunk] = []
    for chunk in chunks:
        is_duplicate = False
        for existing in deduplicated_chunks:
            similarity = calculate_jaccard_similarity(chunk.text, existing.text)
            if similarity > 0.8:
                is_duplicate = True
                logger.info(
                    "dropping_duplicate_chunk",
                    chunk_id=chunk.id,
                    existing_id=existing.id,
                    similarity=similarity
                )
                break
        if not is_duplicate:
            deduplicated_chunks.append(chunk)

    # 5. Trim to top_k and return sorted (already sorted by score desc)
    final_chunks = deduplicated_chunks[:top_k]
    logger.info("retrieved_chunks_summary", count=len(final_chunks), query=query)
    return final_chunks
