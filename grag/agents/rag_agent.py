"""
Main RAG Agent

This module implements the main RAG agent that orchestrates the entire
Agentic RAG pipeline from query planning to final answer generation.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .planner import QueryPlanner
from .retrieval_agent import RetrievalAgent
from .reasoning_agent import ReasoningAgent
from .tool_agent import ToolAgent, ReflectorAgent
from .schemas import QueryState, QueryType, Evidence
from ..core.database_services import DatabaseManager
from ..core.config import get_config

logger = logging.getLogger(__name__)


class AgenticRAGAgent:
    """Main agent that orchestrates the complete Agentic RAG pipeline"""

    def __init__(self,
                 llm: Optional[ChatOpenAI] = None,
                 db_manager: Optional[DatabaseManager] = None):
        self.config = get_config()

        # Initialize components
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )

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
        """Generate the final answer using LLM with collected evidence"""
        if not query_state.collected_evidence:
            return "I couldn't find sufficient information to answer your question. Could you provide more details?"

        # Prepare context for LLM
        evidence_texts = []
        for i, evidence in enumerate(query_state.collected_evidence[:5]):  # Limit to top 5 evidence
            evidence_texts.append(f"[{i+1}] {evidence.content} (Confidence: {evidence.confidence:.2f})")

        evidence_summary = "\n".join(evidence_texts)

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

        # Create prompt for final answer generation
        system_prompt = """You are an expert assistant that provides accurate, well-reasoned answers based on the provided evidence.

Guidelines:
1. Base your answer primarily on the provided evidence
2. If evidence is insufficient, clearly state this and suggest what additional information would help
3. Provide confidence levels for your statements
4. When appropriate, cite evidence numbers [1], [2], etc.
5. Keep answers concise but comprehensive
6. For complex questions, break down your reasoning step by step

Always include a confidence assessment at the end."""

        user_prompt = f"""
Query: {query_state.original_query}

Evidence Available:
{evidence_summary}

{reasoning_context}

Please provide a comprehensive answer based on the above evidence. Include your confidence level and cite sources where relevant."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            final_answer = response.content.strip()

            # Add confidence assessment if not present
            if "confidence" not in final_answer.lower() and query_state.confidence_score > 0:
                final_answer += f"\n\nOverall confidence: {query_state.confidence_score:.2f}"

            return final_answer

        except Exception as e:
            logger.error(f"Final answer generation failed: {e}")
            return f"I encountered an error while generating the final answer: {str(e)}. However, I found {len(query_state.collected_evidence)} pieces of evidence that may be relevant."

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
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

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
