"""Configuration management using Pydantic Settings and environment variables"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # === Database Configuration ===
    # Neo4j Graph Database
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password123"

    # Supabase Vector Database
    supabase_url: str = ""
    supabase_key: str = ""

    # === AI Model Configuration ===
    # OpenAI (for completions)
    openai_api_key: str = ""

    # Qwen2VL (for multimodal analysis)
    qwen2vl_base_url: str = "https://api.qwen2vl.com"
    qwen2vl_api_key: str = ""

    # === Application Configuration ===
    debug: bool = True
    knowledge_area_id: str = "default_area"
    log_level: str = "INFO"

    # === Processing Configuration ===
    # Text chunking parameters
    chunk_size: int = 512
    chunk_overlap: int = 50
    include_visual_chunks: bool = True

    # Embedding model parameters
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Knowledge extraction parameters
    extract_entities: bool = True
    extract_relations: bool = True
    extract_events: bool = True
    min_entity_confidence: float = 0.5

    # === File Upload Configuration ===
    upload_base_path: str = "./uploads"
    max_file_size_mb: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
