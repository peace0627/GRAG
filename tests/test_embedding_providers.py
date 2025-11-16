#!/usr/bin/env python3
"""Test script for embedding providers integration

This script tests the new embedding provider architecture including:
- Provider factory creation
- SentenceTransformer provider
- EmbeddingService integration
- Configuration loading from environment
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from grag.core.config import settings
from grag.ingestion.indexing.providers.embedding_providers import create_embedding_provider, get_provider_info, list_available_providers
from grag.ingestion.indexing.embedding_service import EmbeddingService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_configuration_loading():
    """Test that configuration is loaded correctly from settings"""
    print("🧪 Testing configuration loading...")

    print(f"  EMBEDDING_PROVIDER: {settings.embedding_provider}")
    print(f"  EMBEDDING_MODEL: {settings.embedding_model}")
    print(f"  EMBEDDING_DIMENSION: {settings.embedding_dimension}")
    print(f"  EMBEDDING_API_KEY: {'*' * len(settings.embedding_api_key) if settings.embedding_api_key else 'Not set'}")

    assert settings.embedding_provider is not None, "Embedding provider should be configured"
    assert settings.embedding_model is not None, "Embedding model should be configured"
    assert settings.embedding_dimension > 0, "Embedding dimension should be positive"

    print("✅ Configuration loading test passed")
    return True


def test_factory_creation():
    """Test provider factory creates providers correctly"""
    print("🧪 Testing provider creation...")

    # Test creating a provider
    provider = create_embedding_provider()
    print(f"  Created provider: {provider.get_info()['name']}")
    print(f"  Provider dimension: {provider.dimension}")
    print(f"  Provider available: {provider.is_available()}")

    # Get provider info
    info = provider.get_info()
    print(f"  Provider info: {info}")

    assert provider is not None, "Provider should be created"
    assert hasattr(provider, 'embed_texts'), "Provider should have embed_texts method"
    assert hasattr(provider, 'dimension'), "Provider should have dimension"
    assert hasattr(provider, 'is_available'), "Provider should have is_available method"

    print("✅ Provider creation test passed")
    return provider


def test_embedding_service():
    """Test EmbeddingService integration"""
    print("🧪 Testing EmbeddingService...")

    # Create embedding service
    service = EmbeddingService()
    print(f"  Service created with provider: {service.get_provider_info()['name']}")
    print(f"  Service dimension: {service.dimension}")
    print(f"  Service available: {service.is_available()}")

    # Test embedding some sample texts
    test_texts = [
        "This is a test document.",
        "The GraphRAG system processes multimodal content.",
        "Embeddings capture semantic meaning of text."
    ]

    print("  Testing embed_texts...")
    embeddings = service.embed_texts(test_texts)
    print(f"  Generated {len(embeddings)} embeddings")
    print(f"  Embedding dimension: {len(embeddings[0]) if embeddings else 0}")

    # Test single embedding
    print("  Testing embed_single_text...")
    single_embedding = service.embed_single_text(test_texts[0])
    print(f"  Single embedding dimension: {len(single_embedding)}")

    assert len(embeddings) == len(test_texts), "Should return same number of embeddings as inputs"
    assert len(single_embedding) == service.dimension, f"Single embedding should be dimension {service.dimension}"

    print("✅ EmbeddingService test passed")
    return embeddings


def test_chunk_embedding():
    """Test embedding chunks functionality"""
    print("🧪 Testing chunk embedding...")

    # Create mock chunks
    chunks = [
        {
            "chunk_id": "test-chunk-1",
            "document_id": "test-doc-1",
            "content": "This is the first test chunk with some content.",
            "order": 0,
            "metadata": {"source": "test"}
        },
        {
            "chunk_id": "test-chunk-2",
            "document_id": "test-doc-1",
            "content": "This is the second test chunk for embedding.",
            "order": 1,
            "metadata": {"source": "test"}
        }
    ]

    service = EmbeddingService()

    print("  Testing embed_chunks...")
    enriched_chunks = service.embed_chunks(chunks)

    print(f"  Original chunks: {len(chunks)}")
    print(f"  Enriched chunks: {len(enriched_chunks)}")

    # Check that chunks now have embedding data
    for i, chunk in enumerate(enriched_chunks):
        assert "vector_id" in chunk, f"Chunk {i} should have vector_id"
        assert "embedding" in chunk, f"Chunk {i} should have embedding"
        assert "embedding_model" in chunk, f"Chunk {i} should have embedding_model"
        assert "embedding_dimension" in chunk, f"Chunk {i} should have embedding_dimension"
        assert "embedding_provider" in chunk, f"Chunk {i} should have embedding_provider"

        print(f"  Chunk {i} embedded with provider: {chunk['embedding_provider']}")

    assert len(enriched_chunks) == len(chunks), "Should preserve original number of chunks"

    print("✅ Chunk embedding test passed")
    return enriched_chunks


def test_provider_utilities():
    """Test utility functions"""
    print("🧪 Testing utility functions...")

    # Test listing available providers
    providers = list_available_providers()
    print(f"  Available providers: {providers}")
    assert "sentence_transformers" in providers, "Should include sentence_transformers"

    # Test getting requirements for a provider
    requirements = get_provider_info("sentence_transformers")
    print(f"  SentenceTransformers requirements: {requirements}")

    assert "packages" in requirements, "Should have packages info"
    assert "cost" in requirements, "Should have cost info"

    print("✅ Utility functions test passed")


def main():
    """Run all embedding provider tests"""
    print("🚀 Running Embedding Providers Integration Tests\n")

    try:
        # Run all tests
        test_configuration_loading()
        print()

        provider = test_factory_creation()
        print()

        embeddings = test_embedding_service()
        print()

        enriched_chunks = test_chunk_embedding()
        print()

        test_provider_utilities()
        print()

        print("🎉 All embedding provider tests passed!")
        print("\n📊 Test Summary:")
        print(f"  - Configuration loaded successfully")
        print(f"  - Provider factory working")
        print(f"  - Embedding service functional")
        print(f"  - Chunk embedding working")
        print(f"  - Factory utilities available")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
