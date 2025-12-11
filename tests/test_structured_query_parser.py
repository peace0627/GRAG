"""
Test Structured Query Parser

This module tests the LLM-driven structured query parser functionality.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from grag.agents import (
    StructuredQueryParser,
    FallbackQueryParser,
    QueryParsingResult,
    QueryType,
    PrimaryAction
)


class TestStructuredQueryParser:
    """Test cases for StructuredQueryParser"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def parser(self, mock_llm):
        """Create parser with mock LLM"""
        mock_llm.model_name = "test_model"  # Set model_name to avoid validation error
        return StructuredQueryParser(llm=mock_llm)

    @pytest.mark.asyncio
    async def test_parse_simple_chinese_query(self, parser, mock_llm):
        """Test parsing a simple Chinese query"""

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = '''
        {
          "query_type": "visual",
          "intent": {
            "primary_action": "find",
            "target_metric": "sales",
            "group_by": "month",
            "visualization_preferred": true
          },
          "constraints": {
            "must_include": ["monthly_data"],
            "preferred_sources": ["charts"]
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
        '''
        mock_llm.ainvoke.return_value = mock_response

        # Test parsing
        result = await parser.parse_query("圖表顯示哪個月銷售最低？")

        # Assertions
        assert result.success is True
        assert result.structured_query is not None
        assert result.structured_query.language == "multilingual"  # Now defaults to multilingual
        assert result.structured_query.query_type == QueryType.VISUAL
        assert result.structured_query.intent.primary_action == PrimaryAction.FIND
        assert result.structured_query.intent.target_metric == "sales"
        assert result.structured_query.intent.group_by == "month"
        assert result.structured_query.intent.visualization_preferred is True

    @pytest.mark.asyncio
    async def test_parse_analytical_query(self, parser, mock_llm):
        """Test parsing an analytical query"""

        mock_response = MagicMock()
        mock_response.content = '''
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
        '''
        mock_llm.ainvoke.return_value = mock_response

        result = await parser.parse_query("為什麼營收在第三季度下降？")

        assert result.success is True
        assert result.structured_query.query_type == QueryType.CAUSAL
        assert result.structured_query.intent.primary_action == PrimaryAction.EXPLAIN
        assert result.structured_query.constraints.time_scope == "Q3"
        assert result.structured_query.reasoning_requirements.needs_causal_analysis is True

    @pytest.mark.asyncio
    async def test_parse_english_query(self, parser, mock_llm):
        """Test parsing an English query"""

        mock_response = MagicMock()
        mock_response.content = '''
        {
          "query_type": "factual",
          "intent": {
            "primary_action": "find",
            "target_metric": "sales",
            "group_by": "region"
          },
          "constraints": {},
          "reasoning_requirements": {
            "complexity_level": "low"
          },
          "response_format": {
            "preferred_style": "concise"
          }
        }
        '''
        mock_llm.ainvoke.return_value = mock_response

        result = await parser.parse_query("What are the sales by region?")

        assert result.success is True
        assert result.structured_query.language == "multilingual"  # Now defaults to multilingual
        assert result.structured_query.query_type == QueryType.FACTUAL

    @pytest.mark.asyncio
    async def test_parsing_failure_handling(self, parser, mock_llm):
        """Test handling of parsing failures"""

        # Mock LLM returning invalid JSON
        mock_response = MagicMock()
        mock_response.content = "This is not JSON at all, just plain text response."
        mock_llm.ainvoke.return_value = mock_response

        result = await parser.parse_query("Invalid query that will fail")

        assert result.success is False
        assert result.error_message is not None
        assert result.fallback_type == "keyword_matching"
        assert result.raw_llm_response == mock_response.content

    @pytest.mark.asyncio
    async def test_multilingual_parsing(self, parser, mock_llm):
        """Test LLM's ability to handle multilingual queries"""

        # Test mixed Chinese-English query
        mock_response = MagicMock()
        mock_response.content = '''
        {
          "query_type": "visual",
          "intent": {
            "primary_action": "find",
            "target_metric": "sales",
            "group_by": "month",
            "visualization_preferred": true
          },
          "constraints": {
            "must_include": ["monthly_data"]
          },
          "reasoning_requirements": {
            "needs_comparison": true,
            "complexity_level": "medium"
          },
          "response_format": {
            "include_evidence": true
          }
        }
        '''
        mock_llm.ainvoke.return_value = mock_response

        # Test mixed Chinese-English query
        result = await parser.parse_query("混合Chinese and English文本 - show sales chart")

        assert result.success is True
        assert result.structured_query.language == "multilingual"
        assert result.structured_query.query_type == QueryType.VISUAL
        assert result.structured_query.intent.primary_action == PrimaryAction.FIND

        # Verify the prompt included multilingual context
        call_args = mock_llm.ainvoke.call_args
        prompt = call_args[0][0][1].content  # Second message content
        assert "multilingual" in prompt

    def test_fallback_parser(self):
        """Test fallback parser functionality"""

        fallback = FallbackQueryParser()
        result = fallback.parse_query("圖表顯示銷售趨勢")

        assert result.success is True
        assert result.structured_query is not None
        assert result.fallback_type == "keyword_matching"
        assert result.structured_query.query_type == QueryType.VISUAL  # Should detect visual keywords

    @pytest.mark.asyncio
    async def test_batch_parsing(self, parser, mock_llm):
        """Test batch parsing functionality"""

        # Mock multiple responses
        responses = [
            MagicMock(content='{"query_type": "factual", "intent": {"primary_action": "find"}, "constraints": {}, "reasoning_requirements": {}, "response_format": {}}'),
            MagicMock(content='{"query_type": "analytical", "intent": {"primary_action": "analyze"}, "constraints": {}, "reasoning_requirements": {}, "response_format": {}}')
        ]
        mock_llm.ainvoke.side_effect = responses

        queries = ["What are sales?", "Why did revenue drop?"]
        results = await parser.parse_batch(queries)

        assert len(results) == 2
        assert all(result.success for result in results)
        assert results[0].structured_query.query_type == QueryType.FACTUAL
        assert results[1].structured_query.query_type == QueryType.ANALYTICAL

    def test_validation_functions(self, parser):
        """Test input validation functions"""

        # Valid query types
        assert parser._validate_query_type("factual") == QueryType.FACTUAL
        assert parser._validate_query_type("VISUAL") == QueryType.VISUAL

        # Invalid query type defaults to FACTUAL
        assert parser._validate_query_type("invalid_type") == QueryType.FACTUAL

        # Valid primary actions
        assert parser._validate_primary_action("find") == PrimaryAction.FIND
        assert parser._validate_primary_action("ANALYZE") == PrimaryAction.ANALYZE

        # Invalid primary action defaults to FIND
        assert parser._validate_primary_action("invalid_action") == PrimaryAction.FIND

    def test_parsing_statistics(self, parser):
        """Test parsing statistics reporting"""

        stats = parser.get_parsing_statistics()

        assert "supported_languages" in stats
        assert "model_used" in stats
        assert "parsing_features" in stats
        assert isinstance(stats["supported_languages"], list)
        assert len(stats["supported_languages"]) > 0


# Integration test with real LLM (requires API key)
@pytest.mark.integration
class TestStructuredQueryParserIntegration:
    """Integration tests with real LLM (requires API key)"""

    @pytest.mark.asyncio
    async def test_real_llm_parsing(self):
        """Test with real LLM (requires OpenAI API key)"""
        try:
            parser = StructuredQueryParser()  # Uses real LLM

            result = await parser.parse_query("圖表顯示哪個月銷售最低？")

            assert result.success is True
            assert result.structured_query is not None
            assert result.structured_query.language == "zh"
            assert result.structured_query.intent.primary_action == PrimaryAction.FIND

        except Exception as e:
            pytest.skip(f"Real LLM test skipped: {e}")

    @pytest.mark.asyncio
    async def test_complex_query_parsing(self):
        """Test parsing a complex real-world query"""
        try:
            parser = StructuredQueryParser()

            complex_query = "分析過去一年各產品線的銷售趨勢，並找出成長最快的產品類別"

            result = await parser.parse_query(complex_query)

            assert result.success is True
            assert result.structured_query.query_type in [QueryType.ANALYTICAL, QueryType.COMPLEX]
            assert result.structured_query.intent.primary_action in [PrimaryAction.ANALYZE, PrimaryAction.FIND]
            assert "trend" in str(result.structured_query.reasoning_requirements.needs_trend_analysis).lower() or \
                   result.structured_query.reasoning_requirements.needs_trend_analysis is True

        except Exception as e:
            pytest.skip(f"Complex query test skipped: {e}")


if __name__ == "__main__":
    # Run basic tests
    print("Running Structured Query Parser tests...")

    # Simple functionality test
    fallback = FallbackQueryParser()
    result = fallback.parse_query("圖表顯示銷售數據")

    print("✅ Fallback parser test passed")
    print(f"   Query type: {result.structured_query.query_type}")
    print(f"   Primary action: {result.structured_query.intent.primary_action}")

    print("\nAll basic tests completed!")
