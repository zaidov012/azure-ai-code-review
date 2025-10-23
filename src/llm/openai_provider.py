"""OpenAI provider implementation."""

from typing import Optional, List

try:
    from openai import OpenAI
    import tiktoken
except ImportError:
    OpenAI = None
    tiktoken = None

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI provider.

        Args:
            config: LLM configuration

        Raises:
            ImportError: If openai package not installed
            ValueError: If API key not provided
        """
        if OpenAI is None:
            raise ImportError("openai package not installed. Install with: pip install openai")

        super().__init__(config)

        if not config.api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=config.api_key,
            timeout=config.timeout,
        )

        # Initialize tokenizer for token counting
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            logger.warning(f"Unknown model {self.model}, using cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.info(f"Initialized OpenAI provider with model: {self.model}")

    def generate_completion(
        self, prompt: str, system_message: Optional[str] = None, **kwargs
    ) -> LLMResponse:
        """
        Generate completion using OpenAI API.

        Args:
            prompt: User prompt
            system_message: System message (optional)
            **kwargs: Additional OpenAI parameters

        Returns:
            LLMResponse with generated content

        Raises:
            Exception: On API errors
        """
        messages = []

        # Add system message if provided
        if system_message:
            messages.append({"role": "system", "content": system_message})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        # Prepare API parameters
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        # Add optional parameters
        if "response_format" in kwargs:
            params["response_format"] = kwargs["response_format"]

        logger.debug(f"Calling OpenAI API with model: {self.model}")

        try:
            response = self.client.chat.completions.create(**params)

            # Extract response content
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Count tokens used
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                f"OpenAI response received " f"(tokens: {tokens_used}, finish: {finish_reason})"
            )

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        Count tokens using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def validate_config(self) -> List[str]:
        """
        Validate OpenAI-specific configuration.

        Returns:
            List of validation errors
        """
        errors = super().validate_config()

        if not self.config.api_key:
            errors.append("OpenAI API key is required")

        # Validate model name
        valid_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]

        if self.model not in valid_models and not self.model.startswith("gpt-"):
            logger.warning(
                f"Model '{self.model}' not in known models list. "
                "It may still work if it's a valid OpenAI model."
            )

        return errors

    def close(self):
        """Close OpenAI client."""
        if hasattr(self, "client"):
            self.client.close()
        super().close()


# Register provider
LLMProviderFactory.register("openai", OpenAIProvider)
