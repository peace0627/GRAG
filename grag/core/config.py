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

    # Ollama (local VLM service - RECOMMENDED for qwen3-vl and other vision models)
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str = "ollama"
    ollama_model: str = "qwen3-vl:235b-cloud"  # Uses qwen3-vl model via Ollama

    # Note: Qwen2VL cloud service has been removed - using local Ollama instead
    # for better privacy, cost control, and performance
    qwen2vl_api_key: str = ""  # Kept for backward compatibility with app.py checks

    # === Application Configuration ===
    debug: bool = True
    knowledge_area_id: str = "default_area"
    log_level: str = "INFO"

    # === Processing Configuration ===
    # Text chunking parameters
    chunk_size: int = 512
    chunk_overlap: int = 50
    include_visual_chunks: bool = True

    # Embedding service configuration
    embedding_provider: str = "sentence_transformers"  # sentence_transformers, openai, cohere, huggingface
    embedding_api_key: str = ""                        # API key for cloud providers
    embedding_base_url: str = ""                       # Custom API endpoint
    embedding_model: str = "all-MiniLM-L6-v2"           # Model identifier
    embedding_dimension: int = 384                      # Expected embedding dimension

    # Knowledge extraction parameters
    extract_entities: bool = True
    extract_relations: bool = True
    extract_events: bool = True
    min_entity_confidence: float = 0.5

    # === File Upload Configuration ===
    upload_base_path: str = "./uploads"
    max_file_size_mb: int = 50

    # === Neo4j Browser Configuration ===
    # For GUI database visualization (Neo4j Browser iframe)
    neo4j_browser_url: str = "http://localhost:7474"
    neo4j_browser_username: str = "neo4j"  # Used for Browser access
    neo4j_browser_password: str = "password123"  # Used for Browser access

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Alias for backward compatibility
get_config = get_settings

# Global settings instance
settings = get_settings()
