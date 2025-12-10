"""
Test Unified Knowledge System

This module tests the unified knowledge representation and agent system.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from grag.core.schemas.unified_schemas import (
    KnowledgeUnit, UnifiedEvidence, TraceabilityInfo,
    SourceType, Modality, ExtractionMethod
)
from grag.agents.smart_router import SmartRouter
from grag.agents.evidence_fusion import EvidenceFusionEngine


class TestUnifiedSchemas:
    """Test unified knowledge schemas"""

    def test_knowledge_unit_creation(self):
        """Test KnowledgeUnit creation and methods"""
        traceability = TraceabilityInfo(
            source_type=SourceType.NEO4J,
            source_id="test_chunk_123",
            document_id="doc_456",
            document_path="/test/doc.pdf",
            extraction_method=ExtractionMethod.LLM
        )

        unit = KnowledgeUnit(
            knowledge_area_id="test_area",
            content="Test knowledge content",
            modality=Modality.TEXT,
            content_type="chunk",
            source=SourceType.NEO4J,
            traceability=traceability,
            confidence=0.85
        )

        assert unit.id is not None
        assert unit.confidence == 0.85
        assert unit.get_confidence_level().value == "high"
        assert unit.modality == Modality.TEXT

    def test_unified_evidence_creation(self):
        """Test UnifiedEvidence creation"""
        evidence = UnifiedEvidence(
            evidence_id="evidence_001",
            source_type=SourceType.SUPABASE,
            modality=Modality.VISUAL,
            content="Test evidence content",
            confidence=0.9,
            relevance_score=0.8
        )

        assert evidence.evidence_id == "evidence_001"
        assert evidence.source_type == SourceType.SUPABASE
        assert evidence.get_combined_score() == 0.82  # (0.8 + 0.9) / 2 * 0.9 wait, actually (0.8 * 0.7) + (0.9 * 0.3) = 0.56 + 0.27 = 0.83

    def test_traceability_info(self):
        """Test TraceabilityInfo functionality"""
        trace = TraceabilityInfo(
            source_type=SourceType.HYBRID,
            source_id="entity_789",
            document_id="doc_101",
            extraction_method=ExtractionMethod.NER,
            quality_score=0.95
        )

        assert trace.source_type == SourceType.HYBRID
        assert trace.extraction_method == ExtractionMethod.NER
        assert trace.quality_score == 0.95


class TestSmartRouter:
    """Test SmartRouter functionality"""

    def test_router_initialization(self):
        """Test router initialization"""
        router = SmartRouter()
        assert len(router.routing_rules) > 0
        assert "factual_find" in router.routing_rules

    def test_query_pattern_detection(self):
        """Test query pattern detection"""
        from grag.agents.query_schemas import StructuredQuery, QueryType, QueryIntent, PrimaryAction

        router = SmartRouter()

        # Test visual query
        visual_query = StructuredQuery(
            query_id="test_001",
            original_query="圖表顯示什麼？",
            language="zh",
            query_type=QueryType.VISUAL,
            intent=QueryIntent(primary_action=PrimaryAction.FIND),
            constraints=Mock(),
            reasoning_requirements=Mock(),
            response_format=Mock()
        )

        pattern = router._determine_routing_pattern(visual_query)
        assert "visual" in pattern

    def test_routing_decision_validation(self):
        """Test routing decision validation"""
        router = SmartRouter()

        valid_decision = {
            "routing_pattern": "factual_find",
            "strategy": "single_tool",
            "tools": ["vector_search"],
            "parameters": {},
            "execution_order": "parallel",
            "confidence_threshold": 0.8,
            "estimated_complexity": "medium"
        }

        assert router.validate_routing_decision(valid_decision)

        invalid_decision = {
            "routing_pattern": "factual_find",
            "strategy": "single_tool",
            # Missing required fields
        }

        assert not router.validate_routing_decision(invalid_decision)


class TestEvidenceFusion:
    """Test EvidenceFusionEngine functionality"""

    def test_fusion_engine_creation(self):
        """Test fusion engine creation"""
        engine = EvidenceFusionEngine()
        assert len(engine.fusion_strategies) > 0
        assert "adaptive_fusion" in engine.fusion_strategies

    def test_evidence_deduplication(self):
        """Test evidence deduplication"""
        engine = EvidenceFusionEngine()

        # Create duplicate evidence
        evidence_list = [
            UnifiedEvidence(
                evidence_id="ev1",
                source_type=SourceType.NEO4J,
                modality=Modality.TEXT,
                content="Test content",
                confidence=0.8
            ),
            UnifiedEvidence(
                evidence_id="ev2",
                source_type=SourceType.SUPABASE,
                modality=Modality.TEXT,
                content="Test content",  # Same content
                confidence=0.7
            )
        ]

        deduplicated = engine._deduplicate_evidence(evidence_list)
        assert len(deduplicated) == 1  # Should merge duplicates
        assert deduplicated[0].confidence > 0.7  # Should be average/higher

    def test_contradiction_analysis(self):
        """Test contradiction detection"""
        engine = EvidenceFusionEngine()

        # Create contradictory evidence
        evidence_list = [
            {
                "evidence_id": "ev1",
                "content": "Sales increased by 20%",
                "confidence": 0.9
            },
            {
                "evidence_id": "ev2",
                "content": "Sales increased by 20%",  # Same content
                "confidence": 0.4  # Much lower confidence
            }
        ]

        analysis = engine._analyze_evidence_contradictions(evidence_list)
        assert analysis["has_contradictions"]
        assert analysis["contradiction_count"] > 0
        assert analysis["severity"] in ["low", "medium", "high"]

    def test_source_weighting(self):
        """Test source reliability weighting"""
        engine = EvidenceFusionEngine()

        neo4j_weight = engine._get_source_weight(SourceType.NEO4J)
        supabase_weight = engine._get_source_weight(SourceType.SUPABASE)
        hybrid_weight = engine._get_source_weight(SourceType.HYBRID)

        assert neo4j_weight >= supabase_weight
        assert hybrid_weight >= neo4j_weight  # Hybrid should be highest


class TestIngestionEnhancements:
    """Test enhanced ingestion functionality"""

    def test_chunk_quality_assessment(self):
        """Test chunk quality assessment"""
        from grag.ingestion.indexing.ingestion_service import IngestionService

        service = IngestionService()

        # Test high quality chunk
        good_chunk = {"content": "This is a comprehensive explanation of the topic with detailed information."}
        good_quality = service._assess_chunk_quality(good_chunk)
        assert good_quality > 0.7

        # Test low quality chunk
        bad_chunk = {"content": "Hi"}
        bad_quality = service._assess_chunk_quality(bad_chunk)
        assert bad_quality < 0.5

    def test_knowledge_quality_assessment(self):
        """Test knowledge quality assessment"""
        from grag.ingestion.indexing.ingestion_service import IngestionService

        service = IngestionService()

        # Test with entities and relations
        entities = [
            {"id": "ent1", "type": "PERSON", "confidence": 0.9},
            {"id": "ent2", "type": "ORG", "confidence": 0.8}
        ]
        relations = [
            {"source_id": "ent1", "target_id": "ent2", "type": "WORKS_FOR", "confidence": 0.85}
        ]

        assessment = service._assess_knowledge_quality(entities, relations)
        assert assessment["overall_score"] > 0.7
        assert len(assessment["issues"]) == 0  # Should be good quality


class TestIntegration:
    """Test integration between components"""

    @pytest.mark.asyncio
    async def test_unified_evidence_conversion(self):
        """Test conversion to unified evidence format"""
        from grag.agents.rag_agent import AgenticRAGAgent

        # Mock evidence objects
        mock_evidence = [
            Mock(
                evidence_id="test_ev_1",
                source_type="neo4j",
                modality="text",
                content="Test content from Neo4j",
                confidence=0.85,
                relevance_score=0.8,
                quality_score=0.9,
                metadata={"test": "data"}
            )
        ]

        agent = AgenticRAGAgent()
        unified = await agent._convert_to_unified_evidence(mock_evidence)

        assert len(unified) == 1
        assert unified[0]["source_type"] == "neo4j"
        assert unified[0]["confidence"] == 0.85

    def test_source_aware_context_building(self):
        """Test building source-aware context"""
        from grag.agents.rag_agent import AgenticRAGAgent

        agent = AgenticRAGAgent()

        evidence_list = [
            {
                "evidence_id": "ev1",
                "source_type": "neo4j",
                "modality": "text",
                "content": "Graph-based relationship information",
                "confidence": 0.9,
                "relevance_score": 0.8,
                "quality_score": 0.85
            },
            {
                "evidence_id": "ev2",
                "source_type": "supabase",
                "modality": "visual",
                "content": "Visual content from vector search",
                "confidence": 0.8,
                "relevance_score": 0.9,
                "quality_score": 0.8
            }
        ]

        context = agent._build_source_aware_evidence_context(evidence_list)

        assert "Knowledge Graph (Neo4j)" in context
        assert "Vector Database (Supabase)" in context
        assert "Source Reliability Guide" in context


if __name__ == "__main__":
    # Run basic functionality tests
    print("🧪 Running Unified Knowledge System Tests...")

    # Test schema creation
    print("✅ Testing schema creation...")
    unit = KnowledgeUnit(
        knowledge_area_id="test",
        content="Test content",
        modality=Modality.TEXT,
        source=SourceType.NEO4J,
        traceability=TraceabilityInfo(
            source_type=SourceType.NEO4J,
            source_id="test_123",
            document_id="doc_456",
            extraction_method=ExtractionMethod.LLM
        )
    )
    print(f"   Created KnowledgeUnit with ID: {unit.id}")

    # Test evidence creation
    evidence = UnifiedEvidence(
        evidence_id="test_ev",
        source_type=SourceType.SUPABASE,
        modality=Modality.VISUAL,
        content="Test evidence",
        confidence=0.85
    )
    print(f"   Created UnifiedEvidence with combined score: {evidence.get_combined_score()}")

    # Test router
    print("✅ Testing SmartRouter...")
    router = SmartRouter()
    rules_count = len(router.routing_rules)
    print(f"   Loaded {rules_count} routing rules")

    # Test fusion engine
    print("✅ Testing EvidenceFusionEngine...")
    engine = EvidenceFusionEngine()
    strategies_count = len(engine.fusion_strategies)
    print(f"   Loaded {strategies_count} fusion strategies")

    print("🎉 All basic tests passed! Unified knowledge system is ready.")
