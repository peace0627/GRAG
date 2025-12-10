"""
Main RAG Agent

This module implements the main RAG agent that orchestrates the entire
Agentic RAG pipeline from query planning to final answer generation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .planner import QueryPlanner
from .retrieval_agent import RetrievalAgent
from .reasoning_agent import ReasoningAgent
from .tool_agent import ToolAgent, ReflectorAgent
from .schemas import QueryState, QueryType, Evidence
from ..core.database_services import DatabaseManager
from ..core.config import get_config
from ..core.llm_factory import create_answerer_llm, create_default_llm

logger = logging.getLogger(__name__)


class AgenticRAGAgent:
    """Main agent that orchestrates the complete Agentic RAG pipeline"""

    def __init__(self,
                 llm: Optional[ChatOpenAI] = None,
                 db_manager: Optional[DatabaseManager] = None):
        self.config = get_config()

        # Initialize components
        self.llm = llm or create_answerer_llm()

        self.db_manager = db_manager or DatabaseManager(
            neo4j_uri=self.config.neo4j_uri,
            neo4j_user=self.config.neo4j_user,
            neo4j_password=self.config.neo4j_password,
            supabase_url=self.config.supabase_url,
            supabase_key=self.config.supabase_key
        )

        # Initialize agents
        self.planner = QueryPlanner(self.llm)
        self.retrieval_agent = RetrievalAgent(self.db_manager)
        self.reasoning_agent = ReasoningAgent(self.db_manager)
        self.tool_agent = ToolAgent(self.db_manager)
        self.reflector = ReflectorAgent(self.tool_agent)

    async def query(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main query entry point for the Agentic RAG system"""
        start_time = datetime.now()

        logger.info(f"Starting Agentic RAG query: {user_query[:100]}...")

        try:
            # Phase 1: Query Planning
            logger.info("Phase 1: Query Planning")
            planner_output = await self.planner.plan_query(user_query, context)

            # Initialize query state
            query_state = QueryState(
                query_id=planner_output.query_type.value + "_" + str(hash(user_query))[:8],
                original_query=user_query,
                query_type=planner_output.query_type,
                current_plan=planner_output.execution_plan,
                context=context or {}
            )

            # Phase 2: Tool Execution
            logger.info("Phase 2: Tool Execution")
            query_state = await self.tool_agent.execute_plan(query_state)

            # Phase 3: Reasoning (if needed)
            if query_state.query_type in [QueryType.ANALYTICAL, QueryType.COMPLEX]:
                logger.info("Phase 3: Advanced Reasoning")
                reasoning_result = await self.reasoning_agent.reason(
                    user_query,
                    query_state.context,
                    reasoning_type="general"
                )
                query_state.context["reasoning_result"] = reasoning_result

            # Phase 4: Context Reflection
            logger.info("Phase 4: Context Reflection")
            reflection_result = await self.reflector.reflect_and_suggest(query_state)

            # Phase 5: Final Answer Generation
            logger.info("Phase 5: Final Answer Generation")
            final_answer = await self._generate_final_answer(query_state)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Prepare response
            response = {
                "query_id": query_state.query_id,
                "original_query": user_query,
                "query_type": query_state.query_type.value,
                "final_answer": final_answer,
                "confidence_score": query_state.confidence_score,
                "evidence_count": len(query_state.collected_evidence),
                "execution_time": execution_time,
                "needs_clarification": query_state.needs_clarification,
                "clarification_questions": query_state.clarification_questions,
                "planning_info": {
                    "estimated_complexity": planner_output.estimated_complexity,
                    "execution_plan_steps": len(planner_output.execution_plan),
                    "suggested_tools": [t.value for t in planner_output.suggested_tools]
                },
                "evidence": [
                    {
                        "evidence_id": e.evidence_id,
                        "source_type": e.source_type,
                        "content": e.content,
                        "confidence": e.confidence,
                        "metadata": e.metadata
                    } for e in query_state.collected_evidence[:10]  # Limit evidence in response
                ],
                "reflection": {
                    "context_sufficient": reflection_result.get("context_sufficient", False),
                    "gaps_identified": reflection_result.get("gaps_identified", []),
                    "confidence_assessment": reflection_result.get("confidence_assessment", {})
                }
            }

            logger.info(f"Agentic RAG query completed in {execution_time:.2f}s with confidence {query_state.confidence_score:.2f}")
            return response

        except Exception as e:
            logger.error(f"Agentic RAG query failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "query_id": f"error_{hash(user_query)}",
                "original_query": user_query,
                "error": str(e),
                "execution_time": execution_time,
                "success": False
            }

    async def _generate_final_answer(self, query_state: QueryState) -> str:
        """Generate the final answer using LLM with source-aware evidence processing"""
        if not query_state.collected_evidence:
            return "I couldn't find sufficient information to answer your question. Could you provide more details."

        # Convert evidence to UnifiedEvidence format for enhanced processing
        unified_evidence = await self._convert_to_unified_evidence(query_state.collected_evidence)

        # Detect and handle contradictions
        contradiction_analysis = self._analyze_evidence_contradictions(unified_evidence)

        # Prepare source-aware context for LLM
        evidence_context = self._build_source_aware_evidence_context(unified_evidence)

        # Prepare reasoning context
        reasoning_context = ""
        if "reasoning_result" in query_state.context:
            reasoning = query_state.context["reasoning_result"]
            reasoning_context = f"""
Reasoning Analysis:
- Relations found: {len(reasoning.inferred_relations)}
- Reasoning path: {' -> '.join(reasoning.reasoning_path)}
- Confidence: {reasoning.confidence:.2f}
"""

        # Create enhanced prompt for final answer generation
        system_prompt = self._build_source_aware_system_prompt(contradiction_analysis)

        user_prompt = f"""
Query: {query_state.original_query}

{evidence_context}

{reasoning_context}

Please provide a comprehensive answer based on the above evidence. Consider source reliability and note any contradictions."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            final_answer = response.content.strip()

            # Add source traceability and contradiction warnings
            final_answer = self._enhance_answer_with_traceability(
                final_answer, unified_evidence, contradiction_analysis, query_state.confidence_score
            )

            return final_answer

        except Exception as e:
            logger.error(f"Final answer generation failed: {e}")
            return f"I encountered an error while generating the final answer: {str(e)}. However, I found {len(query_state.collected_evidence)} pieces of evidence that may be relevant."

    async def _convert_to_unified_evidence(self, evidence_list: List[Any]) -> List[Dict[str, Any]]:
        """Convert collected evidence to unified format with source awareness"""
        from ..core.schemas.unified_schemas import SourceType, Modality

        unified_evidence = []

        for evidence in evidence_list:
            # Handle different evidence formats
            if hasattr(evidence, 'model_dump'):  # Already UnifiedEvidence
                unified_evidence.append(evidence.model_dump())
            else:  # Legacy Evidence format
                unified_item = {
                    "evidence_id": getattr(evidence, 'evidence_id', f"evidence_{len(unified_evidence)}"),
                    "source_type": getattr(evidence, 'source_type', 'unknown'),
                    "modality": getattr(evidence, 'modality', Modality.TEXT.value),
                    "content": getattr(evidence, 'content', ''),
                    "summary": getattr(evidence, 'summary', None),
                    "confidence": getattr(evidence, 'confidence', 0.5),
                    "relevance_score": getattr(evidence, 'relevance_score', 0.5),
                    "quality_score": getattr(evidence, 'quality_score', 0.5),
                    "traceability": getattr(evidence, 'traceability', None),
                    "metadata": getattr(evidence, 'metadata', {}),
                    "created_at": getattr(evidence, 'created_at', None)
                }
                unified_evidence.append(unified_item)

        return unified_evidence

    def _analyze_evidence_contradictions(self, evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze evidence for contradictions and conflicts"""
        analysis = {
            "has_contradictions": False,
            "contradiction_count": 0,
            "conflicting_evidence_pairs": [],
            "severity": "none",  # none, low, medium, high
            "recommendations": []
        }

        if len(evidence_list) < 2:
            return analysis

        # Simple contradiction detection (can be enhanced with LLM)
        content_hashes = {}
        contradictions_found = []

        for i, evidence in enumerate(evidence_list):
            content_hash = hash(evidence["content"].lower().strip()[:100])  # First 100 chars

            if content_hash in content_hashes:
                existing_idx = content_hashes[content_hash]
                # Check if confidence scores differ significantly
                conf_diff = abs(evidence["confidence"] - evidence_list[existing_idx]["confidence"])

                if conf_diff > 0.3:  # Significant confidence difference
                    contradictions_found.append({
                        "evidence_1": existing_idx,
                        "evidence_2": i,
                        "confidence_diff": conf_diff,
                        "content_similarity": "high"
                    })

            content_hashes[content_hash] = i

        if contradictions_found:
            analysis["has_contradictions"] = True
            analysis["contradiction_count"] = len(contradictions_found)
            analysis["conflicting_evidence_pairs"] = contradictions_found

            # Assess severity
            if len(contradictions_found) >= 3:
                analysis["severity"] = "high"
            elif len(contradictions_found) >= 2:
                analysis["severity"] = "medium"
            else:
                analysis["severity"] = "low"

            analysis["recommendations"] = [
                "Consider the source reliability of conflicting evidence",
                "Look for additional corroborating evidence",
                "Note uncertainty in areas with conflicting information"
            ]

        return analysis

    def _build_source_aware_evidence_context(self, evidence_list: List[Dict[str, Any]]) -> str:
        """Build evidence context with source awareness for LLM"""
        if not evidence_list:
            return "No evidence available."

        context_parts = ["Evidence Available (with source information):"]

        for i, evidence in enumerate(evidence_list[:8]):  # Limit to top 8 evidence
            source_info = self._format_source_info(evidence)
            modality_info = f"[{evidence.get('modality', 'text').upper()}]"

            evidence_text = f"""
[{i+1}] {modality_info} {evidence['content']}
    Source: {source_info}
    Confidence: {evidence['confidence']:.2f}, Relevance: {evidence.get('relevance_score', 0.5):.2f}
    Quality: {evidence.get('quality_score', 0.5):.2f}
"""

            # Add traceability info if available
            if evidence.get('traceability'):
                trace = evidence['traceability']
                if trace.get('document_path'):
                    evidence_text += f"    Document: {trace['document_path']}\n"
                if trace.get('extraction_method'):
                    evidence_text += f"    Extraction: {trace['extraction_method']}\n"

            context_parts.append(evidence_text)

        # Add source reliability guide
        reliability_guide = """

Source Reliability Guide:
- Neo4j: Graph database - best for relationship and structural information
- Supabase: Vector database - best for semantic similarity and content matching
- Hybrid: Combined sources - generally most reliable
- External: Third-party sources - verify independently

Higher confidence scores indicate more reliable evidence."""

        context_parts.append(reliability_guide)

        return "\n".join(context_parts)

    def _format_source_info(self, evidence: Dict[str, Any]) -> str:
        """Format source information for display"""
        source_type = evidence.get('source_type', 'unknown')

        if source_type == 'neo4j':
            return "Knowledge Graph (Neo4j) - Structural relationships"
        elif source_type == 'supabase':
            return "Vector Database (Supabase) - Semantic similarity"
        elif source_type == 'hybrid':
            return "Hybrid Sources - Combined reliability"
        else:
            return f"{source_type} - External source"

    def _build_source_aware_system_prompt(self, contradiction_analysis: Dict[str, Any]) -> str:
        """Build system prompt that considers source awareness and contradictions"""
        base_prompt = """You are an expert assistant that provides accurate, well-reasoned answers based on the provided evidence.

Guidelines:
1. Base your answer primarily on the provided evidence, considering source reliability
2. Pay special attention to source types: Neo4j (relationships), Supabase (similarity), Hybrid (combined)
3. When appropriate, cite evidence numbers [1], [2], etc. with their source types
4. Keep answers concise but comprehensive
5. For complex questions, break down your reasoning step by step
"""

        # Add contradiction handling if needed
        if contradiction_analysis["has_contradictions"]:
            severity = contradiction_analysis["severity"]
            contradiction_guidance = f"""

IMPORTANT: Evidence contains contradictions (Severity: {severity.upper()})
- Acknowledge conflicting information in your answer
- Explain which sources you prioritize and why
- Note uncertainty where contradictions exist
- Suggest areas needing clarification
"""
            base_prompt += contradiction_guidance

        base_prompt += "\nAlways include a confidence assessment and source attribution at the end."

        return base_prompt

    def _enhance_answer_with_traceability(self, answer: str, evidence_list: List[Dict[str, Any]],
                                        contradiction_analysis: Dict[str, Any],
                                        overall_confidence: float) -> str:
        """Enhance answer with traceability information and contradiction warnings"""
        enhanced_answer = answer

        # Add contradiction warning if needed
        if contradiction_analysis["has_contradictions"]:
            severity_descriptions = {
                "high": "significant conflicting evidence",
                "medium": "some conflicting information",
                "low": "minor contradictions noted"
            }

            warning = f"\n\n⚠️ Note: Answer based on evidence with {severity_descriptions[contradiction_analysis['severity']]}. "
            warning += f"Found {contradiction_analysis['contradiction_count']} conflicting evidence pairs."

            enhanced_answer += warning

        # Add source attribution
        source_counts = {}
        for evidence in evidence_list[:5]:  # Top 5 evidence
            source = evidence.get('source_type', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1

        if source_counts:
            attribution = "\n\n📚 Sources used: " + ", ".join([
                f"{source} ({count})" for source, count in source_counts.items()
            ])
            enhanced_answer += attribution

        # Add confidence assessment
        if overall_confidence > 0:
            confidence_level = "High" if overall_confidence > 0.8 else "Medium" if overall_confidence > 0.6 else "Low"
            enhanced_answer += f"\n\n🎯 Overall confidence: {confidence_level} ({overall_confidence:.2f})"

        return enhanced_answer

    async def get_system_status(self) -> Dict[str, Any]:
        """Get the current status of all agents and components"""
        try:
            # Check available tools
            tools = await self.tool_agent.get_available_tools()

            # Check database connectivity
            db_status = await self._check_database_status()

            return {
                "status": "operational",
                "agents": {
                    "planner": "ready",
                    "retrieval": "ready",
                    "reasoning": "ready",
                    "tool_agent": "ready",
                    "reflector": "ready"
                },
                "tools_available": len(tools),
                "database_status": db_status,
                "llm_model": self.llm.model_name if hasattr(self.llm, 'model_name') else "unknown"
            }

        except Exception as e:
            logger.error(f"System status check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _check_database_status(self) -> Dict[str, str]:
        """Check database connectivity status"""
        status = {}

        try:
            # Check Neo4j
            async with self.db_manager.neo4j_session() as session:
                result = await session.run("RETURN 'neo4j_connected' as status")
                record = await result.single()
                status["neo4j"] = "connected" if record else "error"
        except Exception as e:
            status["neo4j"] = f"error: {str(e)}"

        try:
            # Check Supabase
            client = self.db_manager.get_supabase_client()
            # Simple connectivity check
            response = client.table('vectors').select('count', count='exact').limit(1).execute()
            status["supabase"] = "connected"
        except Exception as e:
            status["supabase"] = f"error: {str(e)}"

        return status


class SimpleRAGAgent:
    """Simplified RAG agent for basic queries (fallback option)"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager(
            neo4j_uri=get_config().neo4j_uri,
            neo4j_user=get_config().neo4j_user,
            neo4j_password=get_config().neo4j_password,
            supabase_url=get_config().supabase_url,
            supabase_key=get_config().supabase_key
        )
        self.retrieval_agent = RetrievalAgent(self.db_manager)
        self.llm = create_default_llm()

    async def query(self, user_query: str) -> Dict[str, Any]:
        """Simple RAG query without full agent orchestration"""
        start_time = datetime.now()

        try:
            # Simple retrieval
            result = await self.retrieval_agent.retrieve(
                query=user_query,
                tool_type=ToolType.VECTOR_SEARCH,
                parameters={"top_k": 5}
            )

            # Collect evidence
            evidence = await self.retrieval_agent.collect_evidence(result) if result.merged_results else []

            # Generate answer
            if evidence:
                evidence_text = "\n".join([f"- {e.content}" for e in evidence[:3]])
                prompt = f"Based on this evidence, answer: {user_query}\n\nEvidence:\n{evidence_text}"

                response = await self.llm.ainvoke([HumanMessage(content=prompt)])
                answer = response.content
            else:
                answer = "I couldn't find relevant information for your query."

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "query_id": f"simple_{hash(user_query)}",
                "original_query": user_query,
                "final_answer": answer,
                "evidence_count": len(evidence),
                "execution_time": execution_time,
                "simple_mode": True
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "query_id": f"error_{hash(user_query)}",
                "original_query": user_query,
                "error": str(e),
                "execution_time": execution_time,
                "success": False
            }
