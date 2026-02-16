"""Configuration management using environment variables."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Chat (LLM): Groq or open ai 
    groq_api_key: Optional[str] = None  #for Groq chat
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "groq/compound"
    openai_api_key: Optional[str] = None  # For openai only (chat + embeddings)
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4"

    # Embeddings "jina" (default) or "openai" (if there is one or reviewers use thier own open ai keys)
    embedding_provider: str = "jina"
    openai_embedding_api_key: Optional[str] = None  # When openai: uses this or openai_api_key
    openai_embedding_model: str = "text-embedding-3-small"
    jina_embedding_api_key: Optional[str] = None
    jina_embedding_model: str = "jina-embeddings-v3"

    # Vector DB and KB paths
    chroma_db_path: str = "./chroma_db"
    kb_path: str = "./data/kb"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
