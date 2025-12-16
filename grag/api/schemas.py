"""
API Schemas for GraphRAG REST API

Defines Pydantic models for all API endpoints including RAG queries,
document management, and system operations.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class QueryType(str, Enum):
    """Query type enumeration matching agent schemas"""
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    VISUAL = "visual"
    TEMPORAL = "temporal"
    COMPLEX = "complex"


class QueryRequest(BaseModel):
    """Request model for RAG queries"""
    query: str = Field(..., description="User query string", min_length=1, max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for the query")
    query_type: Optional[QueryType] = Field(default=None, description="Force specific query type")
    max_evidence: Optional[int] = Field(default=10, description="Maximum evidence items to return", ge=1, le=50)
    include_planning: Optional[bool] = Field(default=False, description="Include planning details in response")


class EvidenceResponse(BaseModel):
    """Evidence item in API responses"""
    evidence_id: str
    source_type: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    relevance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    traceability: Optional[Dict[str, Any]] = Field(default=None)


class PlanningInfo(BaseModel):
    """Planning information from agent"""
    estimated_complexity: str
    execution_plan_steps: int
    suggested_tools: List[str]


class ReflectionInfo(BaseModel):
    """Reflection information from agent"""
    context_sufficient: bool
    gaps_identified: List[str]
    confidence_assessment: Dict[str, Any]


class QueryResponse(BaseModel):
    """Response model for RAG queries"""
    query_id: str
    original_query: str
    query_type: str
    final_answer: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_count: int
    execution_time: float
    needs_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)
    planning_info: Optional[PlanningInfo] = None
    evidence: List[EvidenceResponse] = Field(default_factory=list)
    reflection: Optional[ReflectionInfo] = None
    success: bool = True
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class QueryHistoryItem(BaseModel):
    """Query history item"""
    query_id: str
    timestamp: datetime
    query: str
    query_type: str
    confidence_score: float
    execution_time: float
    success: bool


class QueryHistoryResponse(BaseModel):
    """Response for query history"""
    queries: List[QueryHistoryItem]
    total: int
    pagination: Dict[str, Any]


class EvidenceDetailRequest(BaseModel):
    """Request for detailed evidence information"""
    query_id: str
    evidence_ids: List[str]


class EvidenceDetailResponse(BaseModel):
    """Detailed evidence response"""
    query_id: str
    evidence: List[EvidenceResponse]
    total_evidence: int


class SystemStatusResponse(BaseModel):
    """System status response"""
    status: str
    timestamp: str
    overall_health: str
    services: Dict[str, Any]
    agents: Optional[Dict[str, Any]] = None


class DocumentInfo(BaseModel):
    """Document information"""
    document_id: str
    title: str
    source_path: str
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    vector_count: int = 0
    processing_method: Optional[str] = Field(default=None, description="Document processing method (VLM, OCR, Text)")
    processing_quality: Optional[str] = Field(default=None, description="Processing quality assessment")
    content_quality_score: Optional[float] = Field(default=None, description="Content quality score (0.0-1.0)")
    vlm_provider: Optional[str] = Field(default=None, description="VLM provider used")
    vlm_success: Optional[bool] = Field(default=None, description="Whether VLM processing succeeded")
    total_characters: Optional[int] = Field(default=None, description="Total characters extracted")


class DocumentListResponse(BaseModel):
    """Document list response"""
    documents: List[DocumentInfo]
    pagination: Dict[str, Any]


class UploadResponse(BaseModel):
    """File upload response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    document_id: Optional[str] = None
    processing_time: Optional[float] = None


class BatchUploadResponse(BaseModel):
    """Batch upload response"""
    success: bool
    message: str
    results: List[Dict[str, Any]]
    statistics: Dict[str, int]


class DeleteResponse(BaseModel):
    """Delete operation response"""
    success: bool
    message: str
    deleted_count: Optional[int] = None
    failed_deletions: Optional[List[str]] = None


class StatisticsResponse(BaseModel):
    """System statistics response"""
    total_documents: int
    total_chunks: int
    total_vectors: int
    total_entities: int
    total_events: int
    database_sizes: Dict[str, Any]
    last_updated: datetime


class SearchRequest(BaseModel):
    """Search request (legacy endpoint)"""
    query: str
    limit: Optional[int] = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Search result item"""
    document_id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    results: List[SearchResult]
    total_results: int
    execution_time: float
    metadata: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
