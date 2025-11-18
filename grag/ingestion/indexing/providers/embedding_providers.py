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


class CLIPProvider(EmbeddingProvider):
    """CLIP multimodal embedding provider (OpenCLIP)"""

    def __init__(self):
        from open_clip import create_model_and_transforms, get_tokenizer
        import torch

        # Use ViT-B/32 as a good balance of quality and speed
        self.model_name = "ViT-B-32"
        self.pretrained = "laion2b_s34b_b79k"

        try:
            self.model, _, self.preprocess = create_model_and_transforms(
                self.model_name, pretrained=self.pretrained
            )
            self.tokenizer = get_tokenizer(self.model_name)

            # Move to GPU if available, otherwise CPU
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = self.model.to(self.device)
            self.model.eval()

            # CLIP uses 512-dimensional embeddings
            self._dimension = 512

            logger.info(f"CLIP provider initialized on {self.device}")

        except Exception as e:
            logger.error(f"Failed to initialize CLIP model: {e}")
            self.model = None

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Create text embeddings using CLIP text encoder"""
        if not self.model:
            raise Exception("CLIP model not initialized")

        try:
            import torch
            import torch.nn.functional as F

            # Tokenize texts
            text_tokens = self.tokenizer(texts).to(self.device)

            with torch.no_grad():
                # Get text features
                text_features = self.model.encode_text(text_tokens)

                # Normalize features
                text_features = F.normalize(text_features, dim=-1)

            return text_features.cpu().numpy().tolist()

        except Exception as e:
            logger.error(f"CLIP text embedding failed: {e}")
            raise

    def embed_images(self, image_paths: List[str]) -> List[List[float]]:
        """Create image embeddings using CLIP vision encoder"""
        if not self.model:
            raise Exception("CLIP model not initialized")

        try:
            import torch
            import torch.nn.functional as F
            from PIL import Image

            images = []
            for path in image_paths:
                image = Image.open(path).convert("RGB")
                image = self.preprocess(image).unsqueeze(0).to(self.device)
                images.append(image)

            # Stack images into batch
            image_batch = torch.cat(images)

            with torch.no_grad():
                # Get image features
                image_features = self.model.encode_image(image_batch)

                # Normalize features
                image_features = F.normalize(image_features, dim=-1)

            return image_features.cpu().numpy().tolist()

        except Exception as e:
            logger.error(f"CLIP image embedding failed: {e}")
            raise

    def embed_image_regions(self, image_path: str, regions: Optional[List[Dict]] = None) -> List[List[float]]:
        """Create embeddings for image regions (simplified - uses full image)"""
        if not self.model:
            raise Exception("CLIP model not initialized")

        # For now, return full image embedding for each region
        # TODO: Implement actual region cropping and embedding
        embeddings = self.embed_images([image_path])

        if regions:
            # Repeat the same embedding for all regions (temporary)
            return embeddings * len(regions)
        else:
            return embeddings

    def is_available(self) -> bool:
        return self.model is not None


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

        elif provider_name == "clip":
            return CLIPProvider()

        else:
            supported = ["sentence_transformers", "openai", "cohere", "clip"]
            raise ValueError(f"Unsupported provider '{provider_name}'. Supported: {supported}")

    except Exception as e:
        logger.error(f"Failed to create provider '{provider_name}': {e}")
        raise


def list_available_providers() -> List[str]:
    """List all available embedding providers"""
    return ["sentence_transformers", "openai", "cohere", "clip"]


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
        },
        "clip": {
            "api_key_required": False,
            "packages": ["open_clip_torch", "torch", "torchvision"],
            "cost": "Free (local)",
            "dimension": 512,
            "description": "Multimodal embeddings for text and images in shared space"
        }
    }

    return info.get(provider_name.lower(), {})
