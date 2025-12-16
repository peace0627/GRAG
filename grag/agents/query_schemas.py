"""
Structured Query Schemas for LLM-driven query parsing

This module defines the JSON schemas that LLMs use to convert natural language
queries into structured, programmable representations.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class QueryType(str, Enum):
    """Enhanced query type classification"""
    FACTUAL = "factual"          # What, When, Where questions
    ANALYTICAL = "analytical"    # Why, How, Compare questions
    VISUAL = "visual"           # Questions requiring visual evidence
    TEMPORAL = "temporal"       # Time-based questions
    COMPLEX = "complex"         # Multi-step reasoning required
    CAUSAL = "causal"           # Cause-effect analysis
    COMPARATIVE = "comparative"  # Comparison between entities/metrics
    PREDICTIVE = "predictive"   # Future predictions or forecasting


class PrimaryAction(str, Enum):
    """Primary actions that queries can request"""
    FIND = "find"
    ANALYZE = "analyze"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    PREDICT = "predict"
    EXPLAIN = "explain"
    CALCULATE = "calculate"
    VISUALIZE = "visualize"


class QueryIntent(BaseModel):
    """Core intent of the query"""
    primary_action: PrimaryAction = Field(..., description="Main action requested")
    target_metric: Optional[str] = Field(None, description="Target metric (sales, revenue, etc.)")
    target_entities: List[str] = Field(default_factory=list, description="Target entities mentioned")
    group_by: Optional[str] = Field(None, description="Grouping dimension (month, region, etc.)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filtering conditions")
    sort_by: Optional[str] = Field(None, description="Sort criteria")
    limit: Optional[int] = Field(None, description="Result limit")
    visualization_preferred: bool = Field(default=False, description="Whether visualization is preferred")
    calculation_needed: bool = Field(default=False, description="Whether calculation is required")


class QueryConstraints(BaseModel):
    """Constraints and requirements for the query"""
    must_include: List[str] = Field(default_factory=list, description="Must-include elements")
    preferred_sources: List[str] = Field(default_factory=list, description="Preferred source types")
    exclude_sources: List[str] = Field(default_factory=list, description="Sources to exclude")
    time_scope: Optional[str] = Field(None, description="Time scope limitation")
    data_freshness: Optional[str] = Field(None, description="Data freshness requirement")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence required")


class ReasoningRequirements(BaseModel):
    """Reasoning complexity and requirements"""
    needs_causal_analysis: bool = Field(default=False, description="Requires cause-effect analysis")
    needs_trend_analysis: bool = Field(default=False, description="Requires trend analysis")
    needs_comparison: bool = Field(default=False, description="Requires comparison")
    needs_correlation: bool = Field(default=False, description="Requires correlation analysis")
    needs_statistical_analysis: bool = Field(default=False, description="Requires statistical methods")
    complexity_level: str = Field(default="medium", description="low|medium|high")
    reasoning_depth: int = Field(default=1, ge=1, le=5, description="Reasoning depth required")
    domain_expertise: List[str] = Field(default_factory=list, description="Required domain knowledge")


class ResponseFormat(BaseModel):
    """Preferred response format and style"""
    include_evidence: bool = Field(default=True, description="Include evidence citations")
    include_confidence: bool = Field(default=True, description="Include confidence scores")
    include_methodology: bool = Field(default=False, description="Include analysis methodology")
    preferred_style: str = Field(default="balanced", description="concise|detailed|balanced|technical")
    max_length: Optional[int] = Field(None, description="Maximum response length")
    format_type: str = Field(default="narrative", description="narrative|bullet_points|table|mixed")
    language_preference: Optional[str] = Field(None, description="Preferred response language")


class StructuredQuery(BaseModel):
    """Complete structured query representation"""
    query_id: str = Field(..., description="Unique query identifier")
    original_query: str = Field(..., description="Original natural language query")
    language: str = Field(..., description="Detected query language")
    query_type: QueryType = Field(..., description="Classified query type")
    intent: QueryIntent = Field(..., description="Core query intent")
    constraints: QueryConstraints = Field(..., description="Query constraints")
    reasoning_requirements: ReasoningRequirements = Field(..., description="Reasoning requirements")
    response_format: ResponseFormat = Field(..., description="Response format preferences")

    # Metadata
    parsing_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="LLM parsing confidence")
    parsing_model: str = Field(default="unknown", description="Model used for parsing")
    parsing_timestamp: str = Field(..., description="Parsing timestamp")
    version: str = Field(default="1.0", description="Schema version")

    # Optional extensions
    domain_context: Dict[str, Any] = Field(default_factory=dict, description="Domain-specific context")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User-specific preferences")


class QueryParsingResult(BaseModel):
    """Result of query parsing operation"""
    success: bool = Field(..., description="Whether parsing was successful")
    structured_query: Optional[StructuredQuery] = Field(None, description="Parsed structured query")
    error_message: Optional[str] = Field(None, description="Error message if parsing failed")
    fallback_type: Optional[str] = Field(None, description="Fallback parsing method used")
    processing_time: float = Field(..., description="Processing time in seconds")
    raw_llm_response: Optional[str] = Field(None, description="Raw LLM response for debugging")


# Tool and Workflow Schemas for LangChain integration

class ToolSpecification(BaseModel):
    """Specification for a LangChain Tool derived from JSON"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    required_inputs: List[str] = Field(default_factory=list, description="Required input parameters")
    output_type: str = Field(..., description="Expected output type")
    execution_timeout: int = Field(default=30, description="Timeout in seconds")


class WorkflowNode(BaseModel):
    """Node in a LangGraph workflow"""
    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Node type (tool|condition|merge|etc)")
    tool_spec: Optional[ToolSpecification] = Field(None, description="Tool specification if applicable")
    condition: Optional[str] = Field(None, description="Condition expression if conditional node")
    inputs: List[str] = Field(default_factory=list, description="Input node IDs")
    outputs: List[str] = Field(default_factory=list, description="Output node IDs")
    parallel_group: Optional[str] = Field(None, description="Parallel execution group")


class WorkflowSpecification(BaseModel):
    """Complete workflow specification for LangGraph"""
    workflow_id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="Workflow nodes")
    entry_points: List[str] = Field(default_factory=list, description="Entry point node IDs")
    exit_points: List[str] = Field(default_factory=list, description="Exit point node IDs")
    max_parallelism: int = Field(default=3, description="Maximum parallel execution")
    timeout: int = Field(default=300, description="Workflow timeout in seconds")


# Enhanced Agent Configuration

class AgentConfiguration(BaseModel):
    """Configuration for LangChain Agent based on JSON query"""
    agent_type: str = Field(default="react", description="Agent type (react|structured|conversational)")
    tools: List[ToolSpecification] = Field(default_factory=list, description="Available tools")
    memory_type: str = Field(default="buffer", description="Memory type (buffer|summary|conversation)")
    max_iterations: int = Field(default=5, description="Maximum reasoning iterations")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="LLM temperature")
    custom_prompts: Dict[str, str] = Field(default_factory=dict, description="Custom prompt templates")
    reasoning_style: str = Field(default="balanced", description="Reasoning style (concise|detailed|balanced)")


# Monitoring and Metrics

class QueryExecutionMetrics(BaseModel):
    """Metrics collected during query execution"""
    query_id: str = Field(..., description="Query identifier")
    parsing_time: float = Field(..., description="Query parsing time")
    planning_time: float = Field(..., description="Query planning time")
    execution_time: float = Field(..., description="Total execution time")
    tool_calls: int = Field(default=0, description="Number of tool calls made")
    llm_calls: int = Field(default=0, description="Number of LLM calls made")
    tokens_used: int = Field(default=0, description="Total tokens used")
    cache_hits: int = Field(default=0, description="Cache hits")
    errors_count: int = Field(default=0, description="Number of errors encountered")
    final_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Final answer confidence")
