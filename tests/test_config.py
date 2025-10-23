"""Unit tests for configuration module."""

import os
import pytest
import tempfile
import yaml
from src.config.config import (
    Config,
    LLMConfig,
    AzureDevOpsConfig,
    ReviewConfig,
    LLMProvider,
    load_config,
    load_config_from_env,
)


def test_llm_config_creation():
    """Test LLMConfig dataclass creation."""
    config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        api_key="test-key",
    )
    assert config.provider == LLMProvider.OPENAI
    assert config.model == "gpt-4"
    assert config.temperature == 0.3  # default value


def test_llm_config_provider_string_conversion():
    """Test that provider string is converted to enum."""
    config = LLMConfig(
        provider="azure_openai",
        model="gpt-4",
    )
    assert config.provider == LLMProvider.AZURE_OPENAI


def test_azure_devops_config_pat_from_env(monkeypatch):
    """Test PAT token loaded from environment."""
    monkeypatch.setenv("AZDO_PERSONAL_ACCESS_TOKEN", "env-token")
    config = AzureDevOpsConfig(
        organization_url="https://dev.azure.com/test",
        project="TestProject",
        repository="TestRepo",
    )
    assert config.pat_token == "env-token"


def test_config_validation_success():
    """Test successful configuration validation."""
    config = Config(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            api_key="test-key",
        ),
        azure_devops=AzureDevOpsConfig(
            organization_url="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
            pat_token="test-pat",
        ),
    )
    errors = config.validate()
    assert len(errors) == 0


def test_config_validation_missing_llm_model():
    """Test validation fails when LLM model is missing."""
    config = Config(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model="",
            api_key="test-key",
        ),
        azure_devops=AzureDevOpsConfig(
            organization_url="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
            pat_token="test-pat",
        ),
    )
    errors = config.validate()
    assert any("model is required" in error.lower() for error in errors)


def test_config_validation_missing_api_key():
    """Test validation fails when OpenAI API key is missing."""
    config = Config(
        llm=LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            api_key=None,
        ),
        azure_devops=AzureDevOpsConfig(
            organization_url="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
            pat_token="test-pat",
        ),
    )
    errors = config.validate()
    assert any("api key" in error.lower() for error in errors)


def test_config_validation_azure_openai_requirements():
    """Test Azure OpenAI requires api_base and api_version."""
    config = Config(
        llm=LLMConfig(
            provider=LLMProvider.AZURE_OPENAI,
            model="gpt-4",
        ),
        azure_devops=AzureDevOpsConfig(
            organization_url="https://dev.azure.com/test",
            project="TestProject",
            repository="TestRepo",
            pat_token="test-pat",
        ),
    )
    errors = config.validate()
    assert any("api_base" in error.lower() for error in errors)
    assert any("api_version" in error.lower() for error in errors)


def test_load_config_from_file():
    """Test loading configuration from YAML file."""
    config_data = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
        },
        "azure_devops": {
            "organization_url": "https://dev.azure.com/test",
            "project": "TestProject",
            "repository": "TestRepo",
            "pat_token": "test-pat",
        },
        "log_level": "DEBUG",
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        config = load_config(temp_path)
        assert config.llm.model == "gpt-4"
        assert config.azure_devops.project == "TestProject"
        assert config.log_level == "DEBUG"
    finally:
        os.unlink(temp_path)


def test_load_config_file_not_found():
    """Test that FileNotFoundError is raised when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_load_config_validation_error():
    """Test that ValueError is raised for invalid configuration."""
    config_data = {
        "llm": {
            "provider": "openai",
            "model": "",  # Invalid: empty model
        },
        "azure_devops": {
            "organization_url": "",  # Invalid: empty URL
            "project": "TestProject",
            "repository": "TestRepo",
        },
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Configuration validation failed"):
            load_config(temp_path)
    finally:
        os.unlink(temp_path)


def test_load_config_from_env(monkeypatch):
    """Test loading configuration from environment variables."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("AZDO_ORG_URL", "https://dev.azure.com/test")
    monkeypatch.setenv("AZDO_PROJECT", "TestProject")
    monkeypatch.setenv("AZDO_REPOSITORY", "TestRepo")
    monkeypatch.setenv("AZDO_PERSONAL_ACCESS_TOKEN", "test-pat")
    
    config = load_config_from_env()
    assert config.llm.provider == LLMProvider.OPENAI
    assert config.llm.model == "gpt-4"
    assert config.azure_devops.project == "TestProject"


def test_review_config_defaults():
    """Test ReviewConfig has sensible defaults."""
    config = ReviewConfig()
    assert "code_quality" in config.review_scope
    assert "security" in config.review_scope
    assert ".py" in config.file_extensions
    assert config.comment_style == "constructive"
    assert config.max_files_per_review == 50
