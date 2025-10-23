"""Base abstract interface for LLM providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from ..config.config import LLMConfig
from ..azure_devops.models import ReviewComment
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class CodeReviewRequest:
    """Request for code review."""
    file_path: str
    file_content: str
    diff_content: Optional[str] = None
    pr_title: str = ""
    pr_description: str = ""
    language: Optional[str] = None
    review_scope: Optional[List[str]] = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All LLM provider implementations must inherit from this class
    and implement the required methods.
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider.
        
        Args:
            config: LLM configuration
        """
        self.config = config
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
        self.timeout = config.timeout
        
        logger.info(
            f"Initialized {self.__class__.__name__} "
            f"(model: {self.model}, temp: {self.temperature})"
        )
    
    @abstractmethod
    def generate_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from LLM.
        
        Args:
            prompt: User prompt
            system_message: System message/instruction (optional)
            **kwargs: Provider-specific parameters
        
        Returns:
            LLMResponse with generated content
        
        Raises:
            Exception: On API errors
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Number of tokens
        """
        pass
    
    def validate_config(self) -> List[str]:
        """
        Validate provider-specific configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.model:
            errors.append("Model is required")
        
        if self.temperature < 0 or self.temperature > 2:
            errors.append("Temperature must be between 0 and 2")
        
        if self.max_tokens <= 0:
            errors.append("Max tokens must be positive")
        
        return errors
    
    def test_connection(self) -> bool:
        """
        Test connection to LLM provider.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing connection to {self.__class__.__name__}...")
            
            # Try a simple completion
            response = self.generate_completion(
                prompt="Hello, please respond with 'OK'.",
                system_message="You are a helpful assistant."
            )
            
            if response.content:
                logger.info("✅ Connection successful")
                return True
            else:
                logger.error("❌ Connection failed: empty response")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def optimize_prompt(self, prompt: str, max_length: Optional[int] = None) -> str:
        """
        Optimize prompt to fit within token limits.
        
        Args:
            prompt: Original prompt
            max_length: Maximum allowed tokens (uses config if not specified)
        
        Returns:
            Optimized prompt
        """
        if max_length is None:
            # Reserve space for completion
            max_length = self.max_tokens // 2
        
        token_count = self.count_tokens(prompt)
        
        if token_count <= max_length:
            return prompt
        
        logger.warning(
            f"Prompt too long ({token_count} tokens). "
            f"Truncating to {max_length} tokens."
        )
        
        # Simple truncation (can be improved with smarter strategies)
        # Estimate characters per token (rough average: 4 chars/token)
        target_chars = max_length * 4
        
        if len(prompt) > target_chars:
            return prompt[:target_chars] + "\n\n[Content truncated...]"
        
        return prompt
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """
        Close connections and cleanup resources.
        Subclasses can override if needed.
        """
        logger.debug(f"Closing {self.__class__.__name__}")


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register(cls, provider_name: str, provider_class: type):
        """
        Register a provider class.
        
        Args:
            provider_name: Name of the provider
            provider_class: Provider class
        """
        cls._providers[provider_name.lower()] = provider_class
        logger.debug(f"Registered LLM provider: {provider_name}")
    
    @classmethod
    def create(cls, config: LLMConfig) -> LLMProvider:
        """
        Create LLM provider instance from configuration.
        
        Args:
            config: LLM configuration
        
        Returns:
            LLM provider instance
        
        Raises:
            ValueError: If provider not found
        """
        provider_name = config.provider.value
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        logger.info(f"Creating {provider_class.__name__} instance")
        
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """
        List all registered providers.
        
        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
