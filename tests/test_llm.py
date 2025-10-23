"""Tests for LLM integration components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from src.config.config import LLMConfig
from src.azure_devops.models import ReviewComment, FileDiff, PullRequest, ChangeType
from src.llm.base import LLMProvider, LLMResponse, LLMProviderFactory
from src.llm.prompts import CodeReviewPrompts, detect_language
from src.llm.parser import ResponseParser
from src.llm.review_client import LLMReviewClient


# Test Prompts
class TestCodeReviewPrompts:
    """Test prompt generation."""

    def test_detect_language(self):
        """Test language detection from file path."""
        assert detect_language("main.py") == "python"
        assert detect_language("src/app.ts") == "typescript"
        assert detect_language("components/App.jsx") == "javascript"
        assert detect_language("README.md") == "markdown"
        assert detect_language("unknown.xyz") == "unknown"

    def test_file_review_prompt(self):
        """Test file review prompt generation."""
        prompt = CodeReviewPrompts.build_file_review_prompt(
            file_path="test.py",
            file_content="def hello():\n    print('Hello')",
            language="python",
            change_type="add",
            pr_title="Add greeting function",
            pr_description="Implements hello world",
            review_scope=["security", "performance"],
        )

        assert "test.py" in prompt
        assert "python" in prompt.lower()
        assert "def hello()" in prompt
        assert "security" in prompt
        assert "performance" in prompt

    def test_quick_review_prompt(self):
        """Test quick review prompt generation."""
        prompt = CodeReviewPrompts.build_quick_review_prompt(
            file_path="test.py", file_content="import os\nos.system('rm -rf /')", language="python"
        )

        assert "test.py" in prompt
        assert "security" in prompt.lower() or "critical" in prompt.lower()

    def test_summary_prompt(self):
        """Test summary prompt generation."""
        stats = {
            "total_files": 3,
            "total_issues": 10,
            "by_severity": {"error": 2, "warning": 8},
            "by_category": {"security": 3, "style": 7},
        }

        prompt = CodeReviewPrompts.build_summary_prompt("Test PR", stats)

        assert "Test PR" in prompt
        assert "3" in prompt
        assert "10" in prompt


# Test Parser
class TestResponseParser:
    """Test response parsing."""

    def setup_method(self):
        """Setup test fixtures."""
        self.parser = ResponseParser()

    def test_extract_json_from_markdown(self):
        """Test JSON extraction from markdown code blocks."""
        response = """
Here are my comments:

```json
[
    {"line_number": 10, "severity": "warning", "category": "style", "content": "Add type hints"}
]
```
"""
        result = self.parser.extract_json(response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["line_number"] == 10

    def test_extract_json_raw(self):
        """Test JSON extraction from raw JSON."""
        response = (
            '[{"line_number": 5, "severity": "error", "category": "bug", "content": "Null check"}]'
        )
        result = self.parser.extract_json(response)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_parse_review_response(self):
        """Test parsing review response into ReviewComment objects."""
        response = """
```json
[
    {
        "line_number": 10,
        "severity": "warning",
        "category": "style",
        "content": "Consider adding type hints"
    },
    {
        "line_number": 15,
        "severity": "error",
        "category": "bug",
        "content": "Missing null check"
    }
]
```
"""
        comments = self.parser.parse_review_response(response, "test.py")

        assert len(comments) == 2
        assert all(isinstance(c, ReviewComment) for c in comments)
        assert comments[0].file_path == "test.py"
        assert comments[0].line == 10
        assert comments[0].severity == "warning"
        assert comments[1].severity == "error"

    def test_validate_comments(self):
        """Test comment validation."""
        comments = [
            ReviewComment(
                file_path="test.py",
                line=10,
                content="Valid comment",
                severity="warning",
                category="style",
            ),
            ReviewComment(
                file_path="test.py",
                line=-1,  # Invalid line number
                content="Invalid line",
                severity="warning",
                category="style",
            ),
            ReviewComment(
                file_path="test.py",
                line=20,
                content="",  # Empty content
                severity="warning",
                category="style",
            ),
        ]

        validated = self.parser.validate_comments(comments)

        # Only the first comment should remain
        assert len(validated) == 1
        assert validated[0].line == 10

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        response = "This is not JSON at all"
        comments = self.parser.parse_review_response(response, "test.py")
        assert comments == []


# Test LLM Provider Factory
class TestLLMProviderFactory:
    """Test LLM provider factory."""

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")

        with patch("src.llm.openai_provider.openai") as mock_openai:
            provider = LLMProviderFactory.create(config)
            assert provider.__class__.__name__ == "OpenAIProvider"

    def test_create_azure_openai_provider(self):
        """Test creating Azure OpenAI provider."""
        config = LLMConfig(
            provider="azure_openai",
            model="gpt-4",
            api_key="test-key",
            api_base="https://test.openai.azure.com",
            api_version="2023-05-15",
        )

        with patch("src.llm.azure_openai.openai") as mock_openai:
            provider = LLMProviderFactory.create(config)
            assert provider.__class__.__name__ == "AzureOpenAIProvider"

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        config = LLMConfig(provider="anthropic", model="claude-3-opus", api_key="test-key")

        with patch("src.llm.anthropic_provider.anthropic") as mock_anthropic:
            provider = LLMProviderFactory.create(config)
            assert provider.__class__.__name__ == "AnthropicProvider"

    def test_create_ollama_provider(self):
        """Test creating Ollama provider."""
        config = LLMConfig(provider="ollama", model="llama2", api_base="http://localhost:11434")

        provider = LLMProviderFactory.create(config)
        assert provider.__class__.__name__ == "OllamaProvider"

    def test_create_unknown_provider(self):
        """Test creating unknown provider raises error."""
        config = LLMConfig(provider="unknown", model="test")

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMProviderFactory.create(config)


# Test Review Client
class TestLLMReviewClient:
    """Test LLM review client."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")

        # Mock provider
        self.mock_provider = Mock(spec=LLMProvider)
        self.mock_provider.generate_completion.return_value = LLMResponse(
            content="""```json
[
    {
        "line_number": 10,
        "severity": "warning",
        "category": "style",
        "content": "Consider adding type hints"
    }
]
```""",
            tokens_used=100,
            model="gpt-4",
        )
        self.mock_provider.count_tokens.return_value = 50
        self.mock_provider.optimize_prompt.side_effect = lambda x: x
        self.mock_provider.test_connection.return_value = True

    def test_init(self):
        """Test client initialization."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)
            assert client.provider == self.mock_provider
            assert client.parser is not None

    def test_test_connection(self):
        """Test connection testing."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)
            assert client.test_connection() is True
            self.mock_provider.test_connection.assert_called_once()

    def test_review_file(self):
        """Test reviewing a single file."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)

            file_diff = FileDiff(
                path="test.py", change_type=ChangeType.EDIT, additions=10, deletions=5
            )

            file_content = "def hello():\n    print('Hello')"

            comments = client.review_file(file_diff=file_diff, file_content=file_content)

            assert len(comments) > 0
            assert all(isinstance(c, ReviewComment) for c in comments)
            self.mock_provider.generate_completion.assert_called_once()

    def test_review_file_quick_mode(self):
        """Test reviewing file in quick mode."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)

            file_diff = FileDiff(
                path="test.py", change_type=ChangeType.EDIT, additions=10, deletions=5
            )

            file_content = "def hello():\n    print('Hello')"

            comments = client.review_file(
                file_diff=file_diff, file_content=file_content, quick_mode=True
            )

            assert isinstance(comments, list)
            # In quick mode, should use quick system message
            call_args = self.mock_provider.generate_completion.call_args
            assert (
                "critical" in call_args.kwargs.get("system_message", "").lower()
                or "security" in call_args.kwargs.get("system_message", "").lower()
            )

    def test_review_pull_request(self):
        """Test reviewing entire pull request."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)

            pr = PullRequest(
                pull_request_id=1,
                title="Test PR",
                description="Test description",
                source_branch="feature",
                target_branch="main",
                author="test-user",
                created_date="2024-01-01T00:00:00Z",
                status="active",
            )

            file_diffs = [
                FileDiff(path="test1.py", change_type=ChangeType.EDIT, additions=10, deletions=5),
                FileDiff(path="test2.py", change_type=ChangeType.ADD, additions=20, deletions=0),
            ]

            file_contents = {
                "test1.py": "def func1():\n    pass",
                "test2.py": "def func2():\n    pass",
            }

            comments = client.review_pull_request(
                pull_request=pr, file_diffs=file_diffs, file_contents=file_contents
            )

            assert isinstance(comments, list)
            # Should call generate_completion for each file
            assert self.mock_provider.generate_completion.call_count == 2

    def test_generate_summary(self):
        """Test generating review summary."""
        self.mock_provider.generate_completion.return_value = LLMResponse(
            content="Overall the code looks good with minor style issues.",
            tokens_used=50,
            model="gpt-4",
        )

        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            client = LLMReviewClient(self.config)

            pr = PullRequest(
                pull_request_id=1,
                title="Test PR",
                description="Test description",
                source_branch="feature",
                target_branch="main",
                author="test-user",
                created_date="2024-01-01T00:00:00Z",
                status="active",
            )

            comments = [
                ReviewComment(
                    file_path="test.py",
                    line=10,
                    content="Add type hints",
                    severity="warning",
                    category="style",
                )
            ]

            summary = client.generate_summary(pr, comments)

            assert isinstance(summary, str)
            assert len(summary) > 0

    def test_context_manager(self):
        """Test client as context manager."""
        with patch.object(LLMProviderFactory, "create", return_value=self.mock_provider):
            with LLMReviewClient(self.config) as client:
                assert client.provider == self.mock_provider

            # Should call close
            self.mock_provider.close.assert_called_once()


# Integration-style tests
class TestLLMIntegration:
    """Integration tests for LLM workflow."""

    def test_end_to_end_review_flow(self):
        """Test complete review flow from config to comments."""
        config = LLMConfig(provider="openai", model="gpt-4", api_key="test-key")

        mock_response = """```json
[
    {
        "line_number": 10,
        "severity": "warning",
        "category": "style",
        "content": "Consider using f-strings"
    },
    {
        "line_number": 15,
        "severity": "error",
        "category": "bug",
        "content": "Missing error handling"
    }
]
```"""

        with patch("src.llm.openai_provider.openai"):
            mock_provider = Mock(spec=LLMProvider)
            mock_provider.generate_completion.return_value = LLMResponse(
                content=mock_response, tokens_used=150, model="gpt-4"
            )
            mock_provider.count_tokens.return_value = 50
            mock_provider.optimize_prompt.side_effect = lambda x: x

            with patch.object(LLMProviderFactory, "create", return_value=mock_provider):
                with LLMReviewClient(config) as client:
                    file_diff = FileDiff(
                        path="app.py", change_type=ChangeType.EDIT, additions=10, deletions=2
                    )

                    content = """
def greet(name):
    message = "Hello, " + name
    print(message)
    return message
"""

                    comments = client.review_file(file_diff, content)

                    assert len(comments) == 2
                    assert comments[0].line == 10
                    assert comments[0].severity == "warning"
                    assert comments[1].line == 15
                    assert comments[1].severity == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
