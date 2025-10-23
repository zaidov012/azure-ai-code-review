"""Configuration management for Azure DevOps AI PR Review Extension."""

import os
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4000
    timeout: int = 500
    custom_headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate and convert provider string to enum."""
        if isinstance(self.provider, str):
            self.provider = LLMProvider(self.provider.lower())


@dataclass
class AzureDevOpsConfig:
    """Configuration for Azure DevOps connection."""

    organization_url: str
    project: str
    repository: str
    pat_token: Optional[str] = None
    verify_ssl: bool = True
    timeout: int = 30

    def __post_init__(self) -> None:
        """Load PAT token from environment if not provided."""
        if not self.pat_token:
            self.pat_token = os.environ.get("AZDO_PERSONAL_ACCESS_TOKEN")


@dataclass
class ReviewConfig:
    """Configuration for PR review behavior."""

    review_scope: List[str] = field(
        default_factory=lambda: [
            "code_quality",
            "security",
            "performance",
            "best_practices",
            "bugs",
        ]
    )
    file_extensions: List[str] = field(
        default_factory=lambda: [".py", ".js", ".ts", ".java", ".cs", ".go", ".rb", ".php"]
    )
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["*/tests/*", "*/test/*", "*.min.js", "package-lock.json", "*.lock"]
    )
    max_files_per_review: int = 50
    max_diff_size_kb: int = 500
    comment_style: str = "constructive"  # constructive, concise, detailed
    severity_levels: List[str] = field(
        default_factory=lambda: ["critical", "major", "minor", "suggestion"]
    )


@dataclass
class Config:
    """Main configuration class."""

    llm: LLMConfig
    azure_devops: AzureDevOpsConfig
    review: ReviewConfig = field(default_factory=ReviewConfig)
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """Create Config instance from dictionary."""
        llm_config = LLMConfig(**config_dict.get("llm", {}))
        azdo_config = AzureDevOpsConfig(**config_dict.get("azure_devops", {}))
        review_config = ReviewConfig(**config_dict.get("review", {}))

        return cls(
            llm=llm_config,
            azure_devops=azdo_config,
            review=review_config,
            log_level=config_dict.get("log_level", "INFO"),
        )

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate LLM config
        if not self.llm.model:
            errors.append("LLM model is required")

        if self.llm.provider in [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]:
            if not self.llm.api_key:
                errors.append(f"{self.llm.provider.value} requires an API key")

        if self.llm.provider == LLMProvider.AZURE_OPENAI:
            if not self.llm.api_base:
                errors.append("Azure OpenAI requires api_base URL")
            if not self.llm.api_version:
                errors.append("Azure OpenAI requires api_version")

        # Validate Azure DevOps config
        if not self.azure_devops.organization_url:
            errors.append("Azure DevOps organization URL is required")

        if not self.azure_devops.project:
            errors.append("Azure DevOps project is required")

        if not self.azure_devops.repository:
            errors.append("Azure DevOps repository is required")

        if not self.azure_devops.pat_token:
            errors.append(
                "Azure DevOps PAT token is required "
                "(set in config or AZDO_PERSONAL_ACCESS_TOKEN env var)"
            )

        return errors


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file or environment variables.

    Args:
        config_path: Path to configuration file. If not provided, looks for
                    'config.yaml' in current directory or path from CONFIG_PATH env var.

    Returns:
        Config: Configuration instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    if not config_path:
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_dict = yaml.safe_load(f)

    config = Config.from_dict(config_dict)

    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(
            "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return config


def load_config_from_env() -> Config:
    """
    Load configuration from environment variables only.
    Useful for CI/CD pipelines.

    Environment variables:
        LLM_PROVIDER: LLM provider (openai, azure_openai, anthropic, ollama)
        LLM_MODEL: Model name
        LLM_API_KEY: API key for LLM provider
        LLM_API_BASE: Base URL for API (for Azure OpenAI or custom endpoints)
        LLM_API_VERSION: API version (for Azure OpenAI)
        AZDO_ORG_URL: Azure DevOps organization URL
        AZDO_PROJECT: Project name
        AZDO_REPOSITORY: Repository name
        AZDO_PERSONAL_ACCESS_TOKEN: Personal Access Token
    """
    config_dict = {
        "llm": {
            "provider": os.environ.get("LLM_PROVIDER", "openai"),
            "model": os.environ.get("LLM_MODEL", "gpt-4"),
            "api_key": os.environ.get("LLM_API_KEY"),
            "api_base": os.environ.get("LLM_API_BASE"),
            "api_version": os.environ.get("LLM_API_VERSION"),
            "temperature": float(os.environ.get("LLM_TEMPERATURE", "0.3")),
            "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "4000")),
        },
        "azure_devops": {
            "organization_url": os.environ.get("AZDO_ORG_URL"),
            "project": os.environ.get("AZDO_PROJECT"),
            "repository": os.environ.get("AZDO_REPOSITORY"),
            "pat_token": os.environ.get("AZDO_PERSONAL_ACCESS_TOKEN"),
            "verify_ssl": os.environ.get("AZDO_VERIFY_SSL", "true").lower() == "true",
        },
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    }

    config = Config.from_dict(config_dict)

    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(
            "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return config
