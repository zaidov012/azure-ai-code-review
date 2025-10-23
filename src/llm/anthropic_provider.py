"""Anthropic (Claude) provider implementation."""

from typing import Optional, List

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider implementation."""

    def __init__(self, config: LLMConfig):
        """
        Initialize Anthropic provider.

        Args:
            config: LLM configuration

        Raises:
            ImportError: If anthropic package not installed
            ValueError: If API key not provided
        """
        if Anthropic is None:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )

        super().__init__(config)

        if not config.api_key:
            raise ValueError("Anthropic API key is required")

        # Initialize Anthropic client
        self.client = Anthropic(
            api_key=config.api_key,
            timeout=config.timeout,
        )

        logger.info(f"Initialized Anthropic provider with model: {self.model}")

    def generate_completion(
        self, prompt: str, system_message: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate completion using Anthropic API.

        Args:
            prompt: User prompt
            system_message: System message (optional)
            **kwargs: Additional Anthropic parameters

        Returns:
            LLMResponse with generated content

        Raises:
            Exception: On API errors
        """
        params = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add system message if provided
        if system_message:
            params["system"] = system_message

        logger.debug(f"Calling Anthropic API with model: {self.model}")

        try:
            response = self.client.messages.create(**params)

            # Extract text from response
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text

            # Get token usage
            tokens_used = 0
            if hasattr(response, "usage"):
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

            finish_reason = response.stop_reason if hasattr(response, "stop_reason") else "unknown"

            logger.info(
                f"Anthropic response received " f"(tokens: {tokens_used}, finish: {finish_reason})"
            )

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens (rough estimate for Anthropic).

        Anthropic uses a similar tokenization to GPT models.
        This is a rough estimate.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated number of tokens
        """
        # Rough estimate: ~4 characters per token
        # This is an approximation since Anthropic's tokenizer
        # is not publicly available
        return len(text) // 4

    def validate_config(self) -> List[str]:
        """
        Validate Anthropic-specific configuration.

        Returns:
            List of validation errors
        """
        errors = super().validate_config()

        if not self.config.api_key:
            errors.append("Anthropic API key is required")

        # Validate model name
        valid_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
        ]

        if self.model not in valid_models and not self.model.startswith("claude-"):
            logger.warning(
                f"Model '{self.model}' not in known models list. "
                "It may still work if it's a valid Anthropic model."
            )

        return errors


# Register provider
LLMProviderFactory.register("anthropic", AnthropicProvider)
