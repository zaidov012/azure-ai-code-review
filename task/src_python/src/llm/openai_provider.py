"""OpenAI provider implementation."""

from typing import Optional, List, Any

try:
    from openai import OpenAI
    import tiktoken  # type: ignore[import-not-found]
except ImportError:
    OpenAI = None  # type: ignore[assignment,misc]
    tiktoken = None

from ..config.config import LLMConfig
from ..utils.logger import setup_logger
from .base import LLMProvider, LLMResponse, LLMProviderFactory

logger = setup_logger(__name__, log_level="DEBUG")


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

        # Determine if this is a reasoning model (GPT-5, o1) that needs longer timeout
        reasoning_models = ["gpt-5", "gpt-5-mini", "o1-preview", "o1-mini", "o1"]
        is_reasoning = any(config.model.startswith(model) for model in reasoning_models)

        # Initialize OpenAI client
        # Reasoning models (GPT-5, o1) need much longer timeouts (5-10 minutes)
        # Regular models use the configured timeout
        effective_timeout = config.timeout
        if is_reasoning:
            # At least 10 minutes for reasoning models
            effective_timeout = max(config.timeout, 600)
            logger.info(
                f"Reasoning model detected ({config.model}), "
                f"using extended timeout of {effective_timeout}s"
            )

        logger.debug(f"Initializing OpenAI client with timeout: {effective_timeout}s")

        # Log API key presence (not the actual key)
        api_key_preview = config.api_key[:10] + "..." if len(config.api_key) > 10 else "***"
        logger.debug(f"API Key prefix: {api_key_preview}")

        self.client = OpenAI(api_key=config.api_key, timeout=effective_timeout, max_retries=0)

        logger.debug("OpenAI client initialized successfully")

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
            logger.debug(
                "Skipping temperature and max_tokens for reasoning model: " f"{self.model}"
            )

        # Add optional parameters
        if "response_format" in kwargs:
            params["response_format"] = kwargs["response_format"]

        # Log the full request for debugging
        logger.info("=== OpenAI API Request ===")
        logger.info(f"Model: {self.model}")
        logger.info(f"Is reasoning model: {self._is_reasoning_model()}")
        logger.info(f"Messages count: {len(messages)}")
        logger.info(f"Request params keys: {list(params.keys())}")
        logger.info(f"Timeout: {self.timeout}s")

        # Log message sizes
        for i, msg in enumerate(messages):
            msg_len = len(msg.get("content", ""))
            logger.debug(f"Message {i} ({msg['role']}): {msg_len} characters")

        logger.info("Calling OpenAI API...")

        try:
            import time

            start_time = time.time()

            response = self.client.chat.completions.create(**params)

            elapsed = time.time() - start_time
            logger.info(f"API call completed in {elapsed:.2f}s")

            # Extract response content
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Count tokens used
            tokens_used = response.usage.total_tokens if response.usage else 0

            logger.info("=== OpenAI API Response ===")
            logger.info(f"Tokens used: {tokens_used}")
            logger.info(f"Finish reason: {finish_reason}")
            logger.info(f"Response length: {len(content) if content else 0} characters")

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                raw_response=(response.model_dump() if hasattr(response, "model_dump") else None),
            )

        except Exception as e:
            logger.error("=== OpenAI API Error ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")

            # Log more details if available
            if hasattr(e, "response"):
                logger.error(f"Response status: " f"{getattr(e.response, 'status_code', 'N/A')}")
                logger.error(f"Response body: {getattr(e.response, 'text', 'N/A')}")

            if hasattr(e, "body"):
                logger.error(f"Error body: {e.body}")

            if hasattr(e, "code"):
                logger.error(f"Error code: {e.code}")

            # Log the full exception details
            import traceback

            logger.error(f"Full traceback:\n{traceback.format_exc()}")

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
