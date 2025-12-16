"""
Smart Query Router

This module implements intelligent query routing based on structured query analysis,
dynamically selecting the optimal combination of tools for different query types.
"""

import logging
from typing import Dict, Any
from enum import Enum

from .query_schemas import StructuredQuery, QueryType
from .schemas import ToolType

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategy types"""
    SINGLE_TOOL = "single_tool"          # Use only one primary tool
    PARALLEL_TOOLS = "parallel_tools"     # Run multiple tools in parallel
    SEQUENTIAL_TOOLS = "sequential_tools" # Run tools sequentially based on results
    HYBRID_ADAPTIVE = "hybrid_adaptive"  # Adaptive routing based on query complexity


class SmartRouter:
    """Intelligent query routing engine"""

    def __init__(self):
        self.routing_rules = self._initialize_routing_rules()

    def _initialize_routing_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize routing rules for different query patterns"""
        return {
            # Factual queries - direct retrieval
            "factual_find": {
                "strategy": RoutingStrategy.SINGLE_TOOL,
                "primary_tool": ToolType.VECTOR_SEARCH,
                "fallback_tools": [ToolType.GRAPH_TRAVERSAL],
                "parallel_execution": False
            },

            "factual_analyze": {
                "strategy": RoutingStrategy.SEQUENTIAL_TOOLS,
                "primary_tool": ToolType.VECTOR_SEARCH,
                "secondary_tools": [ToolType.GRAPH_TRAVERSAL],
                "parallel_execution": False
            },

            # Visual queries - visual-first approach
            "visual_find": {
                "strategy": RoutingStrategy.SINGLE_TOOL,
                "primary_tool": ToolType.VECTOR_SEARCH,
                "parameters": {"modality": "visual"},
                "fallback_tools": [ToolType.VLM_RERUN]
            },

            "visual_analyze": {
                "strategy": RoutingStrategy.PARALLEL_TOOLS,
                "tools": [ToolType.VECTOR_SEARCH, ToolType.GRAPH_TRAVERSAL],
                "parameters": {"modality": "visual", "reasoning": True}
            },

            # Temporal queries - time-aware routing
            "temporal": {
                "strategy": RoutingStrategy.HYBRID_ADAPTIVE,
                "primary_tool": ToolType.GRAPH_TRAVERSAL,
                "parameters": {"temporal": True},
                "adaptive_rules": ["expand_time_window", "add_vector_search"]
            },

            # Complex queries - multi-tool orchestration
            "complex": {
                "strategy": RoutingStrategy.SEQUENTIAL_TOOLS,
                "tools": [ToolType.VECTOR_SEARCH, ToolType.GRAPH_TRAVERSAL, ToolType.VECTOR_SEARCH],
                "parameters": {"reasoning": True, "max_depth": 3}
            },

            # Analytical queries - reasoning-focused
            "analytical": {
                "strategy": RoutingStrategy.SEQUENTIAL_TOOLS,
                "primary_tool": ToolType.GRAPH_TRAVERSAL,
                "secondary_tools": [ToolType.VECTOR_SEARCH],
                "parameters": {"reasoning": True}
            },

            # Causal queries - relationship-focused
            "causal": {
                "strategy": RoutingStrategy.PARALLEL_TOOLS,
                "tools": [ToolType.GRAPH_TRAVERSAL, ToolType.VECTOR_SEARCH],
                "parameters": {"reasoning": True, "causal_analysis": True}
            },

            # Comparative queries - multi-source comparison
            "comparative": {
                "strategy": RoutingStrategy.PARALLEL_TOOLS,
                "tools": [ToolType.VECTOR_SEARCH, ToolType.GRAPH_TRAVERSAL],
                "parameters": {"comparison_mode": True}
            }
        }

    def route_query(self, structured_query: StructuredQuery) -> Dict[str, Any]:
        """Route query to optimal tool combination

        Args:
            structured_query: Parsed structured query

        Returns:
            Routing decision with tools, parameters, and execution strategy
        """
        logger.info(f"Routing query: {structured_query.query_type.value}")

        # Determine routing pattern
        routing_pattern = self._determine_routing_pattern(structured_query)

        # Get routing rule
        rule = self.routing_rules.get(routing_pattern)
        if not rule:
            # Fallback to default routing
            rule = self.routing_rules["factual_find"]
            logger.warning(f"No routing rule for pattern {routing_pattern}, using fallback")

        # Customize parameters based on query
        customized_rule = self._customize_parameters(rule, structured_query)

        # Apply adaptive routing if needed
        if customized_rule.get("strategy") == RoutingStrategy.HYBRID_ADAPTIVE:
            customized_rule = self._apply_adaptive_routing(customized_rule, structured_query)

        routing_decision = {
            "routing_pattern": routing_pattern,
            "strategy": customized_rule["strategy"],
            "tools": customized_rule.get("tools", [customized_rule.get("primary_tool")]),
            "parameters": customized_rule.get("parameters", {}),
            "execution_order": customized_rule.get("execution_order", "parallel"),
            "confidence_threshold": self._calculate_confidence_threshold(structured_query),
            "estimated_complexity": self._estimate_complexity(structured_query)
        }

        logger.info(f"Routing decision: {routing_decision['strategy'].value} with {len(routing_decision['tools'])} tools")
        return routing_decision

    def _determine_routing_pattern(self, query: StructuredQuery) -> str:
        """Determine routing pattern based on query characteristics"""
        query_type = query.query_type.value
        primary_action = query.intent.primary_action.value

        # Create pattern key
        pattern_key = f"{query_type}_{primary_action}"

        # Check for special cases
        if query.query_type == QueryType.VISUAL:
            return f"visual_{primary_action}"
        elif query.query_type == QueryType.TEMPORAL:
            return "temporal"
        elif query.query_type in [QueryType.COMPLEX, QueryType.CAUSAL]:
            return query_type.value
        elif query.query_type == QueryType.COMPARATIVE:
            return "comparative"
        elif query.query_type == QueryType.ANALYTICAL:
            return "analytical"

        # Default patterns
        if pattern_key in self.routing_rules:
            return pattern_key
        else:
            return f"{query_type}_find"  # Fallback

    def _customize_parameters(self, rule: Dict[str, Any], query: StructuredQuery) -> Dict[str, Any]:
        """Customize routing parameters based on query specifics"""
        customized = rule.copy()

        # Add query-specific parameters
        parameters = customized.get("parameters", {})

        # Add modality preferences
        if query.query_type == QueryType.VISUAL:
            parameters["modality"] = "visual"
        elif query.intent.visualization_preferred:
            parameters["include_visual"] = True

        # Add temporal parameters
        if query.query_type == QueryType.TEMPORAL or "時間" in query.original_query or "time" in query.original_query.lower():
            parameters["temporal"] = True
            if query.constraints.time_scope:
                parameters["time_scope"] = query.constraints.time_scope

        # Add complexity-based parameters
        if query.reasoning_requirements.complexity_level == "high":
            parameters["max_depth"] = 4
            parameters["reasoning"] = True
        elif query.reasoning_requirements.complexity_level == "medium":
            parameters["max_depth"] = 2
            parameters["reasoning"] = True

        # Add constraint-based parameters
        if query.constraints.must_include:
            parameters["must_include"] = query.constraints.must_include

        if query.constraints.preferred_sources:
            parameters["preferred_sources"] = query.constraints.preferred_sources

        # Update parameters in rule
        customized["parameters"] = parameters

        return customized

    def _apply_adaptive_routing(self, rule: Dict[str, Any], query: StructuredQuery) -> Dict[str, Any]:
        """Apply adaptive routing logic based on query complexity"""
        adaptive_rules = rule.get("adaptive_rules", [])

        # Assess query complexity
        complexity_score = self._calculate_complexity_score(query)

        adapted_rule = rule.copy()

        if "expand_time_window" in adaptive_rules and complexity_score > 0.7:
            # For complex temporal queries, expand search scope
            adapted_rule["tools"] = [ToolType.GRAPH_TRAVERSAL, ToolType.VECTOR_SEARCH]
            adapted_rule["strategy"] = RoutingStrategy.PARALLEL_TOOLS
            adapted_rule["parameters"]["time_window_expansion"] = True

        elif "add_vector_search" in adaptive_rules and query.intent.target_entities:
            # For entity-focused queries, add vector search
            adapted_rule["tools"] = [ToolType.GRAPH_TRAVERSAL, ToolType.VECTOR_SEARCH]
            adapted_rule["strategy"] = RoutingStrategy.PARALLEL_TOOLS

        return adapted_rule

    def _calculate_complexity_score(self, query: StructuredQuery) -> float:
        """Calculate query complexity score (0-1)"""
        score = 0.0

        # Query type complexity
        type_weights = {
            QueryType.COMPLEX: 1.0,
            QueryType.CAUSAL: 0.8,
            QueryType.ANALYTICAL: 0.7,
            QueryType.COMPARATIVE: 0.6,
            QueryType.TEMPORAL: 0.5,
            QueryType.VISUAL: 0.4,
            QueryType.FACTUAL: 0.2
        }
        score += type_weights.get(query.query_type, 0.0) * 0.4

        # Reasoning requirements
        reasoning_depth = query.reasoning_requirements.reasoning_depth
        score += (reasoning_depth / 5.0) * 0.3

        # Constraints complexity
        constraint_count = len(query.constraints.must_include) + len(query.constraints.preferred_sources)
        score += min(constraint_count / 5.0, 1.0) * 0.3

        return min(score, 1.0)

    def _calculate_confidence_threshold(self, query: StructuredQuery) -> float:
        """Calculate required confidence threshold for results"""
        base_threshold = 0.6

        # Adjust based on query type
        if query.query_type in [QueryType.COMPLEX, QueryType.CAUSAL]:
            base_threshold = 0.8
        elif query.query_type == QueryType.ANALYTICAL:
            base_threshold = 0.7

        # Adjust based on reasoning requirements
        if query.reasoning_requirements.complexity_level == "high":
            base_threshold += 0.1

        # Adjust based on constraints
        if query.constraints.confidence_threshold:
            base_threshold = max(base_threshold, query.constraints.confidence_threshold)

        return min(base_threshold, 0.95)

    def _estimate_complexity(self, query: StructuredQuery) -> str:
        """Estimate query complexity level"""
        complexity_score = self._calculate_complexity_score(query)

        if complexity_score >= 0.8:
            return "high"
        elif complexity_score >= 0.5:
            return "medium"
        else:
            return "low"

    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics for monitoring"""
        return {
            "routing_rules_count": len(self.routing_rules),
            "supported_patterns": list(self.routing_rules.keys()),
            "routing_strategies": [rule["strategy"].value for rule in self.routing_rules.values()]
        }

    def add_custom_routing_rule(self, pattern: str, rule: Dict[str, Any]) -> None:
        """Add custom routing rule for specific use cases"""
        self.routing_rules[pattern] = rule
        logger.info(f"Added custom routing rule for pattern: {pattern}")

    def validate_routing_decision(self, decision: Dict[str, Any]) -> bool:
        """Validate routing decision for consistency"""
        required_fields = ["routing_pattern", "strategy", "tools", "parameters"]

        for field in required_fields:
            if field not in decision:
                logger.error(f"Missing required field in routing decision: {field}")
                return False

        if not decision["tools"]:
            logger.error("Routing decision must include at least one tool")
            return False

        return True
