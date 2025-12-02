"""
Tool Agent

This module implements the tool agent that handles dynamic tool invocation,
execution coordination, and reflection-based context validation.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import asyncio

from .schemas import (
    ToolType,
    AgentAction,
    AgentResult,
    QueryState,
    Evidence
)
from ..core.database_services import DatabaseManager
from ..core.config import get_config

logger = logging.getLogger(__name__)


class ToolAgent:
    """Agent for tool invocation and execution coordination"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or self._initialize_db_manager()
        self.config = get_config()

        # Tool registry
        self.tool_registry = self._initialize_tools()

    def _initialize_db_manager(self) -> DatabaseManager:
        """Initialize database manager from config"""
        config = get_config()
        return DatabaseManager(
            neo4j_uri=config.neo4j_uri,
            neo4j_user=config.neo4j_user,
            neo4j_password=config.neo4j_password,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key
        )

    def _initialize_tools(self) -> Dict[ToolType, Callable]:
        """Initialize available tools"""
        return {
            ToolType.VECTOR_SEARCH: self._execute_vector_search,
            ToolType.GRAPH_TRAVERSAL: self._execute_graph_traversal,
            ToolType.VLM_RERUN: self._execute_vlm_rerun,
            ToolType.OCR_PROCESS: self._execute_ocr_process,
            ToolType.TEXT_CHUNK: self._execute_text_chunk
        }

    async def execute_plan(self, query_state: QueryState) -> QueryState:
        """Execute the execution plan step by step"""
        logger.info(f"Starting plan execution for query {query_state.query_id}")

        for step in query_state.current_plan:
            if step.step_id in query_state.executed_steps:
                continue  # Skip already executed steps

            try:
                # Execute the step
                result = await self._execute_step(step, query_state)

                # Update state with results
                query_state.executed_steps.append(step.step_id)
                query_state.intermediate_results[step.step_id] = result.data

                # Collect evidence if available
                if result.evidence:
                    query_state.collected_evidence.extend(result.evidence)

                # Check if we need clarification
                if not result.success and "clarification_needed" in str(result.error_message):
                    query_state.needs_clarification = True
                    break

                logger.info(f"Executed step {step.step_id}: {result.success}")

            except Exception as e:
                logger.error(f"Step {step.step_id} failed: {e}")
                # Continue with next step or mark for clarification
                query_state.context[f"step_{step.step_id}_error"] = str(e)

        # Final reflection
        await self._final_reflection(query_state)

        return query_state

    async def _execute_step(self, step: Dict[str, Any], query_state: QueryState) -> AgentResult:
        """Execute a single plan step"""
        tool_type = step.get('tool_type')
        parameters = step.get('parameters', {})

        # Create action record
        action = AgentAction(
            action_type="tool_execution",
            tool_name=tool_type.value,
            parameters=parameters,
            reasoning=f"Executing {tool_type.value} for step {step.get('step_id')}",
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"Executing tool: {tool_type.value} with params: {parameters}")

        try:
            # Get the tool function
            tool_func = self.tool_registry.get(tool_type)
            if not tool_func:
                raise ValueError(f"Tool {tool_type} not found in registry")

            # Execute the tool
            start_time = asyncio.get_event_loop().time()
            result_data = await tool_func(parameters, query_state)
            execution_time = asyncio.get_event_loop().time() - start_time

            # Create result
            result = AgentResult(
                success=True,
                data=result_data,
                execution_time=execution_time
            )

            # Extract evidence from result if applicable
            if isinstance(result_data, dict) and 'evidence' in result_data:
                result.evidence = result_data['evidence']

            logger.info(f"Tool {tool_type.value} executed successfully in {execution_time:.2f}s")

        except Exception as e:
            logger.error(f"Tool {tool_type.value} execution failed: {e}")
            result = AgentResult(
                success=False,
                error_message=str(e),
                execution_time=0.0
            )

        return result

    async def reflect_on_context(self, query_state: QueryState) -> bool:
        """Reflect on whether current context is sufficient for answering"""
        collected_evidence = query_state.collected_evidence
        intermediate_results = query_state.intermediate_results

        # Simple reflection logic
        min_evidence_threshold = 3
        min_result_types = 2

        evidence_count = len(collected_evidence)
        result_types = len(intermediate_results)

        # Check confidence scores
        avg_confidence = 0.0
        if collected_evidence:
            avg_confidence = sum(e.confidence for e in collected_evidence) / len(collected_evidence)

        # Determine if context is sufficient
        context_sufficient = (
            evidence_count >= min_evidence_threshold and
            result_types >= min_result_types and
            avg_confidence >= 0.6
        )

        logger.info(f"Context reflection: {evidence_count} evidence, {result_types} result types, "
                   f"{avg_confidence:.2f} avg confidence -> {'sufficient' if context_sufficient else 'insufficient'}")

        return context_sufficient

    async def _execute_vector_search(self, parameters: Dict[str, Any],
                                   query_state: QueryState) -> Dict[str, Any]:
        """Execute vector search tool"""
        from .retrieval_agent import RetrievalAgent

        agent = RetrievalAgent(self.db_manager)
        result = await agent.retrieve(
            query=query_state.original_query,
            tool_type=ToolType.VECTOR_SEARCH,
            parameters=parameters
        )

        # Convert to dict and add evidence
        result_dict = result.model_dump()
        if result.merged_results:
            result_dict['evidence'] = await agent.collect_evidence(result)

        return result_dict

    async def _execute_graph_traversal(self, parameters: Dict[str, Any],
                                     query_state: QueryState) -> Dict[str, Any]:
        """Execute graph traversal tool"""
        from .retrieval_agent import RetrievalAgent

        agent = RetrievalAgent(self.db_manager)
        result = await agent.retrieve(
            query=query_state.original_query,
            tool_type=ToolType.GRAPH_TRAVERSAL,
            parameters=parameters
        )

        # Convert to dict and add evidence
        result_dict = result.model_dump()
        if result.merged_results:
            result_dict['evidence'] = await agent.collect_evidence(result)

        return result_dict

    async def _execute_vlm_rerun(self, parameters: Dict[str, Any],
                               query_state: QueryState) -> Dict[str, Any]:
        """Execute VLM re-run tool"""
        # This would integrate with VLM service
        # For now, return placeholder result

        logger.info("VLM re-run requested - placeholder implementation")

        # In production, this would:
        # 1. Extract visual elements from query
        # 2. Call VLM service for re-analysis
        # 3. Return enhanced visual understanding

        return {
            'vlm_rerun': True,
            'status': 'placeholder_implementation',
            'message': 'VLM re-run would analyze visual elements in the query',
            'evidence': []
        }

    async def _execute_ocr_process(self, parameters: Dict[str, Any],
                                 query_state: QueryState) -> Dict[str, Any]:
        """Execute OCR processing tool"""
        # This would integrate with OCR service
        # For now, return placeholder result

        logger.info("OCR processing requested - placeholder implementation")

        return {
            'ocr_processed': True,
            'status': 'placeholder_implementation',
            'message': 'OCR would extract text from images',
            'evidence': []
        }

    async def _execute_text_chunk(self, parameters: Dict[str, Any],
                                query_state: QueryState) -> Dict[str, Any]:
        """Execute text chunking tool"""
        # This would integrate with chunking service
        # For now, return placeholder result

        logger.info("Text chunking requested - placeholder implementation")

        return {
            'chunked': True,
            'status': 'placeholder_implementation',
            'message': 'Text would be chunked for processing',
            'evidence': []
        }

    async def _final_reflection(self, query_state: QueryState) -> None:
        """Perform final reflection on the completed execution"""
        context_sufficient = await self.reflect_on_context(query_state)

        if not context_sufficient:
            # Generate clarification questions
            clarification_questions = await self._generate_clarification_questions(query_state)
            query_state.needs_clarification = True
            query_state.clarification_questions = clarification_questions

            logger.info("Context insufficient - clarification needed")
        else:
            # Calculate overall confidence
            query_state.confidence_score = self._calculate_overall_confidence(query_state)
            logger.info(f"Context sufficient - overall confidence: {query_state.confidence_score:.2f}")

    async def _generate_clarification_questions(self, query_state: QueryState) -> List[str]:
        """Generate clarification questions when context is insufficient"""
        questions = []

        evidence_count = len(query_state.collected_evidence)
        result_types = len(query_state.intermediate_results)

        if evidence_count < 3:
            questions.append("Could you provide more specific details about what you're looking for?")

        if result_types < 2:
            questions.append("Would you like me to search for additional related information?")

        # Check for temporal ambiguity
        if "時間" in query_state.original_query or "time" in query_state.original_query.lower():
            questions.append("Could you specify the time period you're interested in?")

        # Check for entity ambiguity
        if len(query_state.collected_evidence) > 0:
            low_confidence_evidence = [e for e in query_state.collected_evidence if e.confidence < 0.5]
            if low_confidence_evidence:
                questions.append("Some information found has low confidence. Could you provide more context?")

        # Default fallback
        if not questions:
            questions.append("Could you rephrase your question to help me understand better?")

        return questions[:3]  # Limit to 3 questions max

    def _calculate_overall_confidence(self, query_state: QueryState) -> float:
        """Calculate overall confidence score for the query results"""
        if not query_state.collected_evidence:
            return 0.0

        # Base confidence from evidence
        evidence_scores = [e.confidence for e in query_state.collected_evidence]
        avg_evidence_confidence = sum(evidence_scores) / len(evidence_scores)

        # Diversity bonus (more different sources = higher confidence)
        source_types = set(e.source_type for e in query_state.collected_evidence)
        diversity_bonus = min(len(source_types) * 0.1, 0.3)

        # Execution completeness bonus
        planned_steps = len(query_state.current_plan)
        executed_steps = len(query_state.executed_steps)
        completeness_bonus = (executed_steps / planned_steps) * 0.2 if planned_steps > 0 else 0.0

        # Calculate final confidence
        final_confidence = (
            avg_evidence_confidence * 0.6 +  # 60% weight on evidence quality
            diversity_bonus * 0.25 +         # 25% weight on source diversity
            completeness_bonus * 0.15        # 15% weight on execution completeness
        )

        return min(final_confidence, 1.0)

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools with descriptions"""
        tool_info = []
        for tool_type, tool_func in self.tool_registry.items():
            tool_info.append({
                'type': tool_type.value,
                'name': tool_type.value.replace('_', ' ').title(),
                'description': self._get_tool_description(tool_type),
                'available': True
            })

        return tool_info

    def _get_tool_description(self, tool_type: ToolType) -> str:
        """Get human-readable description for a tool"""
        descriptions = {
            ToolType.VECTOR_SEARCH: "Search for semantically similar content using vector embeddings",
            ToolType.GRAPH_TRAVERSAL: "Navigate and query the knowledge graph for relationships",
            ToolType.VLM_RERUN: "Re-analyze content using Vision-Language Models",
            ToolType.OCR_PROCESS: "Extract text from images using OCR",
            ToolType.TEXT_CHUNK: "Split and process text into manageable chunks"
        }

        return descriptions.get(tool_type, f"Execute {tool_type.value} operation")


class ReflectorAgent:
    """Specialized agent for reflection and context validation"""

    def __init__(self, tool_agent: ToolAgent):
        self.tool_agent = tool_agent

    async def reflect_and_suggest(self, query_state: QueryState) -> Dict[str, Any]:
        """Perform comprehensive reflection and suggest next actions"""
        reflection_result = {
            'context_sufficient': False,
            'suggested_actions': [],
            'confidence_assessment': {},
            'gaps_identified': []
        }

        # Assess current context
        context_sufficient = await self.tool_agent.reflect_on_context(query_state)
        reflection_result['context_sufficient'] = context_sufficient

        # Identify gaps
        gaps = await self._identify_context_gaps(query_state)
        reflection_result['gaps_identified'] = gaps

        # Assess confidence by category
        confidence_assessment = await self._assess_confidence_by_category(query_state)
        reflection_result['confidence_assessment'] = confidence_assessment

        # Suggest next actions
        if not context_sufficient:
            suggested_actions = await self._suggest_next_actions(query_state, gaps)
            reflection_result['suggested_actions'] = suggested_actions

        return reflection_result

    async def _identify_context_gaps(self, query_state: QueryState) -> List[str]:
        """Identify gaps in the current context"""
        gaps = []

        evidence = query_state.collected_evidence
        results = query_state.intermediate_results

        # Check evidence coverage
        if len(evidence) < 3:
            gaps.append("insufficient_evidence")

        # Check source diversity
        sources = set(e.source_type for e in evidence)
        if len(sources) < 2:
            gaps.append("limited_source_diversity")

        # Check temporal coverage
        has_temporal = any('時間' in str(e.content) or 'time' in str(e.content).lower()
                          for e in evidence)
        if not has_temporal and ('時間' in query_state.original_query or
                                'time' in query_state.original_query.lower()):
            gaps.append("missing_temporal_context")

        # Check for conflicting information
        if len(evidence) > 1:
            confidences = [e.confidence for e in evidence]
            if max(confidences) - min(confidences) > 0.5:
                gaps.append("confidence_variance_high")

        return gaps

    async def _assess_confidence_by_category(self, query_state: QueryState) -> Dict[str, float]:
        """Assess confidence scores by different categories"""
        evidence = query_state.collected_evidence

        if not evidence:
            return {'overall': 0.0}

        # Group by source type
        source_confidences = {}
        for e in evidence:
            source = e.source_type
            if source not in source_confidences:
                source_confidences[source] = []
            source_confidences[source].append(e.confidence)

        # Calculate average confidence per source
        category_confidence = {}
        for source, confidences in source_confidences.items():
            category_confidence[source] = sum(confidences) / len(confidences)

        # Overall confidence
        category_confidence['overall'] = sum(e.confidence for e in evidence) / len(evidence)

        return category_confidence

    async def _suggest_next_actions(self, query_state: QueryState, gaps: List[str]) -> List[Dict[str, Any]]:
        """Suggest next actions based on identified gaps"""
        suggestions = []

        for gap in gaps:
            if gap == "insufficient_evidence":
                suggestions.append({
                    'action': 'expand_search',
                    'tool': ToolType.VECTOR_SEARCH.value,
                    'reason': 'Need more evidence to support the answer',
                    'priority': 'high'
                })

            elif gap == "limited_source_diversity":
                suggestions.append({
                    'action': 'try_different_source',
                    'tool': ToolType.GRAPH_TRAVERSAL.value,
                    'reason': 'Current results come from limited sources',
                    'priority': 'medium'
                })

            elif gap == "missing_temporal_context":
                suggestions.append({
                    'action': 'add_temporal_search',
                    'tool': ToolType.GRAPH_TRAVERSAL.value,
                    'parameters': {'temporal': True},
                    'reason': 'Query involves time but temporal context is missing',
                    'priority': 'high'
                })

            elif gap == "confidence_variance_high":
                suggestions.append({
                    'action': 'validate_high_confidence_sources',
                    'tool': ToolType.VECTOR_SEARCH.value,
                    'parameters': {'validate_evidence': True},
                    'reason': 'High variance in evidence confidence needs validation',
                    'priority': 'medium'
                })

        return suggestions
