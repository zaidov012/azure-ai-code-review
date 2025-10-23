"""OpenAI provider implementation."""

from typing import Optional, List, Any, Type

try:
    from openai import OpenAI
    import tiktoken  # type: ignore[import-not-found]
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]
    tiktoken = None

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    encoding: Any  # tiktoken encoding object or None

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
            if tiktoken is not None:
                self.encoding = tiktoken.encoding_for_model(self.model)
            else:
                self.encoding = None
        except KeyError:
            # Fallback to cl100k_base for unknown models
            logger.warning(f"Unknown model {self.model}, using cl100k_base encoding")
            if tiktoken is not None:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            else:
                self.encoding = None

        logger.info(f"Initialized OpenAI provider with model: {self.model}")

    def _is_reasoning_model(self) -> bool:
        """
        Check if the model is a reasoning model (GPT-5, o1, etc.).
        These models don't accept temperature and max_tokens parameters.

        Returns:
            True if it's a reasoning model
        """
        reasoning_models = ["gpt-5", "o1-preview", "o1-mini", "o1"]
        return any(self.model.startswith(model) for model in reasoning_models)

    def generate_completion(
        self, prompt: str, system_message: Optional[str] = None, **kwargs: Any
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
        }

        # GPT-5 and newer models don't accept temperature and max_tokens
        # Only add these parameters for older models
        if not self._is_reasoning_model():
            params["temperature"] = kwargs.get("temperature", self.temperature)
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        else:
            logger.debug(f"Skipping temperature and max_tokens for reasoning model: {self.model}")

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
            if self.encoding is not None:
                tokens = self.encoding.encode(text)
                return len(tokens)
            else:
                # Fallback: rough estimate (1 token ≈ 4 characters)
                return len(text) // 4
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
            "gpt-5",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4-0125-preview",
            "gpt-4-1106-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "o1-preview",
            "o1-mini",
        ]

        if self.model not in valid_models and not self.model.startswith(("gpt-", "o1-")):
            logger.warning(
                f"Model '{self.model}' not in known models list. "
                "It may still work if it's a valid OpenAI model."
            )

        return errors

    def close(self) -> None:
        """Close OpenAI client."""
        if hasattr(self, "client"):
            self.client.close()
        super().close()


# Register provider
LLMProviderFactory.register("openai", OpenAIProvider)
