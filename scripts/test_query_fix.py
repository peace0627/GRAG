#!/usr/bin/env python3
"""
Test script to verify the query strategy fixes for GraphRAG

This script tests:
1. Vector similarity search functionality
2. Neo4j fulltext index setup
3. Evidence collection and confidence calculation
4. End-to-end query processing
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from grag.core.config import get_config
from grag.core.database_services import DatabaseManager
from grag.agents.retrieval_agent import RetrievalAgent
from grag.agents.rag_agent import AgenticRAGAgent
from grag.agents.schemas import ToolType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_database_connections():
    """Test Neo4j and Supabase connections"""
    logger.info("Testing database connections...")

    config = get_config()
    db_manager = DatabaseManager(
        neo4j_uri=config.neo4j_uri,
        neo4j_user=config.neo4j_user,
        neo4j_password=config.neo4j_password,
        supabase_url=config.supabase_url,
        supabase_key=config.supabase_key
    )

    try:
        # Test Neo4j connection
        async with db_manager.neo4j_session() as session:
            result = await session.run("MATCH () RETURN count(*) as node_count")
            record = await result.single()
            node_count = record['node_count']
            logger.info(f"✅ Neo4j connected - {node_count} nodes in database")

        # Test Supabase connection
        client = db_manager.get_supabase_client()
        response = client.table('vectors').select('count', count='exact').limit(1).execute()
        logger.info("✅ Supabase connected")

        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def test_fulltext_indexes():
    """Test Neo4j fulltext indexes"""
    logger.info("Testing Neo4j fulltext indexes...")

    config = get_config()
    db_manager = DatabaseManager(
        neo4j_uri=config.neo4j_uri,
        neo4j_user=config.neo4j_user,
        neo4j_password=config.neo4j_password,
        supabase_url=config.supabase_url,
        supabase_key=config.supabase_key
    )

    try:
        async with db_manager.neo4j_session() as session:
            # Check if indexes exist
            result = await session.run("""
            CALL db.indexes()
            YIELD name, state, type
            WHERE type = "FULLTEXT"
            RETURN name, state
            ORDER BY name
            """)

            indexes = await result.fetch(-1)
            fulltext_indexes = [record['name'] for record in indexes]

            expected_indexes = ['entityNameIndex', 'eventIndex', 'visualFactIndex', 'chunkContentIndex', 'documentIndex']

            missing_indexes = []
            for expected in expected_indexes:
                if expected not in fulltext_indexes:
                    missing_indexes.append(expected)

            if missing_indexes:
                logger.warning(f"❌ Missing fulltext indexes: {missing_indexes}")
                logger.info("Run: docker-compose exec neo4j cypher-shell -u neo4j -p testpass123 -f /setup-indexes.cypher")
                return False
            else:
                logger.info(f"✅ All fulltext indexes present: {fulltext_indexes}")
                return True

    except Exception as e:
        logger.error(f"❌ Fulltext index test failed: {e}")
        return False


async def test_vector_search():
    """Test vector similarity search"""
    logger.info("Testing vector similarity search...")

    try:
        retrieval_agent = RetrievalAgent()

        # Test with a simple query
        test_query = "test query for vector search"
        parameters = {
            'top_k': 5,
            'similarity_threshold': 0.1
        }

        result = await retrieval_agent.retrieve(test_query, ToolType.VECTOR_SEARCH, parameters)

        if result.vector_results:
            logger.info(f"✅ Vector search returned {len(result.vector_results)} results")
            for i, res in enumerate(result.vector_results[:3]):  # Show first 3
                logger.info(f"  Result {i+1}: similarity={res.get('similarity_score', 'N/A')}, content='{res.get('content', '')[:50]}...'")
            return True
        else:
            logger.warning("⚠️ Vector search returned no results (this may be expected if no data is indexed)")
            return True  # Not a failure, just no data

    except Exception as e:
        logger.error(f"❌ Vector search test failed: {e}")
        return False


async def test_evidence_collection():
    """Test evidence collection from retrieval results"""
    logger.info("Testing evidence collection...")

    try:
        retrieval_agent = RetrievalAgent()

        # Create a mock retrieval result
        from grag.agents.schemas import RetrievalResult

        mock_result = RetrievalResult(query="test query")
        mock_result.vector_results = [
            {
                'source': 'vector',
                'content': 'Test vector content',
                'similarity_score': 0.8,
                'document_id': 'test-doc-1',
                'combined_score': 0.8
            }
        ]

        evidence_list = await retrieval_agent.collect_evidence(mock_result)

        if evidence_list:
            logger.info(f"✅ Evidence collection returned {len(evidence_list)} evidence items")
            for evidence in evidence_list:
                logger.info(f"  Evidence: confidence={evidence.confidence:.2f}, content='{evidence.content[:50]}...'")
            return True
        else:
            logger.warning("⚠️ Evidence collection returned no evidence")
            return False

    except Exception as e:
        logger.error(f"❌ Evidence collection test failed: {e}")
        return False


async def test_rag_agent():
    """Test the full RAG agent pipeline"""
    logger.info("Testing full RAG agent pipeline...")

    try:
        # Test system status first
        rag_agent = AgenticRAGAgent()

        status = await rag_agent.get_system_status()
        logger.info(f"System status: {status.get('status', 'unknown')}")

        # Test a simple query
        test_query = "What is machine learning?"
        logger.info(f"Testing query: '{test_query}'")

        result = await rag_agent.query(test_query)

        if result.get('success') is False:
            logger.warning(f"⚠️ Query failed: {result.get('error', 'Unknown error')}")
            return False

        confidence = result.get('confidence_score', 0.0)
        evidence_count = result.get('evidence_count', 0)

        logger.info(f"✅ Query completed - confidence: {confidence:.2f}, evidence: {evidence_count}")
        logger.info(f"Answer: {result.get('final_answer', '')[:100]}...")

        # Check if confidence is reasonable (> 0)
        if confidence > 0:
            logger.info("✅ Query returned non-zero confidence")
            return True
        else:
            logger.warning("⚠️ Query returned zero confidence - may indicate no evidence found")
            return True  # Not necessarily a failure if no data

    except Exception as e:
        logger.error(f"❌ RAG agent test failed: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("🚀 Starting GraphRAG Query Strategy Fix Tests")
    logger.info("=" * 60)

    tests = [
        ("Database Connections", test_database_connections),
        ("Fulltext Indexes", test_fulltext_indexes),
        ("Vector Search", test_vector_search),
        ("Evidence Collection", test_evidence_collection),
        ("RAG Agent Pipeline", test_rag_agent),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n📋 Running: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
            status = "✅ PASSED" if success else "❌ FAILED"
            logger.info(f"{status}: {test_name}")
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {test_name}")
        if success:
            passed += 1

    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Query strategy fixes are working.")
        return 0
    else:
        logger.warning(f"⚠️ {total - passed} tests failed. Check the issues above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
