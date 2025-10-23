"""Pytest configuration and shared fixtures for all tests."""

import pytest
import os
from typing import Dict, List
from unittest.mock import Mock
from datetime import datetime

from src.config.config import Config, LLMConfig, AzureDevOpsConfig, ReviewConfig, LLMProvider
from src.azure_devops.models import (
    PullRequest,
    FileDiff,
    ReviewComment,
    User,
    PullRequestStatus,
    FileDiffOperation,
)


# ===========================
# Configuration Fixtures
# ===========================


@pytest.fixture
def sample_llm_config():
    """Sample LLM configuration for testing."""
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        api_key="test-api-key",
        temperature=0.3,
        max_tokens=2000,
    )


@pytest.fixture
def sample_azdo_config():
    """Sample Azure DevOps configuration for testing."""
    return AzureDevOpsConfig(
        organization_url="https://dev.azure.com/testorg",
        project="TestProject",
        repository="TestRepo",
        pat_token="test-pat-token",
        verify_ssl=True,
        timeout=30,
    )


@pytest.fixture
def sample_review_config():
    """Sample review configuration for testing."""
    return ReviewConfig(
        review_scope=[
            "code_quality",
            "security",
            "performance",
            "best_practices",
        ],
        file_extensions=[".py", ".js", ".ts", ".java"],
        exclude_patterns=["*/dist/*", "*/build/*", "*.min.js"],
        comment_style="constructive",
        max_files_per_review=50,
        max_diff_size_kb=100,
    )


@pytest.fixture
def sample_config(sample_llm_config, sample_azdo_config, sample_review_config):
    """Complete sample configuration for testing."""
    return Config(
        llm=sample_llm_config,
        azure_devops=sample_azdo_config,
        review=sample_review_config,
        log_level="DEBUG",
    )


# ===========================
# Model Fixtures
# ===========================


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id="user-123",
        display_name="John Doe",
        unique_name="john.doe@example.com",
        email="john.doe@example.com",
    )


@pytest.fixture
def sample_pull_request(sample_user):
    """Sample pull request for testing."""
    from src.azure_devops.models import GitRepository

    repo = GitRepository(
        id="repo-123",
        name="TestRepo",
        url="https://dev.azure.com/test/repo",
        project_id="proj-123",
    )

    return PullRequest(
        pull_request_id=123,
        title="Add new feature",
        description="This PR adds a new feature to improve user experience.",
        source_branch="refs/heads/feature/new-feature",
        target_branch="refs/heads/main",
        status=PullRequestStatus.ACTIVE,
        created_by=sample_user,
        repository=repo,
        creation_date=datetime.now(),
    )


@pytest.fixture
def sample_file_diffs():
    """Sample file diffs for testing."""
    return [
        FileDiff(
            path="/src/main.py",
            change_type=FileDiffOperation.EDIT,
            additions=10,
            deletions=5,
        ),
        FileDiff(
            path="/src/utils.py",
            change_type=FileDiffOperation.ADD,
            additions=50,
            deletions=0,
        ),
        FileDiff(
            path="/tests/test_main.py",
            change_type=FileDiffOperation.EDIT,
            additions=20,
            deletions=10,
        ),
    ]


@pytest.fixture
def sample_file_contents():
    """Sample file contents for testing."""
    return {
        "/src/main.py": """
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item['price']
    return total

def process_data(data):
    # TODO: Add validation
    result = calculate_total(data)
    return result
""",
        "/src/utils.py": """
import os
import sys

def read_file(path):
    with open(path) as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)
""",
        "/tests/test_main.py": """
import pytest
from src.main import calculate_total, process_data

def test_calculate_total():
    items = [{'price': 10}, {'price': 20}]
    assert calculate_total(items) == 30

def test_process_data():
    data = [{'price': 5}]
    assert process_data(data) == 5
""",
    }


@pytest.fixture
def sample_review_comments():
    """Sample review comments for testing."""
    return [
        ReviewComment(
            file_path="/src/main.py",
            line_number=5,
            content="Consider using sum() with a generator for better performance.",
            severity="minor",
            category="performance",
        ),
        ReviewComment(
            file_path="/src/main.py",
            line_number=9,
            content="Add input validation to check if data is not None or empty.",
            severity="major",
            category="bug",
        ),
        ReviewComment(
            file_path="/src/utils.py",
            line_number=6,
            content="Missing error handling for file not found scenarios.",
            severity="major",
            category="security",
        ),
    ]


# ===========================
# Mock API Response Fixtures
# ===========================


@pytest.fixture
def mock_azdo_pr_response():
    """Mock Azure DevOps API response for a pull request."""
    return {
        "pullRequestId": 123,
        "title": "Add new feature",
        "description": "This PR adds a new feature",
        "sourceRefName": "refs/heads/feature/new-feature",
        "targetRefName": "refs/heads/main",
        "status": "active",
        "createdBy": {
            "id": "user-123",
            "displayName": "John Doe",
            "uniqueName": "john.doe@example.com",
            "emailAddress": "john.doe@example.com",
        },
        "creationDate": "2024-01-01T00:00:00Z",
        "repository": {
            "id": "repo-123",
            "name": "TestRepo",
            "url": "https://dev.azure.com/test/repo",
            "project": {
                "id": "proj-123",
                "name": "TestProject",
            },
        },
        "reviewers": [],
        "labels": [],
    }


@pytest.fixture
def mock_azdo_changes_response():
    """Mock Azure DevOps API response for PR changes."""
    return {
        "changeEntries": [
            {
                "changeType": "edit",
                "item": {
                    "path": "/src/main.py",
                },
            },
            {
                "changeType": "add",
                "item": {
                    "path": "/src/utils.py",
                },
            },
        ]
    }


@pytest.fixture
def mock_llm_review_response():
    """Mock LLM API response for code review."""
    return """```json
[
    {
        "line_number": 5,
        "severity": "minor",
        "category": "performance",
        "content": "Consider using sum() with a generator for better performance."
    },
    {
        "line_number": 9,
        "severity": "major",
        "category": "bug",
        "content": "Add input validation to check if data is not None or empty."
    }
]
```"""


# ===========================
# Mock Client Fixtures
# ===========================


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    from src.llm.base import LLMProvider as BaseLLMProvider, LLMResponse

    provider = Mock(spec=BaseLLMProvider)
    provider.generate_completion.return_value = LLMResponse(
        content="""```json
[
    {
        "line_number": 5,
        "severity": "minor",
        "category": "performance",
        "content": "Test comment"
    }
]
```""",
        tokens_used=100,
        model="gpt-4",
        finish_reason="stop",
    )
    provider.count_tokens.return_value = 50
    provider.test_connection.return_value = True
    provider.optimize_prompt.side_effect = lambda x: x

    return provider


@pytest.fixture
def mock_requests_session():
    """Mock requests session for Azure DevOps API calls."""
    session = Mock()
    session.headers = {}
    return session


# ===========================
# Environment Setup
# ===========================


@pytest.fixture(autouse=True)
def clean_env_vars(monkeypatch):
    """Clean environment variables before each test."""
    env_vars = [
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_API_KEY",
        "AZDO_ORG_URL",
        "AZDO_PROJECT",
        "AZDO_REPOSITORY",
        "AZDO_PERSONAL_ACCESS_TOKEN",
    ]

    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def temp_config_file(tmp_path, sample_config):
    """Create a temporary config file for testing."""
    import yaml

    config_file = tmp_path / "test_config.yaml"
    config_dict = {
        "llm": {
            "provider": sample_config.llm.provider.value,
            "model": sample_config.llm.model,
            "api_key": sample_config.llm.api_key,
            "temperature": sample_config.llm.temperature,
            "max_tokens": sample_config.llm.max_tokens,
        },
        "azure_devops": {
            "organization_url": sample_config.azure_devops.organization_url,
            "project": sample_config.azure_devops.project,
            "repository": sample_config.azure_devops.repository,
            "pat_token": sample_config.azure_devops.pat_token,
        },
        "review": {
            "review_scope": sample_config.review.review_scope,
            "file_extensions": sample_config.review.file_extensions,
            "exclude_patterns": sample_config.review.exclude_patterns,
        },
        "log_level": sample_config.log_level,
    }

    with open(config_file, "w") as f:
        yaml.dump(config_dict, f)

    return str(config_file)


# ===========================
# Test Markers
# ===========================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_api_key: mark test as requiring real API key")
