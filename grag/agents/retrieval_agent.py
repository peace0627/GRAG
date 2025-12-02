"""
Retrieval Agent

This module implements the retrieval agent that performs multi-modal search
across vector databases and knowledge graphs.
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
import time

from .schemas import (
    RetrievalResult,
    Evidence,
    ToolType
)
from ..core.database_services import DatabaseManager
from ..core.config import get_config

logger = logging.getLogger(__name__)


class RetrievalAgent:
    """Agent for performing multi-modal retrieval operations"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or self._initialize_db_manager()
        self.config = get_config()

    def _initialize_db_manager(self) -> DatabaseManager:
        """Initialize database manager from config"""
        config = get_config()
        return DatabaseManager(
            neo4j_uri=config.neo4j_uri,
            neo4j_user=config.neo4j_user,
            neo4j_password=config.neo4j_password,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key
        )

    async def retrieve(self, query: str, tool_type: ToolType,
                      parameters: Dict[str, Any]) -> RetrievalResult:
        """Main retrieval entry point"""
        start_time = time.time()

        result = RetrievalResult(query=query)

        try:
            if tool_type == ToolType.VECTOR_SEARCH:
                vector_results = await self._vector_search(query, parameters)
                result.vector_results = vector_results

            elif tool_type == ToolType.GRAPH_TRAVERSAL:
                graph_results = await self._graph_traversal(query, parameters)
                result.graph_results = graph_results

            elif tool_type == ToolType.VLM_RERUN:
                # VLM re-run would be handled by a separate service
                # For now, return empty results
                logger.info("VLM re-run requested but not implemented yet")
                result.vector_results = []

            # Merge results if both types were performed
            if result.vector_results and result.graph_results:
                result.merged_results = self._merge_results(
                    result.vector_results,
                    result.graph_results,
                    parameters
                )

            result.execution_time = time.time() - start_time
            logger.info(f"Retrieval completed in {result.execution_time:.2f}s")

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            result.execution_time = time.time() - start_time
            raise

        return result

    async def _vector_search(self, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        # This is a simplified implementation
        # In production, you would:
        # 1. Generate embedding for the query
        # 2. Perform similarity search in Supabase pgvector
        # 3. Return ranked results

        try:
            # Placeholder: Get all vectors (in production, use similarity search)
            client = self.db_manager.get_supabase_client()

            # Build query based on parameters
            supabase_query = client.table('vectors').select('*')

            # Apply filters
            if parameters.get('modality') == 'visual':
                supabase_query = supabase_query.eq('type', 'vlm_region')
            else:
                supabase_query = supabase_query.eq('type', 'chunk')

            if parameters.get('document_id'):
                supabase_query = supabase_query.eq('document_id', str(parameters['document_id']))

            if parameters.get('temporal_filter'):
                # Add temporal filtering logic here
                pass

            # Apply limit
            top_k = parameters.get('top_k', 10)
            supabase_query = supabase_query.limit(top_k)

            response = supabase_query.execute()

            results = []
            for item in response.data:
                results.append({
                    'vector_id': item['vector_id'],
                    'document_id': item['document_id'],
                    'chunk_id': item.get('chunk_id'),
                    'fact_id': item.get('fact_id'),
                    'type': item['type'],
                    'page': item['page'],
                    'order': item['order'],
                    'similarity_score': 0.8,  # Placeholder similarity score
                    'content': self._get_content_preview(item),
                    'metadata': item
                })

            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    async def _graph_traversal(self, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform knowledge graph traversal"""
        try:
            async with self.db_manager.neo4j_session() as session:
                results = []

                # Determine traversal strategy based on parameters
                if parameters.get('temporal'):
                    results = await self._temporal_graph_search(session, query, parameters)
                elif parameters.get('reasoning'):
                    results = await self._reasoning_graph_search(session, query, parameters)
                elif parameters.get('explore'):
                    results = await self._exploratory_graph_search(session, query, parameters)
                else:
                    results = await self._basic_graph_search(session, query, parameters)

                logger.info(f"Graph traversal returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Graph traversal failed: {e}")
            raise

    async def _basic_graph_search(self, session, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Basic graph search for entities and relationships"""
        max_depth = parameters.get('max_depth', 2)

        cypher_query = f"""
        CALL db.index.fulltext.queryNodes("entityNameIndex", "{query}")
        YIELD node, score
        MATCH path = (node)-[*1..{max_depth}]-(connected)
        WHERE ALL(r IN relationships(path) WHERE type(r) <> "HAS_CHUNK")
        RETURN node, connected, path, score
        LIMIT 20
        """

        results = await session.run(cypher_query)
        records = await results.fetch(20)

        formatted_results = []
        for record in records:
            formatted_results.append({
                'node': dict(record['node']),
                'connected_node': dict(record['connected']),
                'relationship_path': str(record['path']),
                'relevance_score': record['score'],
                'node_type': record['node'].labels,
                'connected_type': record['connected'].labels
            })

        return formatted_results

    async def _temporal_graph_search(self, session, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Temporal graph search with time-based filtering"""
        # Extract temporal keywords from query
        temporal_terms = self._extract_temporal_terms(query)

        cypher_query = """
        MATCH (e:Event)
        WHERE ANY(term IN $temporal_terms WHERE term IN e.description OR term IN e.type)
        OPTIONAL MATCH (e)-[:PARTICIPATES_IN]-(entity:Entity)
        OPTIONAL MATCH (e)-[:CAUSES]-(next_event:Event)
        RETURN e, entity, next_event
        ORDER BY e.timestamp DESC
        LIMIT 15
        """

        results = await session.run(cypher_query, temporal_terms=temporal_terms)
        records = await results.fetch(15)

        formatted_results = []
        for record in records:
            formatted_results.append({
                'event': dict(record['e']) if record['e'] else None,
                'participant': dict(record['entity']) if record['entity'] else None,
                'next_event': dict(record['next_event']) if record['next_event'] else None,
                'temporal_relevance': 0.9
            })

        return formatted_results

    async def _reasoning_graph_search(self, session, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Graph search with reasoning and relationship inference"""
        max_depth = parameters.get('max_depth', 3)

        # Multi-hop reasoning query
        cypher_query = f"""
        CALL db.index.fulltext.queryNodes("entityNameIndex", "{query}")
        YIELD node, score
        MATCH path = (node)-[*1..{max_depth}]-(target)
        WHERE length(path) > 1
        WITH node, target, path, score,
             [r IN relationships(path) | type(r)] as rel_types,
             length(path) as path_length
        RETURN node, target, rel_types, path_length, score
        ORDER BY score DESC, path_length ASC
        LIMIT 25
        """

        results = await session.run(cypher_query)
        records = await results.fetch(25)

        formatted_results = []
        for record in records:
            formatted_results.append({
                'source_entity': dict(record['node']),
                'target_entity': dict(record['target']),
                'relationship_chain': record['rel_types'],
                'path_length': record['path_length'],
                'confidence': record['score'],
                'inference_type': 'multi_hop_reasoning'
            })

        return formatted_results

    async def _exploratory_graph_search(self, session, query: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Exploratory search to discover related concepts"""
        max_depth = parameters.get('max_depth', 4)

        cypher_query = f"""
        CALL db.index.fulltext.queryNodes("entityNameIndex", "{query}")
        YIELD node, score
        MATCH (node)-[*1..{max_depth}]-(related)
        WITH DISTINCT related,
             count(*) as connection_strength,
             collect(DISTINCT type(relationship)) as relation_types
        WHERE NOT related = node
        RETURN related, connection_strength, relation_types
        ORDER BY connection_strength DESC
        LIMIT 30
        """

        results = await session.run(cypher_query)
        records = await results.fetch(30)

        formatted_results = []
        for record in records:
            formatted_results.append({
                'related_entity': dict(record['related']),
                'connection_strength': record['connection_strength'],
                'relationship_types': record['relation_types'],
                'entity_type': list(record['related'].labels)[0] if record['related'].labels else 'unknown'
            })

        return formatted_results

    def _merge_results(self, vector_results: List[Dict[str, Any]],
                      graph_results: List[Dict[str, Any]],
                      parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Merge and rank vector and graph results"""
        merged = []

        # Simple merging strategy: combine and deduplicate by content
        seen_content = set()

        # Add vector results first
        for result in vector_results:
            content_key = result.get('content', '')[:100]  # Use first 100 chars as key
            if content_key not in seen_content:
                merged.append({
                    **result,
                    'source': 'vector',
                    'combined_score': result.get('similarity_score', 0.5)
                })
                seen_content.add(content_key)

        # Add graph results with lower priority
        for result in graph_results:
            # Extract content key from graph result
            if 'event' in result and result['event']:
                content_key = result['event'].get('description', '')[:100]
            elif 'source_entity' in result and result['source_entity']:
                content_key = result['source_entity'].get('name', '')[:100]
            else:
                content_key = str(result)[:100]

            if content_key not in seen_content:
                merged.append({
                    **result,
                    'source': 'graph',
                    'combined_score': result.get('relevance_score', 0.3) or result.get('confidence', 0.3)
                })
                seen_content.add(content_key)

        # Sort by combined score
        merged.sort(key=lambda x: x['combined_score'], reverse=True)

        # Apply final limit
        max_results = parameters.get('top_k', 20)
        return merged[:max_results]

    def _get_content_preview(self, vector_item: Dict[str, Any]) -> str:
        """Get content preview from vector item"""
        # This would typically fetch the actual content
        # For now, return a placeholder
        if vector_item.get('type') == 'chunk':
            return f"Text chunk from page {vector_item.get('page', 'unknown')}"
        elif vector_item.get('type') == 'vlm_region':
            return f"Visual content from page {vector_item.get('page', 'unknown')}"
        else:
            return "Content preview not available"

    def _extract_temporal_terms(self, query: str) -> List[str]:
        """Extract temporal keywords from query"""
        temporal_keywords = [
            '年', '月', '日', '季度', '週', '小時', '分鐘',
            'year', 'month', 'day', 'quarter', 'week', 'hour', 'minute',
            '現在', '今天', '昨天', '明天', '之前', '之後',
            'now', 'today', 'yesterday', 'tomorrow', 'before', 'after'
        ]

        found_terms = []
        query_lower = query.lower()

        for term in temporal_keywords:
            if term in query_lower:
                found_terms.append(term)

        return found_terms

    async def collect_evidence(self, retrieval_result: RetrievalResult) -> List[Evidence]:
        """Convert retrieval results to evidence objects"""
        evidence_list = []

        for result in retrieval_result.merged_results:
            evidence = Evidence(
                evidence_id=str(UUID.uuid4()),
                source_type=result.get('source', 'unknown'),
                content=result.get('content', str(result)),
                confidence=result.get('combined_score', 0.5),
                metadata={
                    'source': result.get('source'),
                    'similarity_score': result.get('similarity_score'),
                    'relevance_score': result.get('relevance_score'),
                    'entity_type': result.get('entity_type'),
                    'relationship_types': result.get('relationship_types', [])
                }
            )

            # Add document/page info if available
            if 'page' in result:
                evidence.page_number = result['page']
            if 'document_id' in result:
                evidence.source_document = result['document_id']

            evidence_list.append(evidence)

        return evidence_list
