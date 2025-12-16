"""
Unified Knowledge Representation Schemas

This module defines unified schemas for representing knowledge units,
evidence, and relationships across the entire GraphRAG system.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum


class Modality(str, Enum):
    """Knowledge modality types"""
    TEXT = "text"
    VISUAL = "visual"
    RELATIONAL = "relational"
    TEMPORAL = "temporal"
    HYBRID = "hybrid"


class SourceType(str, Enum):
    """Data source types"""
    NEO4J = "neo4j"
    SUPABASE = "supabase"
    HYBRID = "hybrid"
    EXTERNAL = "external"


class ExtractionMethod(str, Enum):
    """Knowledge extraction methods"""
    NER = "ner"                    # Named Entity Recognition
    LLM = "llm"                    # Large Language Model
    RULE_BASED = "rule_based"      # Rule-based extraction
    VLM = "vlm"                    # Vision-Language Model
    MANUAL = "manual"              # Manual annotation


class ConfidenceLevel(str, Enum):
    """Confidence level classifications"""
    VERY_HIGH = "very_high"    # > 0.9
    HIGH = "high"             # 0.8-0.9
    MEDIUM = "medium"         # 0.6-0.8
    LOW = "low"               # 0.4-0.6
    VERY_LOW = "very_low"     # < 0.4


class TraceabilityInfo(BaseModel):
    """Complete traceability information for knowledge units"""

    # Source identification
    source_type: SourceType = Field(..., description="Type of data source")
    source_id: UUID = Field(..., description="Unique identifier in source system")

    # Document/file level traceability
    document_id: UUID = Field(..., description="Document that contains this knowledge")
    document_path: str = Field(..., description="File path of source document")
    page_number: Optional[int] = Field(None, description="Page number in document")
    chunk_order: Optional[int] = Field(None, description="Order within chunked content")

    # Processing traceability
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="When this was processed")
    processing_pipeline: List[str] = Field(default_factory=list, description="Processing steps applied")
    extraction_method: ExtractionMethod = Field(..., description="How this knowledge was extracted")

    # Quality and validation
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall quality score")
    validation_status: Literal["unvalidated", "validated", "rejected"] = Field(default="unvalidated")
    validator_id: Optional[str] = Field(None, description="Who validated this knowledge")

    # Version control
    version: str = Field(default="1.0", description="Knowledge unit version")
    last_modified: datetime = Field(default_factory=datetime.now)

    # Additional metadata
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional processing info")


class Relationship(BaseModel):
    """Relationship between knowledge units"""

    relationship_id: UUID = Field(default_factory=uuid4, description="Unique relationship identifier")
    source_unit_id: UUID = Field(..., description="Source knowledge unit ID")
    target_unit_id: UUID = Field(..., description="Target knowledge unit ID")

    relationship_type: str = Field(..., description="Type of relationship (e.g., 'related_to', 'part_of')")
    direction: Literal["directed", "undirected", "bidirectional"] = Field(default="directed")

    # Relationship properties
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship confidence")
    weight: float = Field(default=1.0, description="Relationship strength/weight")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional relationship properties")

    # Traceability
    source: str = Field(..., description="How this relationship was established")
    created_at: datetime = Field(default_factory=datetime.now)

    # Optional temporal aspects
    valid_from: Optional[datetime] = Field(None, description="When relationship becomes valid")
    valid_until: Optional[datetime] = Field(None, description="When relationship expires")


class KnowledgeUnit(BaseModel):
    """Unified knowledge unit representation"""

    # Core identification
    id: UUID = Field(default_factory=uuid4, description="Unique knowledge unit identifier")
    knowledge_area_id: str = Field(..., description="Knowledge area this belongs to")

    # Content
    content: str = Field(..., description="The actual knowledge content")
    summary: Optional[str] = Field(None, description="Brief summary of the content")

    # Classification
    modality: Modality = Field(..., description="Knowledge modality")
    content_type: str = Field(..., description="Specific content type (e.g., 'entity', 'event', 'fact')")
    domain_tags: List[str] = Field(default_factory=list, description="Domain-specific tags")

    # Source information
    source: SourceType = Field(..., description="Primary data source")
    traceability: TraceabilityInfo = Field(..., description="Complete traceability information")

    # Relationships
    relationships: List[Relationship] = Field(default_factory=list, description="Relationships to other units")

    # Vector representation (optional, for vector-based operations)
    embeddings: Optional[List[float]] = Field(None, description="Vector embeddings if applicable")
    embedding_model: Optional[str] = Field(None, description="Model used for embeddings")

    # Quality and confidence
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall confidence score")
    confidence_breakdown: Dict[str, float] = Field(default_factory=dict, description="Confidence by aspect")

    # Temporal aspects
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    valid_from: Optional[datetime] = Field(None, description="When this knowledge becomes valid")
    valid_until: Optional[datetime] = Field(None, description="When this knowledge expires")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible metadata")

    def get_confidence_level(self) -> ConfidenceLevel:
        """Get confidence level classification"""
        if self.confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def add_relationship(self, target_unit_id: UUID, relationship_type: str,
                        confidence: float = 1.0, **properties) -> None:
        """Add a relationship to another knowledge unit"""
        relationship = Relationship(
            source_unit_id=self.id,
            target_unit_id=target_unit_id,
            relationship_type=relationship_type,
            confidence=confidence,
            properties=properties
        )
        self.relationships.append(relationship)

    def update_confidence(self, new_confidence: float, aspect: str = "overall") -> None:
        """Update confidence score for specific aspect"""
        self.confidence_breakdown[aspect] = new_confidence

        # Recalculate overall confidence as weighted average
        if self.confidence_breakdown:
            self.confidence = sum(self.confidence_breakdown.values()) / len(self.confidence_breakdown)
        else:
            self.confidence = new_confidence

        self.updated_at = datetime.now()


class UnifiedEvidence(BaseModel):
    """Unified evidence structure for query responses"""

    evidence_id: str = Field(..., description="Unique evidence identifier")
    source_type: SourceType = Field(..., description="Type of evidence source")
    modality: Modality = Field(..., description="Evidence modality")

    # Content
    content: str = Field(..., description="Evidence content")
    summary: Optional[str] = Field(None, description="Brief evidence summary")

    # Quality metrics
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Evidence confidence")
    relevance_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Relevance to query")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall quality")

    # Traceability
    knowledge_unit_id: Optional[UUID] = Field(None, description="Corresponding knowledge unit")
    traceability: Optional[TraceabilityInfo] = Field(None, description="Source traceability")

    # Relationships and context
    related_units: List[UUID] = Field(default_factory=list, description="Related knowledge unit IDs")
    context_snippet: Optional[str] = Field(None, description="Surrounding context")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.now)

    def get_combined_score(self) -> float:
        """Calculate combined relevance and quality score"""
        return (self.relevance_score * 0.7) + (self.quality_score * 0.3)

    def to_knowledge_unit(self) -> KnowledgeUnit:
        """Convert evidence to knowledge unit"""
        if not self.traceability:
            raise ValueError("Cannot convert evidence without traceability info")

        return KnowledgeUnit(
            knowledge_area_id=self.metadata.get("area_id", "default"),
            content=self.content,
            summary=self.summary,
            modality=self.modality,
            content_type="evidence",
            source=self.source_type,
            traceability=self.traceability,
            confidence=self.confidence,
            metadata={
                **self.metadata,
                "original_evidence_id": self.evidence_id,
                "converted_from_evidence": True
            }
        )


class KnowledgeGraph(BaseModel):
    """Knowledge graph representation"""

    graph_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Graph name")
    description: Optional[str] = Field(None, description="Graph description")

    # Graph structure
    nodes: List[KnowledgeUnit] = Field(default_factory=list, description="Knowledge units in graph")
    edges: List[Relationship] = Field(default_factory=list, description="Relationships between units")

    # Metadata
    knowledge_area_id: str = Field(..., description="Associated knowledge area")
    version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_node(self, unit: KnowledgeUnit) -> None:
        """Add knowledge unit to graph"""
        self.nodes.append(unit)
        self.updated_at = datetime.now()

    def add_edge(self, relationship: Relationship) -> None:
        """Add relationship to graph"""
        self.edges.append(relationship)
        self.updated_at = datetime.now()

    def get_node_by_id(self, unit_id: UUID) -> Optional[KnowledgeUnit]:
        """Get knowledge unit by ID"""
        return next((node for node in self.nodes if node.id == unit_id), None)

    def get_neighbors(self, unit_id: UUID) -> List[KnowledgeUnit]:
        """Get neighboring nodes"""
        neighbor_ids = set()

        # Find all relationships involving this unit
        for edge in self.edges:
            if edge.source_unit_id == unit_id:
                neighbor_ids.add(edge.target_unit_id)
            elif edge.target_unit_id == unit_id:
                neighbor_ids.add(edge.source_unit_id)

        # Return corresponding nodes
        return [node for node in self.nodes if node.id in neighbor_ids]


# Utility functions for schema conversion

def neo4j_chunk_to_knowledge_unit(chunk_data: Dict[str, Any],
                                 traceability: TraceabilityInfo) -> KnowledgeUnit:
    """Convert Neo4j chunk data to KnowledgeUnit"""
    return KnowledgeUnit(
        knowledge_area_id=chunk_data.get("area_id", "default"),
        content=chunk_data.get("text", ""),
        modality=Modality.TEXT,
        content_type="chunk",
        source=SourceType.NEO4J,
        traceability=traceability,
        confidence=chunk_data.get("confidence", 1.0),
        metadata=chunk_data
    )


def supabase_vector_to_knowledge_unit(vector_data: Dict[str, Any],
                                     traceability: TraceabilityInfo) -> KnowledgeUnit:
    """Convert Supabase vector data to KnowledgeUnit"""
    modality_map = {
        "chunk": Modality.TEXT,
        "vlm_region": Modality.VISUAL
    }

    return KnowledgeUnit(
        knowledge_area_id=vector_data.get("area_id", "default"),
        content=vector_data.get("content_preview", ""),
        modality=modality_map.get(vector_data.get("type", "chunk"), Modality.TEXT),
        content_type=vector_data.get("type", "chunk"),
        source=SourceType.SUPABASE,
        traceability=traceability,
        embeddings=vector_data.get("embedding"),
        confidence=vector_data.get("similarity_score", 1.0),
        metadata=vector_data
    )


def evidence_to_response_format(evidence: UnifiedEvidence) -> Dict[str, Any]:
    """Convert UnifiedEvidence to API response format"""
    return {
        "evidence_id": evidence.evidence_id,
        "source_type": evidence.source_type.value,
        "modality": evidence.modality.value,
        "content": evidence.content,
        "summary": evidence.summary,
        "confidence": evidence.confidence,
        "relevance_score": evidence.relevance_score,
        "quality_score": evidence.quality_score,
        "traceability": {
            "document_id": str(evidence.traceability.document_id) if evidence.traceability else None,
            "page_number": evidence.traceability.page_number if evidence.traceability else None,
            "extraction_method": evidence.traceability.extraction_method.value if evidence.traceability else None
        } if evidence.traceability else None,
        "metadata": evidence.metadata
    }
