"""Simplified embedding providers - single file implementation"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

from grag.core.config import settings

logger = logging.getLogger(__name__)


# Base interface (simplified, no ABC overhead)
class EmbeddingProvider:
    """Simple base for embedding providers"""

    @property
    def name(self) -> str:
        """Get provider name"""
        return self.__class__.__name__.lower().replace("provider", "")

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "dimension": self.dimension,
            "available": self.is_available()
        }

    def get_provider_info(self) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        return self.get_info()


# Provider implementations
class SentenceTransformerProvider(EmbeddingProvider):
    """SentenceTransformer embedding provider"""

    def __init__(self):
        self.model_name = settings.embedding_model
        self._model = None
        self._dimension = settings.embedding_dimension

        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading SentenceTransformer: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer: {e}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self._model:
            raise Exception("SentenceTransformer model not loaded")

        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def is_available(self) -> bool:
        return self._model is not None


class OpenAIProvider(EmbeddingProvider):
    """OpenAI embedding provider"""

    def __init__(self):
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url or "https://api.openai.com/v1"
        self.model_name = settings.embedding_model

        # OpenAI embedding dimensions
        self._dimension = 1536 if "3-small" in self.model_name else 3072

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

            response = client.embeddings.create(
                input=texts,
                model=self.model_name
            )

            return [emb.embedding for emb in response.data]

        except ImportError:
            raise Exception("OpenAI provider requires 'openai' package")
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)


class CohereProvider(EmbeddingProvider):
    """Cohere embedding provider"""

    def __init__(self):
        self.api_key = settings.embedding_api_key
        self.model_name = settings.embedding_model
        self._dimension = 1024  # Cohere typical dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            import cohere
            client = cohere.Client(self.api_key)

            response = client.embed(
                texts=texts,
                model=self.model_name,
                input_type="search_document"
            )

            return response.embeddings

        except ImportError:
            raise Exception("Cohere provider requires 'cohere' package")
        except Exception as e:
            logger.error(f"Cohere embedding failed: {e}")
            raise

    def is_available(self) -> bool:
        return bool(self.api_key)


# Simplified factory
def create_embedding_provider(provider_name: Optional[str] = None) -> EmbeddingProvider:
    """Create embedding provider based on configuration

    Args:
        provider_name: Override default provider from settings

    Returns:
        Configured embedding provider

    Raises:
        ValueError: For unsupported provider
    """
    provider_name = provider_name or settings.embedding_provider
    provider_name = provider_name.lower().strip()

    logger.info(f"Creating embedding provider: {provider_name}")

    try:
        if provider_name in ["sentence_transformers", "local"]:
            return SentenceTransformerProvider()

        elif provider_name == "openai":
            return OpenAIProvider()

        elif provider_name == "cohere":
            return CohereProvider()

        else:
            supported = ["sentence_transformers", "openai", "cohere"]
            raise ValueError(f"Unsupported provider '{provider_name}'. Supported: {supported}")

    except Exception as e:
        logger.error(f"Failed to create provider '{provider_name}': {e}")
        raise


def list_available_providers() -> List[str]:
    """List all available embedding providers"""
    return ["sentence_transformers", "openai", "cohere"]


def get_provider_info(provider_name: str) -> Dict[str, Any]:
    """Get information about a provider without creating it"""
    info = {
        "sentence_transformers": {
            "api_key_required": False,
            "packages": ["sentence-transformers"],
            "cost": "Free (local)",
            "dimension": 384,
            "description": "High-quality local embeddings, no API costs"
        },
        "openai": {
            "api_key_required": True,
            "packages": ["openai"],
            "cost": "Pay per token",
            "dimension": "1536-3072",
            "description": "Premium cloud embeddings with latest models"
        },
        "cohere": {
            "api_key_required": True,
            "packages": ["cohere"],
            "cost": "Pay per token",
            "dimension": 1024,
            "description": "Specialized embeddings for enterprise use"
        }
    }

    return info.get(provider_name.lower(), {})
