import math
import asyncio
from app.config import settings
import structlog
from sentence_transformers import SentenceTransformer
import torch

logger = structlog.get_logger()

_model = None

def get_embedding_model() -> SentenceTransformer:
    """Lazily load the SentenceTransformer model on the appropriate device."""
    global _model
    if _model is None:
        logger.info("loading_sentence_transformer_model", model=settings.EMBEDDING_MODEL_NAME)
        # Choose GPU if available, else fallback to CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("sentence_transformer_device_selected", device=device)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device=device)
    return _model

def normalize_vector(v: list[float]) -> list[float]:
    """L2 normalize a list of floats."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]

async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch-embed texts locally via sentence-transformers.
    Normalize vectors before returning.
    Runs in a background thread to prevent blocking the event loop.
    Return list of float vectors.
    """
    if not texts:
        return []

    if settings.MOCK_VLLM:
        logger.info("generating_mock_embeddings", count=len(texts))
        mock_embeddings = []
        for text in texts:
            # Generate deterministic mock 384-dimensional embedding
            h = hash(text)
            vec = []
            for idx in range(384):
                val = ((h + idx * 37) % 200 - 100) / 100.0
                vec.append(val)
            mock_embeddings.append(normalize_vector(vec))
        return mock_embeddings

    try:
        model = get_embedding_model()
        logger.info("generating_local_embeddings", count=len(texts), model=settings.EMBEDDING_MODEL_NAME)
        
        # Run synchronous model inference in a thread pool to avoid blocking FastAPI event loop
        embeddings = await asyncio.to_thread(
            model.encode, 
            texts, 
            batch_size=32, 
            show_progress_bar=False
        )
        
        # Normalize and return
        return [normalize_vector(e.tolist()) for e in embeddings]

    except Exception as e:
        logger.error("local_embedding_service_exception", error=str(e))
        raise e
