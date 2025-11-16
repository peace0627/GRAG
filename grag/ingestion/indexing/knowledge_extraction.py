"""Knowledge extraction service for triples and entity relationships"""

import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
from datetime import datetime

from grag.core.config import settings

logger = logging.getLogger(__name__)


class KnowledgeExtractor:
    """Extract knowledge triples and relationships from text and visual content"""

    def __init__(self):
        """Initialize knowledge extraction service using environment configuration"""
        # Load extraction settings from environment
        self.extract_entities = settings.extract_entities
        self.extract_relations = settings.extract_relations
        self.extract_events = settings.extract_events
        self.min_entity_confidence = settings.min_entity_confidence

        # Basic entity types to extract (only if enabled)
        self.entity_types = {}
        if self.extract_entities:
            self.entity_types = {
                # More restrictive person extraction - require title OR first letter capital + spaces + reasonable length
                "PERSON": r"\b(?:Mr\.|Ms\.|Dr\.|Prof\.|Mrs\.)\s+[A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})*\b|\b[A-Z][a-z]{2,20}\s+[A-Z][a-z]{2,20}\b",
                # Organization - require company suffixes OR specific patterns
                "ORGANIZATION": r"\b[A-Z][a-zA-Z]{2,20}(?:\s+[A-Z][a-zA-Z]{2,20})*(?:\s+(?:Inc\.?|Ltd\.?|Corp\.?|LLC\.?|Company|Corporation|Corporation|University|College))\b",
                # LOCATION - More specific patterns with location indicators OR city/state/country names
                "LOCATION": r"\b(?:[A-Z][a-z]{2,20}(?:\s+[A-Z][a-z]{2,20})*(?:\s+(?:City|State|Province|Country|Town|Village|Mountain|River|Lake))\b|[A-Z][a-z]{2,20}\s+[A-Z][a-z]{2,20},?\s*[A-Z]{2,3}?\b)",
                # DATE - Keep existing robust date matching
                "DATE": r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|\d{1,2}(?:st|nd|rd|th)?)\s+(?:\d{1,2}(?:st|nd|rd|th)?,?)?\s*\d{4}\b",
                # MONEY - Keep existing money matching
                "MONEY": r"\$[\d,]+\.?\d*|\b\d+(?:,\d{3})*(?:\.\d{2})?\s+(?:dollars?|USD|euros?|EUR|pounds?|GBP)\b",
                # PERCENT - Keep existing percent matching
                "PERCENT": r"\b\d+(?:\.\d+)?%\b|\b\d+(?:\.\d+)?\s+percent\b",
            }

        # Relationship patterns (only if enabled)
        self.relationship_patterns = []
        if self.extract_relations:
            self.relationship_patterns = [
                (r"(\w+) (?:work\w*|employ\w*) (?:at|for) (\w+)", "WORK_AT"),
                (r"(\w+) (?:found\w*|establish\w*|start\w*) (\w+)", "FOUNDED_BY"),
                (r"(\w+) (?:locat\w+|sit\w*) (?:in|at) (\w+)", "LOCATED_IN"),
                (r"(\w+) (?:acquir\w*|buy|bought) (\w+)", "ACQUIRED"),
                (r"(\w+) (?:sell|sold) (?:to )?(\w+)", "SOLD_TO"),
                (r"(\w+) (?:partner\w*|collaborat\w*) (?:with )?(\w+)", "PARTNERS_WITH"),
            ]

    def extract_knowledge(self,
                         chunks: List[Dict[str, Any]],
                         visual_facts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Extract complete knowledge from chunks and visual facts with bulletproof error handling

        Args:
            chunks: Document chunks with text content
            visual_facts: Visual facts from VLM processing

        Returns:
            Dictionary with entities, relations, events, and visual facts
        """
        entities = []
        relations = []
        events = []

        try:
            logger.info(f"Starting knowledge extraction from {len(chunks)} chunks")

            # Extract from text chunks with ultra-safe processing
            for i, chunk in enumerate(chunks):
                try:
                    chunk_entities, chunk_relations, chunk_events = self._extract_from_chunk(chunk)
                    entities.extend(chunk_entities)
                    relations.extend(chunk_relations)
                    events.extend(chunk_events)
                except Exception as chunk_error:
                    logger.warning(f"Failed to extract from chunk {i}: {str(chunk_error)[:50]}..., continuing with other chunks")

            # Process visual facts if provided
            processed_visual_facts = []
            try:
                processed_visual_facts = self._process_visual_facts(visual_facts or [])
            except Exception as visual_error:
                logger.warning(f"Failed to process visual facts: {str(visual_error)[:50]}..., using empty list")

            # Filter and deduplicate with safe processing
            try:
                entities = self._deduplicate_entities(entities)
            except Exception as dedup_error:
                logger.warning(f"Entity deduplication failed: {str(dedup_error)[:50]}..., using original entities")

            try:
                relations = self._deduplicate_relations(relations)
            except Exception as dedup_error:
                logger.warning(f"Relation deduplication failed: {str(dedup_error)[:50]}..., using original relations")

            knowledge = {
                "entities": entities,
                "relations": relations,
                "events": events,
                "visual_facts": processed_visual_facts,
                "metadata": {
                    "total_entities": len(entities),
                    "total_relations": len(relations),
                    "total_events": len(events),
                    "total_visual_facts": len(processed_visual_facts),
                    "extraction_timestamp": datetime.now().isoformat(),
                    "extractor_version": "2.0.0-bulletproof"
                }
            }

            logger.info(f"Knowledge extraction completed: {len(entities)} entities, "
                       f"{len(relations)} relations, {len(events)} events")
            return knowledge

        except Exception as e:
            logger.error(f"Critical knowledge extraction failure: {e}")
            # Return minimal working knowledge structure so system can continue
            return {
                "entities": [],
                "relations": [],
                "events": [],
                "visual_facts": visual_facts or [],
                "metadata": {
                    "extraction_failed": True,
                    "error_message": str(e)[:200],
                    "timestamp": datetime.now().isoformat(),
                    "extractor_version": "2.0.0-bulletproof-fallback"
                }
            }

    def _extract_from_chunk(self, chunk: Dict[str, Any]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Extract knowledge from a single chunk

        Returns:
            Tuple of (entities, relations, events)
        """
        try:
            content = chunk.get("content", "")
            if not content or not isinstance(content, str):
                content = str(content or "")

            chunk_id = chunk.get("chunk_id")

            # Ensure chunk_id is a valid string or UUID
            if chunk_id is None:
                chunk_id = "unknown_chunk"
            try:
                chunk_id_str = str(chunk_id)
            except Exception:
                chunk_id_str = "unknown_chunk"
        except Exception as e:
            self.logger.error(f"Error preparing chunk data: {e}")
            return [], [], []

        entities = []
        relations = []
        events = []

        # Extract entities
        for entity_type, pattern in self.entity_types.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 1:  # Filter out very short matches
                    entity = {
                        "entity_id": self._generate_entity_id(match.strip(),
                                                                  entity_type,
                                                                  chunk_id),
                        "name": match.strip(),
                        "type": entity_type,
                        "chunk_id": str(chunk_id),
                        "confidence": self._calculate_entity_confidence(match, content),
                        "occurrences": [self._get_occurrence_info(match, content)],
                    }
                    entities.append(entity)

        # Extract relations
        for pattern, relation_type in self.relationship_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    subject = match.group(1).strip()
                    object_ = match.group(2).strip()

                    relation = {
                        "relation_id": self._generate_relation_id(subject, relation_type, object_, chunk_id),
                        "subject": subject,
                        "predicate": relation_type,
                        "object": object_,
                        "chunk_id": str(chunk_id),
                        "confidence": 0.7,  # Basic confidence for simple extraction
                        "evidence": match.group(0),
                    }
                    relations.append(relation)

        # Extract basic events (financial events, transactions, etc.)
        event_patterns = [
            (r"(\w+) reported? (\$\w+) (?:in|for) (\w+)", "FINANCIAL_REPORT"),
            (r"acquisition of (\w+) by (\w+)", "ACQUISITION"),
            (r"launch\w* of (\w+)", "PRODUCT_LAUNCH"),
        ]

        for pattern, event_type in event_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                event = {
                    "event_id": self._generate_event_id(event_type, chunk_id),
                    "type": event_type,
                    "description": match.group(0),
                    "timestamp": datetime.now().isoformat(),  # Placeholder - could be extracted
                    "entities_involved": list(match.groups()),
                    "chunk_id": str(chunk_id),
                    "evidence": match.group(0),
                }
                events.append(event)

        return entities, relations, events

    def _process_visual_facts(self, visual_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and enrich visual facts from VLM

        Args:
            visual_facts: Raw visual facts from VLM
        """
        processed_facts = []

        for fact in visual_facts:
            # Enrich with additional metadata
            enriched_fact = fact.copy()
            enriched_fact.update({
                "fact_id": str(UUID()),
                "processed_at": datetime.now().isoformat(),
                "confidence": fact.get("confidence", 0.8),
                "source": "vlm",
                "temporal_scope": None,  # Could be inferred from text
            })
            processed_facts.append(enriched_fact)

        return processed_facts

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities, keeping the most confident one"""
        entity_map = {}

        for entity in entities:
            key = (entity["name"].lower(), entity["type"])
            if key not in entity_map or entity["confidence"] > entity_map[key]["confidence"]:
                entity_map[key] = entity

        return list(entity_map.values())

    def _deduplicate_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate relations"""
        relation_map = {}

        for relation in relations:
            key = (relation["subject"].lower(),
                   relation["predicate"],
                   relation["object"].lower())
            if key not in relation_map:
                relation_map[key] = relation

        return list(relation_map.values())

    def _generate_entity_id(self, name: str, type_: str, chunk_id) -> str:
        """Generate deterministic entity ID"""
        import hashlib
        # Ensure chunk_id is string
        chunk_id_str = str(chunk_id) if chunk_id is not None else "none"
        hash_obj = hashlib.md5(f"{name}_{type_}_{chunk_id_str}".encode())
        return f"ent_{hash_obj.hexdigest()[:16]}"

    def _generate_relation_id(self, subject: str, predicate: str, object_: str, chunk_id) -> str:
        """Generate deterministic relation ID"""
        import hashlib
        # Ensure chunk_id is string
        chunk_id_str = str(chunk_id) if chunk_id is not None else "none"
        hash_obj = hashlib.md5(f"{subject}_{predicate}_{object_}_{chunk_id_str}".encode())
        return f"rel_{hash_obj.hexdigest()[:16]}"

    def _generate_event_id(self, event_type: str, chunk_id) -> str:
        """Generate deterministic event ID"""
        import hashlib
        # Ensure chunk_id is string
        chunk_id_str = str(chunk_id) if chunk_id is not None else "none"
        hash_obj = hashlib.md5(f"{event_type}_{chunk_id_str}_{datetime.now().isoformat()}".encode())
        return f"evt_{hash_obj.hexdigest()[:16]}"

    def _calculate_entity_confidence(self, match: str, content: str) -> float:
        """Calculate basic entity confidence score"""
        # Simple heuristics
        confidence = 0.5  # Base confidence

        # Higher confidence for capitalized words
        if match[0].isupper():
            confidence += 0.2

        # Higher confidence if entity appears multiple times
        count = content.lower().count(match.lower())
        confidence += min(count * 0.1, 0.2)

        # Lower confidence for very short entities
        if len(match) < 3:
            confidence *= 0.7

        return min(confidence, 1.0)

    def _get_occurrence_info(self, match: str, content: str) -> Dict[str, Any]:
        """Get information about where the entity occurs"""
        # Find first occurrence
        start_idx = content.find(match)
        return {
            "start": start_idx,
            "end": start_idx + len(match),
            "surrounding_context": content[max(0, start_idx-50):start_idx+len(match)+50],
        }
