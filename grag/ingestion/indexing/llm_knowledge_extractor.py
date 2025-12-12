"""LLM-powered knowledge extraction service for entities, relations, and events"""

import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
from datetime import datetime

from grag.core.config import settings

logger = logging.getLogger(__name__)


class LLMKnowledgeExtractor:
    """LLM-powered knowledge extraction using structured prompts and JSON parsing"""

    def __init__(self, use_llm: bool = True, batch_size: int = 5):
        """
        Initialize LLM knowledge extractor

        Args:
            use_llm: Whether to use LLM for extraction (fallback to rules if False)
            batch_size: Number of chunks to process in one LLM call
        """
        self.use_llm = use_llm
        self.batch_size = batch_size

        # Initialize LLM for knowledge extraction
        if use_llm:
            try:
                from grag.core.llm_factory import LLMFactory
                self.llm = LLMFactory.create_default_llm()
                logger.info("LLM Knowledge Extractor initialized with LLM support")
            except Exception as e:
                logger.error(f"LLM not available for knowledge extraction: {e}")
                self.use_llm = False
                self.llm = None
        else:
            self.llm = None

    async def extract_knowledge(self,
                               chunks: List[Dict[str, Any]],
                               visual_facts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Extract knowledge from chunks using LLM or rule-based fallback

        Args:
            chunks: Document chunks with text content
            visual_facts: Visual facts from VLM processing

        Returns:
            Dictionary with entities, relations, events, and visual facts
        """
        if self.use_llm:
            try:
                return await self._extract_with_llm(chunks, visual_facts)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, falling back to rules")
                return self._extract_with_rules(chunks, visual_facts)
        else:
            return self._extract_with_rules(chunks, visual_facts)

    async def _extract_with_llm(self,
                               chunks: List[Dict[str, Any]],
                               visual_facts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Extract knowledge using LLM with simple text format and concurrent processing"""
        import asyncio

        logger.info(f"Starting concurrent LLM knowledge extraction from {len(chunks)} chunks")

        # Filter out empty chunks
        valid_chunks = [chunk for chunk in chunks if chunk.get("content", "").strip()]
        logger.info(f"Processing {len(valid_chunks)} non-empty chunks out of {len(chunks)} total")

        if not valid_chunks:
            logger.warning("No valid chunks to process")
            return self._create_empty_result(visual_facts)

        # Create concurrent tasks for entity extraction
        tasks = []
        for chunk in valid_chunks:
            chunk_content = chunk.get("content", "")
            chunk_id = str(chunk.get("chunk_id", ""))
            task = self._extract_entities_with_timeout(chunk_content, chunk_id)
            tasks.append(task)

        # Execute all tasks concurrently with error handling
        logger.info(f"Starting concurrent processing of {len(tasks)} chunks")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        all_entities = []
        failed_chunks = 0

        for i, result in enumerate(results):
            chunk = valid_chunks[i]
            chunk_id = str(chunk.get("chunk_id", ""))

            if isinstance(result, Exception):
                logger.warning(f"Chunk {chunk_id} extraction failed: {str(result)[:100]}...")
                failed_chunks += 1
                continue

            if result and isinstance(result, list):
                all_entities.extend(result)
                logger.info(f"Chunk {chunk_id}: extracted {len(result)} entities")

        # Remove duplicates
        unique_entities = self._deduplicate_entities(all_entities)

        # Process visual facts if provided
        processed_visual_facts = self._process_visual_facts(visual_facts or [])

        extracted_data = {
            "entities": unique_entities,
            "relations": [],  # Empty for now
            "events": [],     # Empty for now
            "visual_facts": processed_visual_facts,
            "metadata": {
                "extraction_method": "llm_concurrent",
                "llm_model": getattr(self.llm, 'model_name', 'unknown'),
                "total_chunks": len(chunks),
                "valid_chunks": len(valid_chunks),
                "failed_chunks": failed_chunks,
                "entities_extracted": len(unique_entities),
                "extraction_timestamp": datetime.now().isoformat(),
                "extractor_version": "llm-concurrent-v1.0"
            }
        }

        logger.info(f"Concurrent LLM extraction completed: {len(unique_entities)} unique entities "
                   f"from {len(valid_chunks)} chunks ({failed_chunks} failed)")

        return extracted_data

    def _create_empty_result(self, visual_facts: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Create empty result when no valid chunks to process"""
        return {
            "entities": [],
            "relations": [],
            "events": [],
            "visual_facts": self._process_visual_facts(visual_facts or []),
            "metadata": {
                "extraction_method": "empty_input",
                "entities_extracted": 0,
                "extraction_timestamp": datetime.now().isoformat(),
                "extractor_version": "empty-v1.0"
            }
        }

    async def _extract_entities_with_timeout(self, content: str, chunk_id: str, timeout: float = 15.0) -> List[Dict[str, Any]]:
        """Extract entities with timeout to prevent hanging"""
        try:
            return await asyncio.wait_for(
                self._extract_entities_with_llm(content, chunk_id),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"LLM extraction timeout for chunk {chunk_id} after {timeout}s")
            return []
        except Exception as e:
            logger.warning(f"LLM extraction error for chunk {chunk_id}: {str(e)[:100]}...")
            return []

    def _extract_with_rules(self,
                           chunks: List[Dict[str, Any]],
                           visual_facts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Fallback when LLM is not available - return minimal structure"""
        logger.warning("Rule-based extraction not available, returning empty results")

        # Return minimal valid structure when no extraction method is available
        return {
            "entities": [],
            "relations": [],
            "events": [],
            "visual_facts": visual_facts or [],
            "metadata": {
                "extraction_method": "none",
                "error": "No extraction method available",
                "timestamp": datetime.now().isoformat(),
                "extractor_version": "fallback-only"
            }
        }

    def _prepare_content_for_llm(self, chunks: List[Dict[str, Any]]) -> str:
        """Prepare content from chunks for LLM processing"""
        content_parts = []

        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "").strip()
            if content:
                # Add chunk marker for reference
                content_parts.append(f"--- Chunk {i+1} ---\n{content}")

        combined_content = "\n\n".join(content_parts)

        # Limit content length to avoid token limits
        max_length = 8000  # Leave room for prompt and response
        if len(combined_content) > max_length:
            combined_content = combined_content[:max_length] + "\n\n[Content truncated due to length...]"

        return combined_content

    def _create_extraction_prompt(self, content: str) -> str:
        """Create simplified structured prompt for LLM knowledge extraction"""
        # Simplify prompt to improve JSON parsing success rate
        prompt = f"""分析以下文本，提取實體、關係和事件。請以JSON格式返回：

文本：{content[:3000]}  # 限制內容長度

返回格式：
{{
  "entities": [
    {{"id": "e1", "name": "實體名稱", "type": "PERSON|ORGANIZATION|LOCATION|PRODUCT", "confidence": 0.9}}
  ],
  "relations": [
    {{"id": "r1", "subject": "實體A", "predicate": "關聯類型", "object": "實體B", "confidence": 0.8}}
  ],
  "events": [
    {{"id": "ev1", "type": "事件類型", "description": "事件描述", "entities_involved": ["實體"]}}
  ]
}}

只返回JSON，不要其他內容。"""

        return prompt

    def _parse_llm_response(self, llm_output: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse LLM JSON response and convert to internal format"""
        try:
            # Clean up LLM output
            llm_output = llm_output.strip()

            # Remove markdown code blocks if present
            if llm_output.startswith("```json"):
                llm_output = llm_output[7:]
            if llm_output.startswith("```"):
                llm_output = llm_output[3:]
            if llm_output.endswith("```"):
                llm_output = llm_output[:-3]

            llm_output = llm_output.strip()

            # Parse JSON
            parsed = json.loads(llm_output)

            # Convert to internal format
            entities = self._convert_llm_entities(parsed.get("entities", []), chunks)
            relations = self._convert_llm_relations(parsed.get("relations", []), chunks)
            events = self._convert_llm_events(parsed.get("events", []), chunks)

            return {
                "entities": entities,
                "relations": relations,
                "events": events
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM output: {llm_output[:500]}...")
            # Return empty result on parse failure
            return {"entities": [], "relations": [], "events": []}
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {"entities": [], "relations": [], "events": []}

    def _convert_llm_entities(self, llm_entities: List[Dict], chunks: List[Dict[str, Any]]) -> List[Dict]:
        """Convert LLM entities to internal format"""
        entities = []

        for llm_entity in llm_entities:
            try:
                # Find chunk IDs where this entity appears
                chunk_ids = []
                entity_name = llm_entity["name"]
                for chunk in chunks:
                    content = chunk.get("content", "")
                    if entity_name.lower() in content.lower():
                        chunk_ids.append(str(chunk.get("chunk_id", "unknown")))

                entity = {
                    "entity_id": llm_entity.get("id", str(uuid4())),
                    "name": llm_entity["name"],
                    "type": llm_entity["type"],
                    "chunk_id": chunk_ids[0] if chunk_ids else None,  # Primary chunk (compatible with rule extractor)
                    "confidence": llm_entity.get("confidence", 0.8),
                    "occurrences": [{
                        "start": 0,
                        "end": len(llm_entity["name"]),
                        "surrounding_context": llm_entity.get("description", "")
                    }]  # Add occurrences for compatibility
                }
                entities.append(entity)

            except Exception as e:
                logger.warning(f"Error converting LLM entity: {e}")
                continue

        return entities

    def _convert_llm_relations(self, llm_relations: List[Dict], chunks: List[Dict[str, Any]]) -> List[Dict]:
        """Convert LLM relations to internal format"""
        relations = []

        for llm_relation in llm_relations:
            try:
                relation = {
                    "relation_id": llm_relation.get("id", str(uuid4())),
                    "subject": llm_relation["subject"],
                    "predicate": llm_relation["predicate"],
                    "object": llm_relation["object"],
                    "confidence": llm_relation.get("confidence", 0.7),
                    "evidence": llm_relation.get("evidence", ""),
                    "chunk_id": None  # Will be set by finding matching chunk
                }

                # Find chunk where this relation appears
                evidence = llm_relation.get("evidence", "")
                for chunk in chunks:
                    content = chunk.get("content", "")
                    if evidence and evidence in content:
                        relation["chunk_id"] = str(chunk.get("chunk_id", "unknown"))
                        break

                relations.append(relation)

            except Exception as e:
                logger.warning(f"Error converting LLM relation: {e}")
                continue

        return relations

    async def _extract_entities_with_llm(self, content: str, chunk_id: str) -> List[Dict[str, Any]]:
        """Extract entities using LLM with simple text format (no JSON parsing issues)"""
        if not hasattr(self, 'llm') or not self.llm:
            return []

        try:
            # Create simple text prompt for LLM
            prompt = f"""從以下文本中提取重要實體。請按以下格式輸出：

文本內容：
{content[:1500]}  # 限制長度避免token限制

輸出格式：
實體: [實體名稱] ([類型])
實體: [實體名稱] ([類型])
...

實體類型包括:
- PERSON: 人名
- ORGANIZATION: 組織機構、公司、政府部門
- LOCATION: 地點、地址
- DATE: 日期
- PRODUCT: 產品名稱
- OTHER: 其他重要實體

只需要列出最重要的實體，不要超過10個。
直接輸出實體列表，不要包含其他解釋。"""

            # Call LLM
            from langchain_core.messages import HumanMessage
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            llm_output = response.content.strip()

            logger.info(f"LLM entity extraction output: {llm_output[:300]}...")

            # Parse the simple text format
            entities = self._parse_llm_entity_output(llm_output, content, chunk_id)

            logger.info(f"LLM extracted {len(entities)} entities from chunk {chunk_id}")
            return entities

        except Exception as e:
            logger.warning(f"LLM entity extraction failed: {e}, falling back to regex")
            return []

    def _parse_llm_entity_output(self, output: str, content: str, chunk_id: str) -> List[Dict[str, Any]]:
        """Parse LLM output in simple text format"""
        entities = []

        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('實體:') or line.startswith('Entity:'):
                # Parse "實體: Food and Drug Administration (ORGANIZATION)"
                # or "Entity: Food and Drug Administration (ORGANIZATION)"
                match = re.search(r'(?:實體|Entity):\s*([^()]+)\s*\(([^)]+)\)', line, re.IGNORECASE)
                if match:
                    name, type_ = match.groups()
                    name = name.strip()
                    type_ = type_.strip().upper()

                    # Validate entity type
                    valid_types = {'PERSON', 'ORGANIZATION', 'LOCATION', 'DATE', 'PRODUCT', 'OTHER'}
                    if type_ in valid_types and len(name) > 1:
                        entity = {
                            "entity_id": str(uuid4()),
                            "name": name,
                            "type": type_,
                            "chunk_id": chunk_id,
                            "confidence": 0.85,  # Higher confidence for LLM extraction
                            "occurrences": [self._get_occurrence_info(name, content)],
                            "extraction_method": "llm"
                        }
                        entities.append(entity)

        return entities

    def _get_occurrence_info(self, match: str, content: str) -> Dict[str, Any]:
        """Get information about where the entity occurs"""
        # Find first occurrence
        start_idx = content.find(match)
        return {
            "start": start_idx,
            "end": start_idx + len(match),
            "surrounding_context": content[max(0, start_idx-50):start_idx+len(match)+50],
        }

    def _convert_llm_events(self, llm_events: List[Dict], chunks: List[Dict[str, Any]]) -> List[Dict]:
        """Convert LLM events to internal format"""
        events = []

        for llm_event in llm_events:
            try:
                # Find chunk where this event appears
                chunk_id = None
                description = llm_event.get("description", "")
                for chunk in chunks:
                    content = chunk.get("content", "")
                    if description and description in content:
                        chunk_id = str(chunk.get("chunk_id", "unknown"))
                        break

                event = {
                    "event_id": llm_event.get("id", str(uuid4())),
                    "type": llm_event["type"],
                    "description": description,
                    "timestamp": llm_event.get("timestamp", datetime.now().isoformat()),
                    "entities_involved": llm_event.get("entities_involved", []),
                    "chunk_id": chunk_id,
                    "evidence": description  # Add evidence field for compatibility
                }
                events.append(event)

            except Exception as e:
                logger.warning(f"Error converting LLM event: {e}")
                continue

        return events

    def _process_visual_facts(self, visual_facts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and enrich visual facts from VLM"""
        processed_facts = []

        for fact in visual_facts:
            try:
                # Enrich with additional metadata
                enriched_fact = fact.copy()
                enriched_fact.update({
                    "fact_id": str(uuid4()),
                    "processed_at": datetime.now().isoformat(),
                    "confidence": fact.get("confidence", 0.8),
                    "source": "vlm",
                    "temporal_scope": None,  # Could be inferred from text
                })
                processed_facts.append(enriched_fact)
            except Exception as fact_error:
                logger.warning(f"Failed to process individual visual fact: {str(fact_error)[:50]}..., skipping")
                continue

        return processed_facts

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entities, keeping the most confident one"""
        entity_map = {}

        for entity in entities:
            key = (entity["name"].lower().strip(), entity["type"])
            if key not in entity_map or entity["confidence"] > entity_map[key]["confidence"]:
                entity_map[key] = entity

        return list(entity_map.values())

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            "method": "llm" if self.use_llm else "rules",
            "batch_size": self.batch_size,
            "llm_available": self.use_llm
        }
