"""
Reasoning Agent

This module implements the reasoning agent that performs knowledge graph
reasoning, path finding, and subgraph extraction.
"""

import logging
from typing import Dict, Any, List, Optional
import time

from .schemas import ReasoningResult
from ..core.database_services import DatabaseManager
from ..core.config import get_config

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """Agent for performing knowledge graph reasoning operations"""

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

    async def reason(self, query: str, context: Dict[str, Any],
                    reasoning_type: str = "general") -> ReasoningResult:
        """Main reasoning entry point"""
        start_time = time.time()

        result = ReasoningResult()

        try:
            if reasoning_type == "entity_relationship":
                result = await self._entity_relationship_reasoning(query, context)
            elif reasoning_type == "path_finding":
                result = await self._path_finding_reasoning(query, context)
            elif reasoning_type == "temporal":
                result = await self._temporal_reasoning(query, context)
            elif reasoning_type == "causal":
                result = await self._causal_reasoning(query, context)
            else:
                result = await self._general_reasoning(query, context)

            result.reasoning_trace = self._generate_reasoning_trace(result, reasoning_type)
            result.confidence = self._calculate_confidence(result)

        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            result.confidence = 0.0
            result.reasoning_trace = f"Reasoning failed: {str(e)}"

        execution_time = time.time() - start_time
        logger.info(f"Reasoning completed in {execution_time:.2f}s with confidence {result.confidence:.2f}")

        return result

    async def _entity_relationship_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Reason about entity relationships and connections"""
        result = ReasoningResult()

        try:
            async with self.db_manager.neo4j_session() as session:
                # Extract entities from query
                entities = await self._extract_entities_from_query(session, query)

                if not entities:
                    result.reasoning_path = ["No entities found in query"]
                    return result

                # Find relationships between entities
                relationships = []
                for entity1 in entities:
                    for entity2 in entities:
                        if entity1 != entity2:
                            rels = await self._find_relationships_between_entities(
                                session, entity1, entity2
                            )
                            relationships.extend(rels)

                # Build relationship graph
                relationship_graph = self._build_relationship_graph(entities, relationships)

                result.inferred_relations = relationships
                result.subgraph_nodes = entities
                result.reasoning_path = [
                    f"Found {len(entities)} entities in query",
                    f"Discovered {len(relationships)} relationships",
                    f"Built relationship graph with {len(relationship_graph)} connections"
                ]

        except Exception as e:
            logger.error(f"Entity relationship reasoning failed: {e}")
            result.reasoning_path = [f"Error: {str(e)}"]

        return result

    async def _path_finding_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Find reasoning paths between concepts"""
        result = ReasoningResult()

        try:
            async with self.db_manager.neo4j_session() as session:
                # Find shortest paths between key concepts
                paths = await self._find_shortest_paths(session, query)

                if paths:
                    result.reasoning_path = [
                        f"Found {len(paths)} reasoning paths",
                        "Paths ranked by length and relevance"
                    ]
                    result.inferred_relations = paths
                else:
                    result.reasoning_path = ["No direct paths found between concepts"]

                # Find alternative paths
                alternative_paths = await self._find_alternative_paths(session, query)
                if alternative_paths:
                    result.reasoning_path.append(
                        f"Found {len(alternative_paths)} alternative reasoning paths"
                    )

        except Exception as e:
            logger.error(f"Path finding reasoning failed: {e}")
            result.reasoning_path = [f"Error: {str(e)}"]

        return result

    async def _temporal_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Perform temporal reasoning on events and sequences"""
        result = ReasoningResult()

        try:
            async with self.db_manager.neo4j_session() as session:
                # Extract temporal aspects from query
                temporal_aspects = self._extract_temporal_aspects(query)

                # Find temporally related events
                temporal_events = await self._find_temporal_events(session, temporal_aspects)

                # Build event sequence
                event_sequence = self._build_event_sequence(temporal_events)

                result.inferred_relations = temporal_events
                result.subgraph_nodes = event_sequence
                result.reasoning_path = [
                    f"Extracted {len(temporal_aspects)} temporal aspects",
                    f"Found {len(temporal_events)} related events",
                    f"Built event sequence with {len(event_sequence)} nodes"
                ]

        except Exception as e:
            logger.error(f"Temporal reasoning failed: {e}")
            result.reasoning_path = [f"Error: {str(e)}"]

        return result

    async def _causal_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """Perform causal reasoning on cause-effect relationships"""
        result = ReasoningResult()

        try:
            async with self.db_manager.neo4j_session() as session:
                # Find causal chains
                causal_chains = await self._find_causal_chains(session, query)

                if causal_chains:
                    result.inferred_relations = causal_chains
                    result.reasoning_path = [
                        f"Found {len(causal_chains)} causal chains",
                        "Analyzed cause-effect relationships"
                    ]
                else:
                    result.reasoning_path = ["No causal relationships found"]

                # Find indirect causal links
                indirect_causes = await self._find_indirect_causal_links(session, query)
                if indirect_causes:
                    result.reasoning_path.append(
                        f"Found {len(indirect_causes)} indirect causal links"
                    )

        except Exception as e:
            logger.error(f"Causal reasoning failed: {e}")
            result.reasoning_path = [f"Error: {str(e)}"]

        return result

    async def _general_reasoning(self, query: str, context: Dict[str, Any]) -> ReasoningResult:
        """General reasoning combining multiple approaches"""
        result = ReasoningResult()

        try:
            # Combine entity, path, and temporal reasoning
            entity_result = await self._entity_relationship_reasoning(query, context)
            path_result = await self._path_finding_reasoning(query, context)
            temporal_result = await self._temporal_reasoning(query, context)

            # Merge results
            all_relations = []
            all_relations.extend(entity_result.inferred_relations or [])
            all_relations.extend(path_result.inferred_relations or [])
            all_relations.extend(temporal_result.inferred_relations or [])

            all_nodes = []
            all_nodes.extend(entity_result.subgraph_nodes or [])
            all_nodes.extend(path_result.subgraph_nodes or [])
            all_nodes.extend(temporal_result.subgraph_nodes or [])

            result.inferred_relations = self._deduplicate_relations(all_relations)
            result.subgraph_nodes = self._deduplicate_nodes(all_nodes)
            result.reasoning_path = [
                "Applied multi-faceted reasoning approach",
                f"Entity reasoning: {len(entity_result.inferred_relations or [])} relations",
                f"Path reasoning: {len(path_result.inferred_relations or [])} relations",
                f"Temporal reasoning: {len(temporal_result.inferred_relations or [])} relations",
                f"Total unique relations: {len(result.inferred_relations)}"
            ]

        except Exception as e:
            logger.error(f"General reasoning failed: {e}")
            result.reasoning_path = [f"Error: {str(e)}"]

        return result

    async def _extract_entities_from_query(self, session, query: str) -> List[Dict[str, Any]]:
        """Extract entities mentioned in the query"""
        # This would use NLP/entity recognition in production
        # For now, use simple keyword matching against graph entities

        cypher_query = """
        MATCH (e:Entity)
        WHERE ANY(keyword IN $keywords WHERE
              toLower(e.name) CONTAINS toLower(keyword) OR
              ANY(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower(keyword)))
        RETURN DISTINCT e
        LIMIT 10
        """

        keywords = query.split()  # Simple tokenization
        results = await session.run(cypher_query, keywords=keywords)

        entities = []
        async for record in results:
            entities.append(dict(record['e']))

        return entities

    async def _find_relationships_between_entities(self, session, entity1: Dict[str, Any],
                                                 entity2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find relationships between two entities"""
        cypher_query = """
        MATCH (e1:Entity {entity_id: $id1}), (e2:Entity {entity_id: $id2})
        MATCH path = shortestPath((e1)-[*..5]-(e2))
        WHERE length(path) > 0
        RETURN path, length(path) as path_length
        ORDER BY path_length
        LIMIT 5
        """

        results = await session.run(cypher_query,
                                  id1=entity1['entity_id'],
                                  id2=entity2['entity_id'])

        relationships = []
        async for record in results:
            relationships.append({
                'path': str(record['path']),
                'length': record['path_length'],
                'source_entity': entity1['name'],
                'target_entity': entity2['name']
            })

        return relationships

    async def _find_shortest_paths(self, session, query: str) -> List[Dict[str, Any]]:
        """Find shortest reasoning paths for the query"""
        cypher_query = """
        CALL db.index.fulltext.queryNodes("entityNameIndex", $query)
        YIELD node, score
        WITH collect({node: node, score: score}) as entities
        UNWIND entities as e1
        UNWIND entities as e2
        WITH e1, e2
        WHERE e1.node <> e2.node
        MATCH path = shortestPath((e1.node)-[*1..4]-(e2.node))
        WHERE length(path) > 0
        RETURN e1.node.name as source, e2.node.name as target,
               path, length(path) as path_length, e1.score + e2.score as combined_score
        ORDER BY combined_score DESC, path_length ASC
        LIMIT 10
        """

        results = await session.run(cypher_query, query=query)

        paths = []
        async for record in results:
            paths.append({
                'source': record['source'],
                'target': record['target'],
                'path': str(record['path']),
                'path_length': record['path_length'],
                'combined_score': record['combined_score']
            })

        return paths

    async def _find_alternative_paths(self, session, query: str) -> List[Dict[str, Any]]:
        """Find alternative reasoning paths"""
        cypher_query = """
        CALL db.index.fulltext.queryNodes("entityNameIndex", $query)
        YIELD node, score
        WITH node, score
        MATCH (node)-[r]-(connected)
        WHERE type(r) <> "HAS_CHUNK"
        WITH node, connected, type(r) as rel_type, score
        ORDER BY score DESC
        LIMIT 20
        RETURN node.name as entity, connected.name as related_entity,
               rel_type, labels(connected) as related_type
        """

        results = await session.run(cypher_query, query=query)

        alternative_paths = []
        async for record in results:
            alternative_paths.append({
                'entity': record['entity'],
                'related_entity': record['related_entity'],
                'relationship_type': record['rel_type'],
                'related_entity_type': list(record['related_type'])
            })

        return alternative_paths

    async def _find_temporal_events(self, session, temporal_aspects: List[str]) -> List[Dict[str, Any]]:
        """Find events related to temporal aspects"""
        cypher_query = """
        MATCH (e:Event)
        WHERE ANY(aspect IN $aspects WHERE
              toLower(e.description) CONTAINS toLower(aspect) OR
              toLower(e.type) CONTAINS toLower(aspect))
        OPTIONAL MATCH (e)-[:PARTICIPATES_IN]-(entity:Entity)
        RETURN e, collect(entity) as participants
        ORDER BY e.timestamp DESC
        LIMIT 15
        """

        results = await session.run(cypher_query, aspects=temporal_aspects)

        events = []
        async for record in results:
            events.append({
                'event': dict(record['e']),
                'participants': [dict(p) for p in record['participants']]
            })

        return events

    async def _find_causal_chains(self, session, query: str) -> List[Dict[str, Any]]:
        """Find causal chains in the knowledge graph"""
        cypher_query = """
        MATCH (e1:Event)-[:CAUSES]->(e2:Event)
        WHERE toLower(e1.description) CONTAINS toLower($query) OR
              toLower(e2.description) CONTAINS toLower($query)
        OPTIONAL MATCH (e1)-[:PARTICIPATES_IN]-(entity1:Entity)
        OPTIONAL MATCH (e2)-[:PARTICIPATES_IN]-(entity2:Entity)
        RETURN e1, e2, collect(DISTINCT entity1) as cause_participants,
               collect(DISTINCT entity2) as effect_participants
        LIMIT 10
        """

        results = await session.run(cypher_query, query=query)

        causal_chains = []
        async for record in results:
            causal_chains.append({
                'cause_event': dict(record['e1']),
                'effect_event': dict(record['e2']),
                'cause_participants': [dict(p) for p in record['cause_participants'] if p],
                'effect_participants': [dict(p) for p in record['effect_participants'] if p]
            })

        return causal_chains

    async def _find_indirect_causal_links(self, session, query: str) -> List[Dict[str, Any]]:
        """Find indirect causal relationships"""
        cypher_query = """
        MATCH (e1:Event)-[:CAUSES*2..3]->(e3:Event)
        WHERE toLower(e1.description) CONTAINS toLower($query) OR
              toLower(e3.description) CONTAINS toLower($query)
        WITH e1, e3, length(relationships(path)) as chain_length
        WHERE chain_length <= 3
        RETURN e1, e3, chain_length
        ORDER BY chain_length
        LIMIT 10
        """

        results = await session.run(cypher_query, query=query)

        indirect_links = []
        async for record in results:
            indirect_links.append({
                'source_event': dict(record['e1']),
                'target_event': dict(record['e3']),
                'causal_chain_length': record['chain_length']
            })

        return indirect_links

    def _build_relationship_graph(self, entities: List[Dict[str, Any]],
                                relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a relationship graph from entities and relationships"""
        graph = {
            'nodes': [{'id': e['entity_id'], 'name': e['name'], 'type': 'entity'} for e in entities],
            'edges': []
        }

        for rel in relationships:
            graph['edges'].append({
                'source': rel.get('source_entity'),
                'target': rel.get('target_entity'),
                'path': rel.get('path'),
                'length': rel.get('length')
            })

        return graph

    def _build_event_sequence(self, temporal_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build chronological sequence of events"""
        # Sort events by timestamp
        sorted_events = sorted(
            temporal_events,
            key=lambda x: x['event'].get('timestamp', ''),
            reverse=True
        )

        return [event['event'] for event in sorted_events]

    def _extract_temporal_aspects(self, query: str) -> List[str]:
        """Extract temporal aspects from query"""
        temporal_keywords = [
            '時間', '日期', '月份', '年份', '季度', '週', '小時', '分鐘',
            'year', 'month', 'day', 'quarter', 'week', 'hour', 'minute',
            '現在', '今天', '昨天', '明天', '之前', '之後',
            'now', 'today', 'yesterday', 'tomorrow', 'before', 'after',
            '第一季度', '第二季度', '第三季度', '第四季度',
            'Q1', 'Q2', 'Q3', 'Q4'
        ]

        found_aspects = []
        query_lower = query.lower()

        for keyword in temporal_keywords:
            if keyword in query_lower:
                found_aspects.append(keyword)

        return found_aspects

    def _deduplicate_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate relationships"""
        seen = set()
        unique_relations = []

        for rel in relations:
            # Create a hashable key from relationship
            key = frozenset(rel.items()) if isinstance(rel, dict) else str(rel)
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)

        return unique_relations

    def _deduplicate_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate nodes"""
        seen = set()
        unique_nodes = []

        for node in nodes:
            node_id = node.get('entity_id') or node.get('event_id') or str(node)
            if node_id not in seen:
                seen.add(node_id)
                unique_nodes.append(node)

        return unique_nodes

    def _generate_reasoning_trace(self, result: ReasoningResult, reasoning_type: str) -> str:
        """Generate human-readable reasoning trace"""
        trace_parts = [
            f"Reasoning Type: {reasoning_type}",
            f"Reasoning Path: {' -> '.join(result.reasoning_path)}",
            f"Inferred Relations: {len(result.inferred_relations)}",
            f"Subgraph Nodes: {len(result.subgraph_nodes)}",
            f"Confidence Score: {result.confidence:.2f}"
        ]

        return " | ".join(trace_parts)

    def _calculate_confidence(self, result: ReasoningResult) -> float:
        """Calculate confidence score for reasoning results"""
        if not result.inferred_relations and not result.subgraph_nodes:
            return 0.0

        # Base confidence from number of results
        relation_confidence = min(len(result.inferred_relations) * 0.1, 0.5)
        node_confidence = min(len(result.subgraph_nodes) * 0.05, 0.3)

        # Path quality factor
        path_quality = 0.2 if result.reasoning_path and len(result.reasoning_path) > 1 else 0.0

        total_confidence = relation_confidence + node_confidence + path_quality

        return min(total_confidence, 1.0)
