"""LLM integration module for AI-powered code reviews."""

from .base import LLMProvider, LLMResponse, LLMProviderFactory, CodeReviewRequest
from .openai_provider import OpenAIProvider
from .azure_openai import AzureOpenAIProvider
from .anthropic_provider import AnthropicProvider
from .ollama_provider import OllamaProvider
from .prompts import CodeReviewPrompts, detect_language
from .parser import ResponseParser
from .review_client import LLMReviewClient, create_review_client

__all__ = [
    # Base classes
    "LLMProvider",
    "LLMResponse",
    "LLMProviderFactory",
    "CodeReviewRequest",
    # Provider implementations
    "OpenAIProvider",
    "AzureOpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    # Prompts
    "CodeReviewPrompts",
    "detect_language",
    # Parser
    "ResponseParser",
    # Main client
    "LLMReviewClient",
    "create_review_client",
]
