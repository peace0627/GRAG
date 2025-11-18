"""Unified embedding service for text and multimodal content"""

import logging
from typing import List, Dict, Any, Optional

from .providers.embedding_providers import create_embedding_provider
from grag.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified embedding service supporting multiple embedding providers

    This service provides a unified interface to different embedding providers
    (SentenceTransformer, OpenAI, Cohere, etc.) based on configuration.
    """

    def __init__(self):
        """Initialize embedding service using environment configuration"""
        # Create provider using factory based on settings
        try:
            self.provider = create_embedding_provider()
            logger.info(f"Initialized embedding service with provider: {self.provider.name}")

            # Get dimension from provider
            self.model_name = settings.embedding_model
            self.dimension = self.provider.dimension

        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            logger.warning("Falling back to development fallback mode")
            self.provider = None
            self.model_name = settings.embedding_model
            self.dimension = settings.embedding_dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If embedding fails
        """
        if not texts:
            return []

        if not self.provider:
            return self._development_embeddings(texts)

        try:
            return self.provider.embed_texts(texts)
        except Exception as e:
            logger.error(f"Embedding service failed: {e}")
            logger.warning("Falling back to development mode")
            return self._development_embeddings(texts)

    def embed_single_text(self, text: str) -> List[float]:
        """Embed a single text string

        Args:
            text: Text string to embed

        Returns:
            Embedding vector
        """
        result = self.embed_texts([text])
        return result[0] if result else [0.0] * self.dimension

    def embed_chunks(self,
                    chunks: List[Dict[str, Any]],
                    include_visual: bool = True) -> List[Dict[str, Any]]:
        """Embed document chunks and return enriched chunks with vector IDs

        Supports multimodal embedding when using CLIP provider.

        Args:
            chunks: List of chunk dictionaries
            include_visual: Whether to process visual chunks differently

        Returns:
            Chunks with 'vector_id' and 'embedding' added
        """
        if not chunks:
            return chunks

        try:
            # Extract texts for batch embedding
            texts = []
            chunk_indices = []

            for i, chunk in enumerate(chunks):
                chunk_type = chunk.get("metadata", {}).get("processing_method", "text")

                if include_visual or chunk_type != "vlm_visual":
                    # Filter out visual chunks if not wanted, otherwise process all
                    texts.append(chunk["content"])
                    chunk_indices.append(i)

            if not texts:
                logger.warning("No texts to embed after filtering")
                return chunks

            # Batch embed
            embeddings = self.embed_texts(texts)

            # Add vector IDs and embeddings back to chunks
            for idx, embed_idx in enumerate(chunk_indices):
                chunk = chunks[embed_idx]

                # Generate deterministic vector ID
                vector_id = self._generate_vector_id(chunk["chunk_id"])

                # Add to chunk
                chunk["vector_id"] = vector_id
                chunk["embedding"] = embeddings[idx]
                chunk["embedding_model"] = self.model_name
                chunk["embedding_dimension"] = self.dimension
                chunk["embedding_provider"] = self.provider.name if self.provider else "fallback"

            logger.info(f"Successfully embedded {len(chunk_indices)} chunks using {self.provider.name if self.provider else 'fallback'}")
            return chunks

        except Exception as e:
            logger.error(f"Chunk embedding failed: {e}")
            raise

    def embed_multimodal_chunks(self,
                              chunks: List[Dict[str, Any]],
                              visual_facts: Optional[List[Dict[str, Any]]] = None,
                              image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Embed chunks with multimodal support (text + visual)

        Uses CLIP for multimodal embedding when available, falls back to text-only.

        Args:
            chunks: List of chunk dictionaries
            visual_facts: Optional list of visual facts from VLM
            image_paths: Optional list of image paths for CLIP embedding

        Returns:
            Chunks with multimodal embeddings added
        """
        if not chunks:
            return chunks

        try:
            # Check if we have CLIP provider for multimodal embedding
            is_clip_available = (self.provider and
                               hasattr(self.provider, 'name') and
                               self.provider.name == 'clip' and
                               self.provider.is_available())

            if is_clip_available and (visual_facts or image_paths):
                logger.info("Using CLIP for multimodal embedding")
                return self._embed_with_clip_multimodal(chunks, visual_facts, image_paths)
            else:
                logger.info("Falling back to text-only embedding")
                return self.embed_chunks(chunks, include_visual=True)

        except Exception as e:
            logger.error(f"Multimodal embedding failed: {e}")
            logger.warning("Falling back to text-only embedding")
            return self.embed_chunks(chunks, include_visual=True)

    def _embed_with_clip_multimodal(self,
                                  chunks: List[Dict[str, Any]],
                                  visual_facts: Optional[List[Dict[str, Any]]] = None,
                                  image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Use CLIP for multimodal embedding"""
        texts_to_embed = []
        visual_contexts = []
        chunk_indices = []

        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get("content", "")
            chunk_visual_facts = visual_facts or []

            # Create enriched text with visual context
            enriched_text = self._enrich_text_with_visual_context(chunk_text, chunk_visual_facts)
            texts_to_embed.append(enriched_text)
            visual_contexts.append(enriched_text)

            chunk_indices.append(i)

        if not texts_to_embed:
            logger.warning("No texts to embed in multimodal mode")
            return chunks

        # Use CLIP to embed texts (CLIP can embed both text and image)
        try:
            embeddings = self.provider.embed_texts(texts_to_embed)

            # Add embeddings to chunks
            for idx, chunk_idx in enumerate(chunk_indices):
                chunk = chunks[chunk_idx]

                vector_id = self._generate_vector_id(chunk["chunk_id"])
                chunk["vector_id"] = vector_id
                chunk["embedding"] = embeddings[idx]
                chunk["embedding_model"] = self.provider.model_name if self.provider else self.model_name
                chunk["embedding_dimension"] = self.dimension
                chunk["embedding_provider"] = "clip_multimodal"
                chunk["multimodal_enriched"] = True

            logger.info(f"Successfully embedded {len(chunk_indices)} chunks with CLIP multimodal")
            return chunks

        except Exception as e:
            logger.error(f"CLIP multimodal embedding failed: {e}")
            raise

    def _enrich_text_with_visual_context(self, text: str, visual_facts: List[Dict[str, Any]]) -> str:
        """Enrich text with visual context for better CLIP embedding

        Args:
            text: Original text content
            visual_facts: Visual facts from VLM analysis

        Returns:
            Enriched text with visual descriptions
        """
        if not visual_facts:
            return text

        # Extract visual descriptions and append to text
        visual_descriptions = []
        for fact in visual_facts:
            if isinstance(fact, dict) and "description" in fact:
                visual_descriptions.append(fact["description"])
            elif isinstance(fact, str):
                visual_descriptions.append(fact)

        if not visual_descriptions:
            return text

        # Combine original text with visual descriptions
        visual_context = " ".join(visual_descriptions)
        enriched_text = f"{text}\n\nVisual context: {visual_context}"

        logger.debug(f"Enriched text from {len(text)} to {len(enriched_text)} characters with visual context")
        return enriched_text

    def embed_visual_regions(self,
                           regions: List[Dict[str, Any]],
                           image_path: Optional[str] = None) -> List[List[float]]:
        """Embed visual regions using CLIP

        Args:
            regions: List of visual regions with descriptions
            image_path: Path to the source image

        Returns:
            List of embedding vectors for each region
        """
        if not self.provider or not hasattr(self.provider, 'embed_image_regions'):
            raise Exception("Visual region embedding requires CLIP provider")

        if not image_path or not regions:
            return []

        try:
            return self.provider.embed_image_regions(image_path, regions)
        except Exception as e:
            logger.error(f"Visual region embedding failed: {e}")
            raise

    def _generate_vector_id(self, chunk_id) -> str:
        """Generate a deterministic vector ID based on chunk ID

        Args:
            chunk_id: UUID of the chunk

        Returns:
            String vector ID
        """
        import hashlib
        # Use hash of chunk_id for deterministic vector ID
        hash_obj = hashlib.md5(str(chunk_id).encode())
        return f"vec_{hash_obj.hexdigest()[:16]}"

    def _development_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Development fallback - NOT for production!

        Creates deterministic but meaningless embeddings based on text hashes.
        Only for development when no provider is available.
        """
        import hashlib

        embeddings = []
        for text in texts:
            # Create deterministic vector based on text hash
            hash_val = hashlib.md5(text.encode()).hexdigest()
            # Convert hash to float vector
            vector = []
            for i in range(0, 32, 8):  # Take 4 byte chunks from hash
                chunk = hash_val[i:i+8]
                val = int(chunk, 16) / (2**32 + 1)  # Normalize to [0,1)
                vector.append(val * 2 - 1)  # Scale to [-1, 1)

            # Pad/truncate to required dimensions
            while len(vector) < self.dimension:
                vector.extend(vector)  # Repeat pattern
            vector = vector[:self.dimension]

            embeddings.append(vector)

        logger.warning("Using development fallback embeddings - NOT suitable for production!")
        return embeddings

    def is_available(self) -> bool:
        """Check if embedding service is available"""
        if not self.provider:
            return False
        return self.provider.is_available()

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current embedding provider"""
        if self.provider:
            return self.provider.get_provider_info()
        else:
            return {
                "name": "fallback",
                "available": False,
                "type": "development_fallback"
            }

    def get_embedding_stats(self, embeddings: Optional[List[List[float]]] = None) -> Dict[str, Any]:
        """Get embedding statistics

        Args:
            embeddings: Optional list of embeddings to analyze

        Returns:
            Statistics dictionary
        """
        stats = {
            "provider": self.get_provider_info(),
            "model_name": self.model_name,
            "dimension": self.dimension,
            "available": self.is_available(),
        }

        if embeddings:
            try:
                import numpy as np
                norms = [np.linalg.norm(emb) for emb in embeddings]
                stats.update({
                    "total_embeddings": len(embeddings),
                    "avg_norm": float(np.mean(norms)),
                    "min_norm": float(np.min(norms)),
                    "max_norm": float(np.max(norms)),
                })
            except Exception as e:
                logger.warning(f"Could not calculate embedding stats: {e}")

        return stats
