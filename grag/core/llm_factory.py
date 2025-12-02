"""
LLM Factory - Centralized LLM instance management

This module provides a centralized factory for creating LLM instances
with proper configuration management and provider abstraction.
"""

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
# Future: from langchain_anthropic import ChatAnthropic
# Future: from langchain_ollama import ChatOllama

from .config import get_config

logger = logging.getLogger(__name__)


class LLMFactory:
    """Centralized factory for LLM instance creation"""

    @staticmethod
    def create_planner_llm() -> ChatOpenAI:
        """Create LLM instance for query planning tasks

        Query planning needs:
        - High precision and consistency
        - Good reasoning capabilities
        - Cost-effective model
        """
        config = get_config()

        return ChatOpenAI(
            model=config.planner_llm_model,
            temperature=config.llm_temperature,  # Low temperature for consistency
            max_tokens=config.llm_max_tokens,
            api_key=config.openai_api_key or None  # Will use env var if not set
        )

    @staticmethod
    def create_reasoner_llm() -> ChatOpenAI:
        """Create LLM instance for reasoning and analysis tasks

        Reasoning tasks need:
        - Strong analytical capabilities
        - Good context understanding
        - Balanced performance/cost
        """
        config = get_config()

        return ChatOpenAI(
            model=config.reasoner_llm_model,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
            api_key=config.openai_api_key or None
        )

    @staticmethod
    def create_answerer_llm() -> ChatOpenAI:
        """Create LLM instance for final answer generation

        Answer generation needs:
        - High quality and natural responses
        - Good language understanding
        - Slightly higher creativity for better UX
        """
        config = get_config()

        return ChatOpenAI(
            model=config.answerer_llm_model,
            temperature=config.answerer_temperature,  # Slightly higher for natural responses
            max_tokens=config.llm_max_tokens * 2,  # Answers can be longer
            api_key=config.openai_api_key or None
        )

    @staticmethod
    def create_query_parser_llm() -> ChatOpenAI:
        """Create LLM instance for structured query parsing

        Query parsing needs:
        - Excellent understanding of natural language
        - Consistent structured output
        - High precision in JSON generation
        """
        config = get_config()

        return ChatOpenAI(
            model=config.query_parser_llm_model,
            temperature=config.query_parser_temperature,  # Very low for consistent parsing
            max_tokens=config.llm_max_tokens,
            api_key=config.openai_api_key or None
        )

    @staticmethod
    def create_default_llm(model: Optional[str] = None,
                          temperature: Optional[float] = None) -> ChatOpenAI:
        """Create default LLM instance with global settings"""
        config = get_config()

        return ChatOpenAI(
            model=model or config.llm_model,
            temperature=temperature or config.llm_temperature,
            max_tokens=config.llm_max_tokens,
            api_key=config.openai_api_key or None
        )

    @staticmethod
    def get_llm_config_summary() -> dict:
        """Get summary of current LLM configuration"""
        config = get_config()

        return {
            "provider": config.llm_provider,
            "default_model": config.llm_model,
            "agent_models": {
                "planner": config.planner_llm_model,
                "reasoner": config.reasoner_llm_model,
                "answerer": config.answerer_llm_model,
                "query_parser": config.query_parser_llm_model
            },
            "temperatures": {
                "default": config.llm_temperature,
                "query_parser": config.query_parser_temperature,
                "answerer": config.answerer_temperature
            },
            "has_api_key": bool(config.openai_api_key)
        }

    @staticmethod
    def validate_llm_connectivity() -> dict:
        """Validate LLM connectivity and configuration"""
        result = {
            "status": "unknown",
            "models_available": [],
            "errors": []
        }

        try:
            config = get_config()

            # Test basic LLM creation
            llm = LLMFactory.create_default_llm()
            result["models_available"].append(config.llm_model)

            # Test planner LLM
            planner_llm = LLMFactory.create_planner_llm()
            result["models_available"].append(config.planner_llm_model)

            # Test other LLMs
            reasoner_llm = LLMFactory.create_reasoner_llm()
            result["models_available"].append(config.reasoner_llm_model)

            answerer_llm = LLMFactory.create_answerer_llm()
            result["models_available"].append(config.answerer_llm_model)

            query_parser_llm = LLMFactory.create_query_parser_llm()
            result["models_available"].append(config.query_parser_llm_model)

            # Remove duplicates
            result["models_available"] = list(set(result["models_available"]))
            result["status"] = "operational"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            logger.error(f"LLM connectivity validation failed: {e}")

        return result


# Convenience functions for backward compatibility
def create_planner_llm() -> ChatOpenAI:
    """Convenience function for creating planner LLM"""
    return LLMFactory.create_planner_llm()

def create_reasoner_llm() -> ChatOpenAI:
    """Convenience function for creating reasoner LLM"""
    return LLMFactory.create_reasoner_llm()

def create_answerer_llm() -> ChatOpenAI:
    """Convenience function for creating answerer LLM"""
    return LLMFactory.create_answerer_llm()

def create_query_parser_llm() -> ChatOpenAI:
    """Convenience function for creating query parser LLM"""
    return LLMFactory.create_query_parser_llm()

def create_default_llm(model: Optional[str] = None,
                      temperature: Optional[float] = None) -> ChatOpenAI:
    """Convenience function for creating default LLM"""
    return LLMFactory.create_default_llm(model, temperature)
