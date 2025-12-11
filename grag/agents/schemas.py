"""
Pydantic schemas for Agentic RAG system
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Query type classification"""
    FACTUAL = "factual"          # What, When, Where questions
    ANALYTICAL = "analytical"    # Why, How, Compare questions
    VISUAL = "visual"           # Questions requiring visual evidence
    TEMPORAL = "temporal"       # Time-based questions
    COMPLEX = "complex"         # Multi-step reasoning required


class ToolType(str, Enum):
    """Available tool types"""
    VECTOR_SEARCH = "vector_search"
    GRAPH_TRAVERSAL = "graph_traversal"
    VLM_RERUN = "vlm_rerun"
    OCR_PROCESS = "ocr_process"
    TEXT_CHUNK = "text_chunk"


class Evidence(BaseModel):
    """Evidence object for traceability"""
    evidence_id: str = Field(..., description="Unique evidence identifier")
    source_type: str = Field(..., description="neo4j, pgvector, vlm")
    content: str = Field(..., description="Evidence content or snippet")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    source_document: Optional[str] = Field(None, description="Source document ID")
    page_number: Optional[int] = Field(None, description="Page number if applicable")


class PlanStep(BaseModel):
    """Individual step in query execution plan"""
    step_id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Human-readable description")
    tool_type: ToolType = Field(..., description="Tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    dependencies: List[str] = Field(default_factory=list, description="Dependent step IDs")
    estimated_cost: float = Field(default=1.0, description="Computational cost estimate")


class AgentAction(BaseModel):
    """Action taken by an agent"""
    action_type: str = Field(..., description="Type of action")
    tool_name: Optional[str] = Field(None, description="Tool name if applicable")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    reasoning: str = Field(..., description="Reasoning behind the action")
    timestamp: str = Field(..., description="Action timestamp")


class AgentResult(BaseModel):
    """Result from agent execution"""
    success: bool = Field(..., description="Whether the action succeeded")
    data: Any = Field(None, description="Result data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    evidence: List[Evidence] = Field(default_factory=list, description="Collected evidence")
    execution_time: float = Field(..., description="Execution time in seconds")


class QueryState(BaseModel):
    """State maintained throughout query execution"""
    query_id: str = Field(..., description="Unique query identifier")
    original_query: str = Field(..., description="Original user query")
    query_type: QueryType = Field(default=QueryType.FACTUAL, description="Classified query type")
    current_plan: List[PlanStep] = Field(default_factory=list, description="Current execution plan")
    executed_steps: List[str] = Field(default_factory=list, description="Completed step IDs")
    collected_evidence: List[Evidence] = Field(default_factory=list, description="All collected evidence")
    intermediate_results: Dict[str, Any] = Field(default_factory=dict, description="Step results")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    final_answer: Optional[str] = Field(None, description="Final generated answer")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence")
    needs_clarification: bool = Field(default=False, description="Whether query needs clarification")
    clarification_questions: List[str] = Field(default_factory=list, description="Questions for clarification")


class PlannerOutput(BaseModel):
    """Output from query planner"""
    query_type: QueryType
    execution_plan: List[PlanStep]
    estimated_complexity: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    suggested_tools: List[ToolType]


class RetrievalResult(BaseModel):
    """Result from retrieval operations"""
    query: str
    vector_results: List[Dict[str, Any]] = Field(default_factory=list)
    graph_results: List[Dict[str, Any]] = Field(default_factory=list)
    merged_results: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: float


class ReasoningResult(BaseModel):
    """Result from reasoning operations"""
    reasoning_path: List[str] = Field(default_factory=list)
    inferred_relations: List[Dict[str, Any]] = Field(default_factory=list)
    subgraph_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float
    reasoning_trace: str
