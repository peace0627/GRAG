"""
LangGraph Query Planner

This module implements the query planning agent using LangGraph.
It analyzes user queries, determines query types, and generates execution plans.
"""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage

from .schemas import (
    QueryState,
    QueryType,
    ToolType,
    PlanStep,
    PlannerOutput
)
from ..core.llm_factory import create_planner_llm


class QueryPlanner:
    """LangGraph-based query planner agent"""

    def __init__(self, llm=None):
        # Use centralized LLM configuration
        self.llm = llm or create_planner_llm()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(QueryState)

        # Define nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("classify_type", self._classify_query_type)
        workflow.add_node("generate_plan", self._generate_execution_plan)
        workflow.add_node("validate_plan", self._validate_plan)

        # Define edges
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "classify_type")
        workflow.add_edge("classify_type", "generate_plan")
        workflow.add_edge("generate_plan", "validate_plan")
        workflow.add_edge("validate_plan", END)

        return workflow.compile()

    async def plan_query(self, query: str, context: Dict[str, Any] = None) -> PlannerOutput:
        """Main entry point for query planning"""
        # Initialize state
        initial_state = QueryState(
            query_id=str(uuid.uuid4()),
            original_query=query,
            context=context or {}
        )

        # Execute planning workflow
        final_state = await self.graph.ainvoke(initial_state)

        # Handle different return types from LangGraph
        if isinstance(final_state, dict):
            # LangGraph returned a dict
            query_type = final_state.get('query_type', QueryType.FACTUAL)
            current_plan = final_state.get('current_plan', [])
            reasoning_context = final_state.get('context', {})
        else:
            # LangGraph returned a QueryState object
            query_type = final_state.query_type
            current_plan = final_state.current_plan
            reasoning_context = final_state.context

        # Convert to output format
        return PlannerOutput(
            query_type=query_type,
            execution_plan=current_plan,
            estimated_complexity=self._calculate_complexity(current_plan),
            reasoning=self._generate_reasoning(final_state),
            suggested_tools=[step.tool_type for step in current_plan]
        )

    async def _analyze_query(self, state: QueryState) -> QueryState:
        """Analyze the query for key elements and intent"""
        query = state.original_query

        # Use LLM to analyze query structure
        analysis_prompt = f"""
        Analyze this query for key elements:
        Query: {query}

        Extract:
        1. Main entities mentioned
        2. Question type (factual, analytical, visual, temporal, complex)
        3. Required information types
        4. Potential multi-modal requirements

        Return as JSON structure.
        """

        try:
            response = await self.llm.ainvoke([SystemMessage(content=analysis_prompt)])
            analysis = self._parse_llm_response(response.content)

            # Update state with analysis
            state.context.update({
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat()
            })

        except Exception as e:
            # Fallback analysis
            state.context.update({
                "analysis": {"error": str(e)},
                "fallback": True
            })

        return state

    async def _classify_query_type(self, state: QueryState) -> QueryState:
        """Classify query into predefined types"""
        query = state.original_query
        analysis = state.context.get("analysis", {})

        # Classification logic
        query_lower = query.lower()

        # Visual indicators
        visual_keywords = ["圖表", "圖片", "圖形", "chart", "graph", "image", "visual", "看起來", "顯示"]
        has_visual = any(keyword in query_lower for keyword in visual_keywords)

        # Temporal indicators
        temporal_keywords = ["時間", "日期", "月份", "年份", "季度", "when", "time", "period", "quarter"]
        has_temporal = any(keyword in query_lower for keyword in temporal_keywords)

        # Analytical indicators
        analytical_keywords = ["為什麼", "如何", "比較", "分析", "原因", "why", "how", "compare", "analysis"]
        has_analytical = any(keyword in query_lower for keyword in analytical_keywords)

        # Document structure indicators
        structure_keywords = ["架構", "結構", "章節", "目錄", "組織", "structure", "chapter", "section", "toc", "table of contents", "analyze document", "document structure"]
        has_structure = any(keyword in query_lower for keyword in structure_keywords)

        # Complex indicators
        complex_keywords = ["和", "與", "之間", "關係", "相關", "影響", "between", "relationship", "impact"]
        has_complex = any(keyword in query_lower for keyword in complex_keywords)

        # Determine query type
        if has_structure:
            query_type = QueryType.DOCUMENT_STRUCTURE
        elif has_visual:
            query_type = QueryType.VISUAL
        elif has_temporal:
            query_type = QueryType.TEMPORAL
        elif has_analytical:
            query_type = QueryType.ANALYTICAL
        elif has_complex or len(query.split()) > 20:  # Long queries often need complex reasoning
            query_type = QueryType.COMPLEX
        else:
            query_type = QueryType.FACTUAL

        state.query_type = query_type
        return state

    async def _generate_execution_plan(self, state: QueryState) -> QueryState:
        """Generate detailed execution plan based on query type"""
        query_type = state.query_type
        query = state.original_query

        plan_steps = []

        if query_type == QueryType.FACTUAL:
            # Simple factual queries - vector search + graph lookup
            plan_steps = [
                PlanStep(
                    step_id="vector_search_1",
                    description="Perform semantic search on vector database",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"query": query, "top_k": 10}
                ),
                PlanStep(
                    step_id="graph_lookup_1",
                    description="Query knowledge graph for related entities",
                    tool_type=ToolType.GRAPH_TRAVERSAL,
                    parameters={"query": query, "max_depth": 2}
                )
            ]

        elif query_type == QueryType.VISUAL:
            # Visual queries - prioritize VLM and visual search
            plan_steps = [
                PlanStep(
                    step_id="vlm_rerun_1",
                    description="Re-run VLM analysis for visual elements",
                    tool_type=ToolType.VLM_RERUN,
                    parameters={"query": query}
                ),
                PlanStep(
                    step_id="vector_search_visual",
                    description="Search visual embeddings",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"query": query, "modality": "visual", "top_k": 5}
                )
            ]

        elif query_type == QueryType.TEMPORAL:
            # Temporal queries - focus on time-based graph traversal
            plan_steps = [
                PlanStep(
                    step_id="graph_temporal_1",
                    description="Query knowledge graph with temporal constraints",
                    tool_type=ToolType.GRAPH_TRAVERSAL,
                    parameters={"query": query, "temporal": True}
                ),
                PlanStep(
                    step_id="vector_search_temporal",
                    description="Vector search with time filtering",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"query": query, "temporal_filter": True}
                )
            ]

        elif query_type == QueryType.ANALYTICAL:
            # Analytical queries - require reasoning and multiple steps
            plan_steps = [
                PlanStep(
                    step_id="vector_search_analytical",
                    description="Initial semantic search",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"query": query, "top_k": 15}
                ),
                PlanStep(
                    step_id="graph_reasoning_1",
                    description="Perform graph reasoning for relationships",
                    tool_type=ToolType.GRAPH_TRAVERSAL,
                    parameters={"query": query, "reasoning": True, "max_depth": 3}
                ),
                PlanStep(
                    step_id="evidence_validation",
                    description="Validate collected evidence",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"validate_evidence": True}
                )
            ]

        elif query_type == QueryType.DOCUMENT_STRUCTURE:
            # Document structure analysis queries
            plan_steps = [
                PlanStep(
                    step_id="structure_analysis_1",
                    description="Analyze document structure and organization",
                    tool_type=ToolType.DOCUMENT_STRUCTURE_ANALYSIS,
                    parameters={"analysis_type": "extract_structure"}
                ),
                PlanStep(
                    step_id="toc_generation",
                    description="Generate table of contents",
                    tool_type=ToolType.DOCUMENT_STRUCTURE_ANALYSIS,
                    parameters={"analysis_type": "generate_toc"}
                ),
                PlanStep(
                    step_id="key_elements_extraction",
                    description="Identify key elements and components",
                    tool_type=ToolType.DOCUMENT_STRUCTURE_ANALYSIS,
                    parameters={"analysis_type": "identify_key_elements"}
                )
            ]

        elif query_type == QueryType.COMPLEX:
            # Complex queries - full pipeline with reflection
            plan_steps = [
                PlanStep(
                    step_id="initial_vector_search",
                    description="Broad semantic search",
                    tool_type=ToolType.VECTOR_SEARCH,
                    parameters={"query": query, "top_k": 20}
                ),
                PlanStep(
                    step_id="graph_exploration",
                    description="Explore knowledge graph relationships",
                    tool_type=ToolType.GRAPH_TRAVERSAL,
                    parameters={"query": query, "explore": True, "max_depth": 4}
                ),
                PlanStep(
                    step_id="vlm_analysis",
                    description="Analyze visual components if needed",
                    tool_type=ToolType.VLM_RERUN,
                    parameters={"query": query, "conditional": True}
                ),
                PlanStep(
                    step_id="reasoning_synthesis",
                    description="Synthesize findings with reasoning",
                    tool_type=ToolType.GRAPH_TRAVERSAL,
                    parameters={"query": query, "synthesis": True}
                )
            ]

        # Set dependencies
        for i, step in enumerate(plan_steps):
            if i > 0:
                step.dependencies = [plan_steps[i-1].step_id]

        state.current_plan = plan_steps
        return state

    async def _validate_plan(self, state: QueryState) -> QueryState:
        """Validate the generated plan for completeness and feasibility"""
        plan = state.current_plan

        # Basic validation
        if not plan:
            state.needs_clarification = True
            state.clarification_questions = ["Could you please rephrase your query?"]

        # Check for tool availability (placeholder - will be enhanced)
        required_tools = set(step.tool_type for step in plan)
        available_tools = {ToolType.VECTOR_SEARCH, ToolType.GRAPH_TRAVERSAL, ToolType.VLM_RERUN, ToolType.DOCUMENT_STRUCTURE_ANALYSIS}

        if not required_tools.issubset(available_tools):
            missing_tools = required_tools - available_tools
            state.context["warnings"] = f"Some tools not available: {missing_tools}"

        return state

    def _calculate_complexity(self, plan: List[PlanStep]) -> float:
        """Calculate plan complexity score"""
        if not plan:
            return 0.0

        base_complexity = len(plan) * 0.2
        tool_complexity = sum(step.estimated_cost for step in plan) * 0.1

        return min(base_complexity + tool_complexity, 1.0)

    def _generate_reasoning(self, state) -> str:
        """Generate human-readable reasoning for the plan"""
        # Handle both dict and QueryState inputs
        if isinstance(state, dict):
            query_type = state.get('query_type', QueryType.FACTUAL)
            plan = state.get('current_plan', [])
            context = state.get('context', {})
        else:
            query_type = state.query_type
            plan = state.current_plan
            context = state.context

        reasoning_parts = [
            f"Query classified as {query_type.value if hasattr(query_type, 'value') else query_type} type.",
            f"Generated {len(plan)} execution steps."
        ]

        if context.get("warnings"):
            reasoning_parts.append(f"Warnings: {context['warnings']}")

        return " ".join(reasoning_parts)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Simple JSON extraction (in production, use more robust parsing)
            import json
            return json.loads(response)
        except:
            return {"raw_response": response, "parsing_failed": True}
