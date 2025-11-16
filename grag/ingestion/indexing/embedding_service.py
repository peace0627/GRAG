"""Unified embedding service for text and multimodal content"""

import logging
from typing import List, Dict, Any, Optional, Union
import hashlib
import numpy as np

from sentence_transformers import SentenceTransformer
from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Unified embedding service supporting multiple embedding providers"""

    def __init__(self):
        """Initialize embedding service using environment configuration"""
        # Load config from environment
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension

        # Initialize model
        self._init_model()

    def _init_model(self):
        """Initialize the embedding model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded successfully. Dimension: {self.dimension}")
        except Exception as e:
            logger.warning(f"Failed to load SentenceTransformer model: {e}")
            logger.info("Falling back to simple hashing (for development only)")

            # Fallback for development - not for production!
            self.model = None
            self.dimension = 384

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            if self.model:
                # Use proper model
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                return embeddings.tolist()
            else:
                # Development fallback
                return self._development_embeddings(texts)

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimension for _ in texts]

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

            logger.info(f"Successfully embedded {len(chunk_indices)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Chunk embedding failed: {e}")
            # Add empty embeddings as fallback
            for chunk in chunks:
                if "vector_id" not in chunk:
                    chunk["vector_id"] = self._generate_vector_id(chunk["chunk_id"])
                    chunk["embedding"] = [0.0] * self.dimension
            return chunks

    def _generate_vector_id(self, chunk_id) -> str:
        """Generate a deterministic vector ID based on chunk ID

        Args:
            chunk_id: UUID of the chunk

        Returns:
            String vector ID
        """
        # Use hash of chunk_id for deterministic vector ID
        hash_obj = hashlib.md5(str(chunk_id).encode())
        return f"vec_{hash_obj.hexdigest()[:16]}"

    def _development_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Development fallback - NOT for production!

        Creates deterministic but meaningless embeddings based on text hashes.
        Only for development when SentenceTransformer is not available.
        """
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

    def get_embedding_stats(self, embeddings: Optional[List[List[float]]] = None) -> Dict[str, Any]:
        """Get embedding statistics

        Args:
            embeddings: Optional list of embeddings to analyze

        Returns:
            Statistics dictionary
        """
        stats = {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "model_loaded": self.model is not None,
        }

        if embeddings:
            norms = [np.linalg.norm(emb) for emb in embeddings]
            stats.update({
                "total_embeddings": len(embeddings),
                "avg_norm": np.mean(norms),
                "min_norm": np.min(norms),
                "max_norm": np.max(norms),
            })

        return stats
