"""Ollama provider implementation for local LLM hosting."""

from typing import Optional, List
import logging
import requests

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider implementation."""
    
    def __init__(self, config: LLMConfig):
        """
        Initialize Ollama provider.
        
        Args:
            config: LLM configuration
        """
        super().__init__(config)
        
        # Default Ollama endpoint
        self.api_base = config.api_base or "http://localhost:11434"
        
        # Ensure endpoint doesn't end with slash
        self.api_base = self.api_base.rstrip('/')
        
        logger.info(
            f"Initialized Ollama provider "
            f"(model: {self.model}, endpoint: {self.api_base})"
        )
    
    def generate_completion(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Ollama API.
        
        Args:
            prompt: User prompt
            system_message: System message (optional)
            **kwargs: Additional Ollama parameters
        
        Returns:
            LLMResponse with generated content
        
        Raises:
            Exception: On API errors
        """
        url = f"{self.api_base}/api/generate"
        
        # Build prompt with system message if provided
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            }
        }
        
        logger.debug(f"Calling Ollama API at {url} with model: {self.model}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            content = data.get("response", "")
            tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
            
            logger.info(f"Ollama response received (tokens: {tokens_used})")
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=tokens_used,
                finish_reason="stop" if data.get("done") else "length",
                raw_response=data
            )
            
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Failed to connect to Ollama at {self.api_base}. "
                "Make sure Ollama is running."
            )
            raise
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens (rough estimate for Ollama).
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Estimated number of tokens
        """
        # Rough estimate: ~4 characters per token
        # Different models may have different tokenizers
        return len(text) // 4
    
    def validate_config(self) -> List[str]:
        """
        Validate Ollama-specific configuration.
        
        Returns:
            List of validation errors
        """
        errors = super().validate_config()
        
        # Ollama doesn't require API key
        # Just validate endpoint is accessible
        
        return errors
    
    def test_connection(self) -> bool:
        """
        Test connection to Ollama server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Check if Ollama is running
            url = f"{self.api_base}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            # Check if model is available
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            
            if self.model in models:
                logger.info(f"✅ Ollama connection successful, model '{self.model}' available")
                return True
            else:
                logger.warning(
                    f"⚠️  Ollama is running but model '{self.model}' not found. "
                    f"Available models: {', '.join(models)}"
                )
                logger.warning(f"Pull the model with: ollama pull {self.model}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.error(
                f"❌ Cannot connect to Ollama at {self.api_base}. "
                "Make sure Ollama is running."
            )
            return False
        except Exception as e:
            logger.error(f"❌ Ollama connection test failed: {e}")
            return False


# Register provider
LLMProviderFactory.register("ollama", OllamaProvider)
