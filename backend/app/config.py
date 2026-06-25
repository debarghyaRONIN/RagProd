import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG QA System"
    DEBUG: bool = False
    SECRET_KEY: str                        # for JWT
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    MOCK_VLLM: bool = False # Mock local vLLM if no GPU available

    # PostgreSQL
    DATABASE_URL: str                      # asyncpg DSN (e.g., postgresql+asyncpg://...)

    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    LLM_MODEL_NAME: str = "Qwen/Qwen2.5-3B-Instruct"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    HF_TOKEN: str = "hf_placeholder"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # RAG config
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 5
    MAX_CONTEXT_TOKENS: int = 3000
    STREAM_TIMEOUT: int = 120

    # Configuration for Pydantic Settings to load from env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
