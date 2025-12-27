"""
醫材財報分析系統 - Pydantic Schema 定義

本模組定義了系統中所有數據結構的 Pydantic 模型，
包括文檔解析、實體提取、查詢請求等。
"""

# Document schemas
from .document import (
    DocumentChunk,
    DocumentMetadata,
    DocumentType,
    VisualAsset,
    VisualAssetStatus
)

# Entity schemas
from .entity import (
    MedicalEntity,
    EntityRelation,
    EntityResolution,
    EntityType,
    RelationType
)

# Query schemas
from .query import (
    QueryRequest,
    QueryIntent,
    QueryResponse,
    Evidence,
    EvidenceType
)

# Vision schemas
from .vision import (
    VisionRequest,
    VisionResponse,
    VisualFact,
    VisionTaskType
)

__all__ = [
    # Document schemas
    "DocumentChunk",
    "DocumentMetadata",
    "DocumentType",
    "VisualAsset",
    "VisualAssetStatus",

    # Entity schemas
    "MedicalEntity",
    "EntityRelation",
    "EntityResolution",
    "EntityType",
    "RelationType",

    # Query schemas
    "QueryRequest",
    "QueryIntent",
    "QueryResponse",
    "Evidence",
    "EvidenceType",

    # Vision schemas
    "VisionRequest",
    "VisionResponse",
    "VisualFact",
    "VisionTaskType",
]
