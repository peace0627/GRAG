"""
Structured Query Parser

This module implements the LLM-driven query parser that converts natural language
queries into structured JSON representations for programmatic processing.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from .query_schemas import (
    StructuredQuery,
    QueryParsingResult,
    QueryType,
    PrimaryAction,
    QueryIntent,
    QueryConstraints,
    ReasoningRequirements,
    ResponseFormat
)
from ..core.llm_factory import create_query_parser_llm

logger = logging.getLogger(__name__)


class StructuredQueryParser:
    """LLM-driven query parser for converting natural language to structured JSON"""

    def __init__(self, llm=None):
        # Use centralized LLM configuration
        self.llm = llm or create_query_parser_llm()
        self.model_name = self.llm.model_name if hasattr(self.llm, 'model_name') else "query_parser_llm"
        self._load_parsing_prompts()

    def _load_parsing_prompts(self):
        """Load parsing prompts for different query types"""
        self.system_prompt = """
你是一個專業的查詢解析助手。你的任務是將用戶的自然語言查詢轉換為結構化的JSON格式。

請分析查詢的以下方面：
1. 主要意圖 (primary_action)
2. 目標指標或實體 (target_metric, target_entities)
3. 分組和過濾條件 (group_by, filters)
4. 約束條件 (constraints)
5. 推理需求 (reasoning_requirements)
6. 回應格式偏好 (response_format)

返回規範的JSON格式，不要包含其他說明。

JSON結構必須包含：
- query_type: factual|analytical|visual|temporal|complex|causal|comparative|predictive
- intent: 包含primary_action等字段
- constraints: 約束條件
- reasoning_requirements: 推理需求
- response_format: 回應格式
"""

        self.examples = """
示例：

查詢: "圖表顯示哪個月銷售最低？"
{
  "query_type": "visual",
  "intent": {
    "primary_action": "find",
    "target_metric": "sales",
    "group_by": "month",
    "visualization_preferred": true
  },
  "constraints": {
    "must_include": ["monthly_data", "visual_charts"],
    "preferred_sources": ["charts", "reports"]
  },
  "reasoning_requirements": {
    "needs_comparison": true,
    "complexity_level": "medium"
  },
  "response_format": {
    "include_evidence": true,
    "preferred_style": "concise"
  }
}

查詢: "為什麼營收在第三季度下降？"
{
  "query_type": "causal",
  "intent": {
    "primary_action": "explain",
    "target_metric": "revenue"
  },
  "constraints": {
    "time_scope": "Q3",
    "must_include": ["causes", "factors"]
  },
  "reasoning_requirements": {
    "needs_causal_analysis": true,
    "needs_trend_analysis": true,
    "complexity_level": "high"
  },
  "response_format": {
    "include_evidence": true,
    "include_methodology": true,
    "preferred_style": "detailed"
  }
}
"""

    async def parse_query(self, query: str, language: Optional[str] = None) -> QueryParsingResult:
        """Parse natural language query into structured JSON"""
        start_time = time.time()

        try:
            # Detect language if not provided
            if not language:
                language = self._detect_language(query)

            # Create parsing prompt
            user_prompt = f"""
請解析以下查詢：

查詢語言: {language}
查詢內容: {query}

{self.examples}

請返回JSON格式的結構化表示。
"""

            # Call LLM for parsing
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            raw_response = response.content.strip()

            # Parse and validate JSON
            parsed_data = self._parse_llm_response(raw_response)
            if not parsed_data:
                return QueryParsingResult(
                    success=False,
                    error_message="Failed to parse LLM response as JSON",
                    fallback_type="keyword_matching",
                    processing_time=time.time() - start_time,
                    raw_llm_response=raw_response
                )

            # Create structured query object
            structured_query = self._create_structured_query(query, language, parsed_data)

            return QueryParsingResult(
                success=True,
                structured_query=structured_query,
                processing_time=time.time() - start_time,
                raw_llm_response=raw_response
            )

        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            return QueryParsingResult(
                success=False,
                error_message=str(e),
                fallback_type="error_fallback",
                processing_time=time.time() - start_time
            )

    def _detect_language(self, query: str) -> str:
        """Simple language detection based on character sets"""
        # Count Chinese characters
        chinese_chars = sum(1 for char in query if '\u4e00' <= char <= '\u9fff')

        if chinese_chars > len(query) * 0.3:  # More than 30% Chinese characters
            return "zh"
        elif any(ord(char) > 127 for char in query):  # Contains non-ASCII
            # Could be extended for Japanese, Korean, etc.
            return "other"
        else:
            return "en"

    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into dictionary"""
        try:
            # Try to extract JSON from response
            # Sometimes LLM includes extra text, try to find JSON block
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                # Try parsing entire response
                return json.loads(response)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            logger.debug(f"Raw response: {response}")
            return None

    def _create_structured_query(self, original_query: str, language: str,
                                parsed_data: Dict[str, Any]) -> StructuredQuery:
        """Create StructuredQuery object from parsed data"""

        # Extract and validate components
        query_type = self._validate_query_type(parsed_data.get("query_type", "factual"))

        intent_data = parsed_data.get("intent", {})
        intent = QueryIntent(
            primary_action=self._validate_primary_action(intent_data.get("primary_action", "find")),
            target_metric=intent_data.get("target_metric"),
            target_entities=intent_data.get("target_entities", []),
            group_by=intent_data.get("group_by"),
            filters=intent_data.get("filters", {}),
            sort_by=intent_data.get("sort_by"),
            limit=intent_data.get("limit"),
            visualization_preferred=intent_data.get("visualization_preferred", False),
            calculation_needed=intent_data.get("calculation_needed", False)
        )

        constraints_data = parsed_data.get("constraints", {})
        constraints = QueryConstraints(
            must_include=constraints_data.get("must_include", []),
            preferred_sources=constraints_data.get("preferred_sources", []),
            exclude_sources=constraints_data.get("exclude_sources", []),
            time_scope=constraints_data.get("time_scope"),
            data_freshness=constraints_data.get("data_freshness"),
            confidence_threshold=constraints_data.get("confidence_threshold", 0.7)
        )

        reasoning_data = parsed_data.get("reasoning_requirements", {})
        reasoning_requirements = ReasoningRequirements(
            needs_causal_analysis=reasoning_data.get("needs_causal_analysis", False),
            needs_trend_analysis=reasoning_data.get("needs_trend_analysis", False),
            needs_comparison=reasoning_data.get("needs_comparison", False),
            needs_correlation=reasoning_data.get("needs_correlation", False),
            needs_statistical_analysis=reasoning_data.get("needs_statistical_analysis", False),
            complexity_level=reasoning_data.get("complexity_level", "medium"),
            reasoning_depth=reasoning_data.get("reasoning_depth", 1),
            domain_expertise=reasoning_data.get("domain_expertise", [])
        )

        response_data = parsed_data.get("response_format", {})
        response_format = ResponseFormat(
            include_evidence=response_data.get("include_evidence", True),
            include_confidence=response_data.get("include_confidence", True),
            include_methodology=response_data.get("include_methodology", False),
            preferred_style=response_data.get("preferred_style", "balanced"),
            max_length=response_data.get("max_length"),
            format_type=response_data.get("format_type", "narrative"),
            language_preference=response_data.get("language_preference")
        )

        # Generate query ID
        query_id = f"{language}_{query_type.value}_{hash(original_query) % 10000:04d}"

        return StructuredQuery(
            query_id=query_id,
            original_query=original_query,
            language=language,
            query_type=query_type,
            intent=intent,
            constraints=constraints,
            reasoning_requirements=reasoning_requirements,
            response_format=response_format,
            parsing_model=self.model_name,
            parsing_timestamp=datetime.now().isoformat(),
            version="1.0"
        )

    def _validate_query_type(self, query_type_str: str) -> QueryType:
        """Validate and convert query type string to enum"""
        try:
            return QueryType(query_type_str.lower())
        except ValueError:
            logger.warning(f"Invalid query type: {query_type_str}, defaulting to factual")
            return QueryType.FACTUAL

    def _validate_primary_action(self, action_str: str) -> PrimaryAction:
        """Validate and convert primary action string to enum"""
        try:
            return PrimaryAction(action_str.lower())
        except ValueError:
            logger.warning(f"Invalid primary action: {action_str}, defaulting to find")
            return PrimaryAction.FIND

    async def parse_batch(self, queries: List[str]) -> List[QueryParsingResult]:
        """Parse multiple queries in batch"""
        results = []
        for query in queries:
            result = await self.parse_query(query)
            results.append(result)

        return results

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return ["en", "zh", "ja", "ko", "fr", "de", "es"]

    def get_parsing_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics (for monitoring)"""
        # This would track parsing success rates, common failures, etc.
        return {
            "supported_languages": self.get_supported_languages(),
            "model_used": self.model_name,
            "parsing_features": [
                "intent_extraction",
                "constraint_analysis",
                "reasoning_requirements",
                "response_format_detection"
            ]
        }


# Fallback parser for when LLM parsing fails
class FallbackQueryParser:
    """Simple keyword-based fallback parser"""

    def __init__(self):
        self.keywords = {
            "visual": ["圖表", "圖片", "圖形", "chart", "graph", "image", "visual", "show", "display"],
            "temporal": ["時間", "日期", "月份", "年份", "季度", "when", "time", "period", "quarter"],
            "analytical": ["為什麼", "如何", "分析", "原因", "why", "how", "analyze", "reason"],
            "comparative": ["比較", "差異", "對比", "compare", "difference", "vs", "versus"]
        }

    def parse_query(self, query: str) -> QueryParsingResult:
        """Simple keyword-based parsing as fallback"""
        query_lower = query.lower()

        # Determine query type based on keywords
        query_type = QueryType.FACTUAL
        max_matches = 0

        for type_name, keywords in self.keywords.items():
            matches = sum(1 for keyword in keywords if keyword in query_lower)
            if matches > max_matches:
                max_matches = matches
                try:
                    query_type = QueryType(type_name)
                except ValueError:
                    query_type = QueryType.FACTUAL

        # Create basic structured query
        structured_query = StructuredQuery(
            query_id=f"fallback_{hash(query) % 10000:04d}",
            original_query=query,
            language="unknown",
            query_type=query_type,
            intent=QueryIntent(primary_action=PrimaryAction.FIND),
            constraints=QueryConstraints(),
            reasoning_requirements=ReasoningRequirements(),
            response_format=ResponseFormat(),
            parsing_model="fallback_parser",
            parsing_timestamp=datetime.now().isoformat(),
            version="1.0"
        )

        return QueryParsingResult(
            success=True,
            structured_query=structured_query,
            fallback_type="keyword_matching",
            processing_time=0.01
        )
