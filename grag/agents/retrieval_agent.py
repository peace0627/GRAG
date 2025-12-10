"""
Retrieval Agent

This module implements the retrieval agent that performs multi-modal search
across vector databases and knowledge graphs with enhanced merging and caching.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
import time
import hashlib
from functools import lru_cache
import asyncio
from collections import defaultdict

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

        # Initialize caching system
        self._result_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._cache_timestamps = {}

        # Enhanced merging strategies
        self._merging_strategies = {
            'weighted_fusion': self._weighted_fusion_merge,
            'source_aware_merge': self._source_aware_merge,
            'adaptive_merge': self._adaptive_merge
        }

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
        """Enhanced merge and rank vector and graph results with intelligent fusion"""

        # Choose merging strategy based on parameters
        merge_strategy = parameters.get('merge_strategy', 'adaptive_merge')
        merge_func = self._merging_strategies.get(merge_strategy, self._adaptive_merge)

        logger.info(f"Using merge strategy: {merge_strategy}")

        # Apply selected merging strategy
        merged_results = merge_func(vector_results, graph_results, parameters)

        # Apply diversity and quality filtering
        filtered_results = self._apply_diversity_filter(merged_results, parameters)

        # Apply final ranking with recency and authority bonuses
        final_results = self._apply_enhanced_ranking(filtered_results, parameters)

        # Cache results for future use
        cache_key = self._generate_cache_key(vector_results, graph_results, parameters)
        self._cache_results(cache_key, final_results)

        # Apply final limit
        max_results = parameters.get('top_k', 20)
        return final_results[:max_results]

    def _weighted_fusion_merge(self, vector_results: List[Dict[str, Any]],
                              graph_results: List[Dict[str, Any]],
                              parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Weighted fusion with normalized scores"""
        all_results = []

        # Normalize and weight vector results
        for result in vector_results:
            normalized_score = self._normalize_score(result.get('similarity_score', 0.5), 'vector')
            weighted_score = normalized_score * 0.6  # 60% weight for vector similarity

            all_results.append({
                **result,
                'source': 'vector',
                'normalized_score': normalized_score,
                'weighted_score': weighted_score,
                'combined_score': weighted_score
            })

        # Normalize and weight graph results
        for result in graph_results:
            score = result.get('relevance_score', 0.5) or result.get('confidence', 0.5)
            normalized_score = self._normalize_score(score, 'graph')
            weighted_score = normalized_score * 0.4  # 40% weight for graph relevance

            all_results.append({
                **result,
                'source': 'graph',
                'normalized_score': normalized_score,
                'weighted_score': weighted_score,
                'combined_score': weighted_score
            })

        return all_results

    def _source_aware_merge(self, vector_results: List[Dict[str, Any]],
                           graph_results: List[Dict[str, Any]],
                           parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Source-aware merging considering content type and modality"""
        all_results = []

        # Process vector results with source awareness
        for result in vector_results:
            content_type = result.get('type', 'chunk')
            modality_bonus = 1.2 if content_type == 'vlm_region' else 1.0  # Boost visual content

            normalized_score = self._normalize_score(result.get('similarity_score', 0.5), 'vector')
            source_weight = self._get_source_weight('vector', result, parameters)
            combined_score = normalized_score * source_weight * modality_bonus

            all_results.append({
                **result,
                'source': 'vector',
                'combined_score': combined_score,
                'modality_bonus': modality_bonus,
                'source_weight': source_weight
            })

        # Process graph results with source awareness
        for result in graph_results:
            inference_bonus = 1.3 if result.get('inference_type') == 'multi_hop_reasoning' else 1.0
            temporal_bonus = 1.2 if 'temporal' in str(result).lower() else 1.0

            score = result.get('relevance_score', 0.5) or result.get('confidence', 0.5)
            normalized_score = self._normalize_score(score, 'graph')
            source_weight = self._get_source_weight('graph', result, parameters)
            combined_score = normalized_score * source_weight * inference_bonus * temporal_bonus

            all_results.append({
                **result,
                'source': 'graph',
                'combined_score': combined_score,
                'inference_bonus': inference_bonus,
                'temporal_bonus': temporal_bonus,
                'source_weight': source_weight
            })

        return all_results

    def _adaptive_merge(self, vector_results: List[Dict[str, Any]],
                       graph_results: List[Dict[str, Any]],
                       parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Adaptive merging based on query characteristics and result quality"""

        # Analyze query intent
        query_type = parameters.get('query_type', 'factual')
        requires_precision = parameters.get('requires_high_precision', False)

        # Choose strategy based on query characteristics
        if query_type == 'visual':
            # Prioritize visual vector results
            return self._modality_focused_merge(vector_results, graph_results, 'visual')
        elif query_type == 'temporal':
            # Prioritize temporal graph results
            return self._modality_focused_merge(vector_results, graph_results, 'temporal')
        elif query_type in ['analytical', 'causal']:
            # Balance precision and coverage
            return self._precision_coverage_merge(vector_results, graph_results, parameters)
        elif requires_precision:
            # Use source reliability weighting
            return self._source_reliability_merge(vector_results, graph_results)
        else:
            # Default weighted fusion
            return self._weighted_fusion_merge(vector_results, graph_results, parameters)

    def _modality_focused_merge(self, vector_results: List[Dict[str, Any]],
                               graph_results: List[Dict[str, Any]],
                               modality: str) -> List[Dict[str, Any]]:
        """Merge with focus on specific modality"""
        all_results = []

        modality_weights = {
            'visual': {'vector': 1.5, 'graph': 0.5},
            'temporal': {'vector': 0.6, 'graph': 1.4},
            'relational': {'vector': 0.4, 'graph': 1.6}
        }

        weights = modality_weights.get(modality, {'vector': 1.0, 'graph': 1.0})

        # Apply modality-specific weighting
        for result in vector_results:
            score = result.get('similarity_score', 0.5)
            combined_score = score * weights['vector']
            all_results.append({**result, 'source': 'vector', 'combined_score': combined_score})

        for result in graph_results:
            score = result.get('relevance_score', 0.5) or result.get('confidence', 0.5)
            combined_score = score * weights['graph']
            all_results.append({**result, 'source': 'graph', 'combined_score': combined_score})

        return all_results

    def _precision_coverage_merge(self, vector_results: List[Dict[str, Any]],
                                 graph_results: List[Dict[str, Any]],
                                 parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Balance precision (graph) and coverage (vector)"""
        precision_weight = 0.6  # Graph results get higher weight for precision
        coverage_weight = 0.4   # Vector results provide coverage

        all_results = []

        for result in vector_results:
            score = result.get('similarity_score', 0.5)
            combined_score = score * coverage_weight
            all_results.append({**result, 'source': 'vector', 'combined_score': combined_score})

        for result in graph_results:
            score = result.get('relevance_score', 0.5) or result.get('confidence', 0.5)
            combined_score = score * precision_weight
            all_results.append({**result, 'source': 'graph', 'combined_score': combined_score})

        return all_results

    def _source_reliability_merge(self, vector_results: List[Dict[str, Any]],
                                 graph_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge based on learned source reliability scores"""
        # Reliability scores (could be learned from user feedback)
        reliability_scores = {
            'vector': 0.75,
            'graph': 0.85
        }

        all_results = []

        for result in vector_results:
            score = result.get('similarity_score', 0.5)
            reliability = reliability_scores['vector']
            combined_score = score * reliability
            all_results.append({**result, 'source': 'vector', 'combined_score': combined_score})

        for result in graph_results:
            score = result.get('relevance_score', 0.5) or result.get('confidence', 0.5)
            reliability = reliability_scores['graph']
            combined_score = score * reliability
            all_results.append({**result, 'source': 'graph', 'combined_score': combined_score})

        return all_results

    def _apply_diversity_filter(self, results: List[Dict[str, Any]],
                               parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply diversity filtering to avoid over-representation of similar content"""
        if len(results) <= 5:
            return results  # No filtering needed for small result sets

        # Group by content similarity
        content_groups = defaultdict(list)
        for result in results:
            content_key = self._generate_content_signature(result)
            content_groups[content_key].append(result)

        # Apply diversity penalty
        diversity_penalty = 0.1  # 10% penalty per additional item from same group
        filtered_results = []

        for group in content_groups.values():
            if len(group) == 1:
                filtered_results.extend(group)
            else:
                # Sort group by score and apply penalty
                group_sorted = sorted(group, key=lambda x: x['combined_score'], reverse=True)
                for i, item in enumerate(group_sorted):
                    penalty = i * diversity_penalty
                    item['combined_score'] *= (1 - penalty)
                filtered_results.extend(group_sorted)

        return filtered_results

    def _apply_enhanced_ranking(self, results: List[Dict[str, Any]],
                               parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply enhanced ranking with multiple factors"""
        for result in results:
            base_score = result['combined_score']

            # Recency bonus (if temporal info available)
            recency_bonus = self._calculate_recency_bonus(result)

            # Authority bonus (based on source and metadata)
            authority_bonus = self._calculate_authority_bonus(result)

            # Relevance bonus (based on query matching)
            relevance_bonus = self._calculate_relevance_bonus(result, parameters)

            # Combine bonuses (diminishing returns)
            total_bonus = min(recency_bonus + authority_bonus + relevance_bonus, 0.5)
            result['final_score'] = base_score * (1 + total_bonus)

        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)

        return results

    def _normalize_score(self, score: float, source_type: str) -> float:
        """Normalize scores to 0-1 range based on source characteristics"""
        if source_type == 'vector':
            # Vector scores are typically 0-1, but can be cosine similarity
            return max(0.0, min(1.0, score))
        elif source_type == 'graph':
            # Graph scores might be different scales, normalize to 0-1
            return max(0.0, min(1.0, score))
        else:
            return max(0.0, min(1.0, score))

    def _get_source_weight(self, source_type: str, result: Dict[str, Any],
                          parameters: Dict[str, Any]) -> float:
        """Get dynamic source weight based on content and parameters"""
        base_weights = {
            'vector': 0.7,
            'graph': 0.8
        }

        weight = base_weights.get(source_type, 0.5)

        # Adjust based on content type
        if source_type == 'vector':
            content_type = result.get('type', 'chunk')
            if content_type == 'vlm_region':
                weight *= 1.2  # Boost visual content
        elif source_type == 'graph':
            if result.get('inference_type') == 'multi_hop_reasoning':
                weight *= 1.1  # Boost reasoning results

        return weight

    def _calculate_recency_bonus(self, result: Dict[str, Any]) -> float:
        """Calculate recency bonus based on temporal information"""
        # Placeholder - would use actual timestamp information
        return 0.05 if result.get('temporal_relevance') else 0.0

    def _calculate_authority_bonus(self, result: Dict[str, Any]) -> float:
        """Calculate authority bonus based on source credibility"""
        authority_bonus = 0.0

        if result['source'] == 'graph':
            if result.get('inference_type') == 'multi_hop_reasoning':
                authority_bonus += 0.1
            if result.get('connection_strength', 0) > 5:
                authority_bonus += 0.05

        return authority_bonus

    def _calculate_relevance_bonus(self, result: Dict[str, Any],
                                  parameters: Dict[str, Any]) -> float:
        """Calculate relevance bonus based on query-parameter matching"""
        relevance_bonus = 0.0

        # Boost visual results for visual queries
        if parameters.get('modality') == 'visual' and result.get('type') == 'vlm_region':
            relevance_bonus += 0.15

        # Boost temporal results for temporal queries
        if parameters.get('temporal') and 'temporal' in str(result).lower():
            relevance_bonus += 0.1

        return relevance_bonus

    def _generate_content_signature(self, result: Dict[str, Any]) -> str:
        """Generate content signature for diversity filtering"""
        content_parts = []

        if result['source'] == 'vector':
            content_parts.append(result.get('content', '')[:50])
        elif result['source'] == 'graph':
            if 'event' in result and result['event']:
                content_parts.append(str(result['event'].get('description', ''))[:50])
            elif 'source_entity' in result and result['source_entity']:
                content_parts.append(str(result['source_entity'].get('name', ''))[:50])

        content_parts.append(result['source'])
        content_parts.append(str(result.get('document_id', '')))

        return "|".join(content_parts)

    def _generate_cache_key(self, vector_results: List[Dict[str, Any]],
                           graph_results: List[Dict[str, Any]],
                           parameters: Dict[str, Any]) -> str:
        """Generate cache key for results"""
        # Create deterministic key based on result characteristics
        key_components = [
            str(len(vector_results)),
            str(len(graph_results)),
            str(parameters.get('top_k', 10)),
            str(parameters.get('merge_strategy', 'adaptive_merge'))
        ]

        return hashlib.md5("|".join(key_components).encode()).hexdigest()

    def _cache_results(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """Cache results for future use"""
        self._result_cache[cache_key] = results.copy()
        self._cache_timestamps[cache_key] = time.time()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()

        # Clean expired entries
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp > self._cache_ttl
        ]

        for key in expired_keys:
            self._result_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

        return {
            'cache_size': len(self._result_cache),
            'expired_cleaned': len(expired_keys),
            'cache_ttl': self._cache_ttl
        }

    def clear_cache(self) -> None:
        """Clear all cached results"""
        self._result_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cache cleared")

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
