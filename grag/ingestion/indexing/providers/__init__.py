"""Simplified embedding providers - single file implementation"""

from .embedding_providers import (
    EmbeddingProvider,
    SentenceTransformerProvider,
    OpenAIProvider,
    CohereProvider,
    create_embedding_provider,
    list_available_providers,
    get_provider_info
)

__all__ = [
    "EmbeddingProvider",
    "SentenceTransformerProvider",
    "OpenAIProvider",
    "CohereProvider",
    "create_embedding_provider",
    "list_available_providers",
    "get_provider_info"
]
