"""Azure OpenAI provider implementation."""

from typing import Optional, List, Any, Type

try:
    from openai import AzureOpenAI
    import tiktoken  # type: ignore[import-not-found]
except ImportError:
    AzureOpenAI = None  # type: ignore[assignment,misc]
    tiktoken = None

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__)


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI API provider implementation."""

    encoding: Any  # tiktoken encoding object or None

    def __init__(self, config: LLMConfig):
        """
        Initialize Azure OpenAI provider.

        Args:
            config: LLM configuration

        Raises:
            ImportError: If openai package not installed
            ValueError: If required Azure config missing
        """
        if AzureOpenAI is None:
            raise ImportError("openai package not installed. Install with: pip install openai")

        super().__init__(config)

        # Validate Azure-specific config
        if not config.api_key:
            raise ValueError("Azure OpenAI API key is required")

        if not config.api_base:
            raise ValueError("Azure OpenAI api_base (endpoint URL) is required")

        if not config.api_version:
            raise ValueError("Azure OpenAI api_version is required")

        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=config.api_key,
            azure_endpoint=config.api_base,
            api_version=config.api_version,
            timeout=config.timeout,
        )

        # Initialize tokenizer for token counting
        try:
            if tiktoken is not None:
                self.encoding = tiktoken.encoding_for_model(self.model)
            else:
                self.encoding = None
        except KeyError:
            logger.warning(f"Unknown model {self.model}, using cl100k_base encoding")
            if tiktoken is not None:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            else:
                self.encoding = None

        logger.info(
            f"Initialized Azure OpenAI provider "
            f"(model: {self.model}, endpoint: {config.api_base})"
        )

    def generate_completion(
        self, prompt: str, system_message: Optional[str] = None, **kwargs: Any
    ) -> LLMResponse:
        """
        Generate completion using Azure OpenAI API.

        Args:
            prompt: User prompt
            system_message: System message (optional)
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content

        Raises:
            Exception: On API errors
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        params = {
            "model": self.model,  # This is the deployment name in Azure
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        logger.debug(f"Calling Azure OpenAI API with deployment: {self.model}")

        try:
            response = self.client.chat.completions.create(**params)

            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info(
                f"Azure OpenAI response received "
                f"(tokens: {tokens_used}, finish: {finish_reason})"
            )

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            logger.error(f"Azure OpenAI API error: {e}")
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
                return len(text) // 4
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            return len(text) // 4

    def validate_config(self) -> List[str]:
        """
        Validate Azure OpenAI-specific configuration.

        Returns:
            List of validation errors
        """
        errors = super().validate_config()

        if not self.config.api_key:
            errors.append("Azure OpenAI API key is required")

        if not self.config.api_base:
            errors.append("Azure OpenAI api_base (endpoint URL) is required")

        if not self.config.api_version:
            errors.append("Azure OpenAI api_version is required")

        return errors

    def close(self) -> None:
        """Close Azure OpenAI client."""
        if hasattr(self, "client"):
            self.client.close()
        super().close()


# Register provider
LLMProviderFactory.register("azure_openai", AzureOpenAIProvider)
