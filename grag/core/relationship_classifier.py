"""
LLM-Powered Relationship Classifier for Domain-Specific Neo4j Relationships

This module provides intelligent relationship classification using LLMs to automatically
determine the most appropriate relationship type between nodes based on domain context.
"""

import logging
from typing import Dict, Any, List, Tuple

from .schemas.domain_relationships import (
    DomainType,
    relationship_registry,
    RelationshipClassificationRequest,
    RelationshipClassificationResponse
)
from ..core.llm_factory import create_answerer_llm
from ..core.config import get_config

logger = logging.getLogger(__name__)


class RelationshipClassifier:
    """LLM-powered classifier for domain-specific relationships"""

    def __init__(self, llm=None):
        self.llm = llm or create_answerer_llm()
        self.config = get_config()
        self.relationship_registry = relationship_registry

    async def classify_relationship(self, domain: DomainType, source_node: Dict[str, Any],
                                  target_node: Dict[str, Any], context_text: str = "") -> RelationshipClassificationResponse:
        """Classify relationship between two nodes using LLM"""

        # Get available relationships for the domain and node types
        available_relationships = self._get_available_relationships(domain, source_node, target_node)

        if not available_relationships:
            # Fallback to legacy relationships
            available_relationships = ["MENTIONED_IN", "RELATED_TO", "PARTICIPATES_IN", "CAUSES", "DESCRIBED_BY_IMAGE"]

        request = RelationshipClassificationRequest(
            domain=domain,
            source_node=source_node,
            target_node=target_node,
            context_text=context_text,
            available_relationships=available_relationships
        )

        try:
            response = await self._call_llm_classifier(request)
            return response
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # Return fallback classification
            return RelationshipClassificationResponse(
                relationship_type="RELATED_TO",  # Safe fallback
                confidence=0.3,
                reasoning=f"LLM classification failed: {str(e)}, using fallback",
                properties={}
            )

    def _get_available_relationships(self, domain: DomainType, source_node: Dict[str, Any],
                                   target_node: Dict[str, Any]) -> List[str]:
        """Get available relationship types based on node types"""

        # Extract node types
        source_type = self._extract_node_type(source_node)
        target_type = self._extract_node_type(target_node)

        # Get available relationships from registry
        available = self.relationship_registry.get_available_relationships(
            domain, source_type, target_type
        )

        return available

    def _extract_node_type(self, node: Dict[str, Any]) -> str:
        """Extract node type from node data"""
        # Try different ways to get node type
        if "type" in node:
            return node["type"]
        elif "entity_type" in node:
            return node["entity_type"]
        elif "labels" in node and node["labels"]:
            # Neo4j labels
            return list(node["labels"])[0] if isinstance(node["labels"], (list, set)) else str(node["labels"])
        elif "node_type" in node:
            return node["node_type"]
        else:
            # Try to infer from node properties
            if "name" in node and "description" in node:
                return "Entity"
            elif "timestamp" in node:
                return "Event"
            elif "text" in node:
                return "Chunk"
            else:
                return "Unknown"

    async def _call_llm_classifier(self, request: RelationshipClassificationRequest) -> RelationshipClassificationResponse:
        """Call LLM for relationship classification"""

        # Build domain-specific prompt
        prompt = self._build_classification_prompt(request)

        try:
            from langchain_core.messages import HumanMessage

            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)

            # Parse LLM response
            return self._parse_llm_response(response.content, request.available_relationships)

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def _build_classification_prompt(self, request: RelationshipClassificationRequest) -> str:
        """Build domain-specific classification prompt"""

        domain = request.domain.value
        source_node = request.source_node
        target_node = request.target_node
        context = request.context_text
        available_rels = request.available_relationships

        # Domain-specific guidance
        domain_guidance = self._get_domain_guidance(domain)

        # Format available relationships with descriptions
        relationships_text = self._format_relationships_for_prompt(domain, available_rels)

        prompt = f"""
你是一個專業的知識圖譜分析師，負責為{domain_guidance}領域分類實體間的關係。

**任務**: 分析以下兩個節點之間的關係，並選擇最合適的關係類型。

**來源節點**:
{self._format_node_for_prompt(source_node)}

**目標節點**:
{self._format_node_for_prompt(target_node)}

**上下文資訊**:
{context or "無額外上下文"}

**可用關係類型** (請從以下選項中選擇最合適的一個):
{relationships_text}

**輸出格式**:
請以JSON格式回答：
{{
    "relationship_type": "選擇的關係類型",
    "confidence": 0.0-1.0之間的信心分數,
    "reasoning": "選擇這個關係類型的詳細理由",
    "properties": {{
        "相關屬性": "值"
    }}
}}

**分析步驟**:
1. 理解兩個節點的性質和內容
2. 考慮它們在{domain}領域中的語義關係
3. 評估哪個關係類型最準確地捕捉它們的聯繫
4. 提供具體的理由和信心評估

請確保選擇的關係類型來自可用選項列表。
"""

        return prompt

    def _get_domain_guidance(self, domain: str) -> str:
        """Get domain-specific guidance for LLM"""
        guidance = {
            "financial": "上市公司財報和財務分析",
            "medical_device": "醫療器材法規遵循和臨床應用",
            "prospect": "潛在客戶關係管理和銷售機會",
            "internal_report": "公司內部研究和品質報告",
            "general": "通用商業和技術文件"
        }
        return guidance.get(domain, domain)

    def _format_relationships_for_prompt(self, domain: str, relationships: List[str]) -> str:
        """Format relationships with descriptions for prompt"""
        formatted = []

        for rel in relationships:
            rel_def = self.relationship_registry.get_relationship_definition(
                DomainType(domain), rel
            )

            if rel_def:
                desc = rel_def.get("description", "無描述")
                category = rel_def.get("category", "unknown")
                props = rel_def.get("properties", [])
                props_text = f" (屬性: {', '.join(props)})" if props else ""

                formatted.append(f"- {rel}: {desc}{props_text}")
            else:
                formatted.append(f"- {rel}: 通用關係")

        return "\n".join(formatted)

    def _format_node_for_prompt(self, node: Dict[str, Any]) -> str:
        """Format node information for prompt"""
        lines = []

        # Node type
        node_type = self._extract_node_type(node)
        lines.append(f"類型: {node_type}")

        # Key properties
        for key, value in node.items():
            if key not in ["labels", "id", "uuid"] and value is not None:
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"{key}: {value}")
                elif isinstance(value, list) and len(value) <= 3:
                    lines.append(f"{key}: {', '.join(str(v) for v in value)}")

        return "\n".join(lines)

    def _parse_llm_response(self, response_text: str, available_relationships: List[str]) -> RelationshipClassificationResponse:
        """Parse LLM response into structured format"""
        import json

        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed = json.loads(json_text)

                # Validate relationship type
                rel_type = parsed.get("relationship_type", "")
                if rel_type not in available_relationships:
                    logger.warning(f"LLM suggested invalid relationship: {rel_type}, using fallback")
                    rel_type = available_relationships[0] if available_relationships else "RELATED_TO"

                return RelationshipClassificationResponse(
                    relationship_type=rel_type,
                    confidence=min(max(float(parsed.get("confidence", 0.5)), 0.0), 1.0),
                    reasoning=parsed.get("reasoning", "LLM分類結果"),
                    properties=parsed.get("properties", {})
                )
            else:
                # Fallback parsing for non-JSON responses
                return self._parse_text_response(response_text, available_relationships)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._parse_text_response(response_text, available_relationships)

    def _parse_text_response(self, response_text: str, available_relationships: List[str]) -> RelationshipClassificationResponse:
        """Fallback parsing for text-based LLM responses"""
        text = response_text.lower()

        # Try to find relationship type in text
        for rel in available_relationships:
            if rel.lower() in text:
                return RelationshipClassificationResponse(
                    relationship_type=rel,
                    confidence=0.6,  # Moderate confidence for text parsing
                    reasoning=f"從文本響應中提取: {response_text[:100]}...",
                    properties={}
                )

        # Ultimate fallback
        fallback_rel = available_relationships[0] if available_relationships else "RELATED_TO"
        return RelationshipClassificationResponse(
            relationship_type=fallback_rel,
            confidence=0.3,
            reasoning="無法解析LLM響應，使用預設關係",
            properties={}
        )

    async def batch_classify_relationships(self, domain: DomainType,
                                         relationships: List[Tuple[Dict[str, Any], Dict[str, Any], str]]) -> List[RelationshipClassificationResponse]:
        """Batch classify multiple relationships for efficiency"""

        results = []
        for source_node, target_node, context in relationships:
            try:
                result = await self.classify_relationship(domain, source_node, target_node, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch classification failed for relationship: {e}")
                # Add fallback result
                results.append(RelationshipClassificationResponse(
                    relationship_type="RELATED_TO",
                    confidence=0.2,
                    reasoning=f"批量處理失敗: {str(e)}",
                    properties={}
                ))

        return results

    def get_relationship_suggestions(self, domain: DomainType, source_type: str,
                                   target_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relationship suggestions for given node types"""

        available = self.relationship_registry.get_available_relationships(
            domain, source_type, target_type
        )

        suggestions = []
        for rel_type in available[:limit]:
            rel_def = self.relationship_registry.get_relationship_definition(domain, rel_type)
            if rel_def:
                suggestions.append({
                    "relationship_type": rel_type,
                    "description": rel_def.get("description", ""),
                    "category": rel_def.get("category", "unknown"),
                    "properties": rel_def.get("properties", [])
                })

        return suggestions

    async def validate_relationship_usage(self, domain: DomainType, relationship_type: str,
                                        source_node: Dict[str, Any], target_node: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if a relationship type is appropriate for given nodes"""

        source_type = self._extract_node_type(source_node)
        target_type = self._extract_node_type(target_node)

        is_valid = self.relationship_registry.validate_relationship(
            domain, relationship_type, source_type, target_type
        )

        rel_def = self.relationship_registry.get_relationship_definition(domain, relationship_type)

        return {
            "is_valid": is_valid,
            "relationship_definition": rel_def,
            "source_type": source_type,
            "target_type": target_type,
            "domain": domain.value
        }


# Global classifier instance
relationship_classifier = RelationshipClassifier()


async def classify_relationship(domain: DomainType, source_node: Dict[str, Any],
                              target_node: Dict[str, Any], context: str = "") -> RelationshipClassificationResponse:
    """Convenience function for relationship classification"""
    return await relationship_classifier.classify_relationship(domain, source_node, target_node, context)


def get_domain_relationships(domain: DomainType) -> Dict[str, Dict]:
    """Get all relationships for a domain"""
    return relationship_registry.get_relationships_for_domain(domain)


def validate_relationship(domain: DomainType, relationship_type: str,
                         from_node_type: str, to_node_type: str) -> bool:
    """Validate relationship type for node types"""
    return relationship_registry.validate_relationship(domain, relationship_type, from_node_type, to_node_type)
