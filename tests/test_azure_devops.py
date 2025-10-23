"""Unit tests for Azure DevOps integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from src.azure_devops.models import (
    PullRequest,
    FileDiff,
    CommentThread,
    Comment,
    ReviewComment,
    User,
    PullRequestStatus,
    FileDiffOperation,
    CommentThreadStatus,
)
from src.azure_devops.auth import AzureDevOpsAuth
from src.azure_devops.client import AzureDevOpsClient
from src.config.config import AzureDevOpsConfig


@pytest.fixture
def azdo_config():
    """Create test Azure DevOps configuration."""
    return AzureDevOpsConfig(
        organization_url="https://dev.azure.com/testorg",
        project="TestProject",
        repository="TestRepo",
        pat_token="test-pat-token",
        verify_ssl=True,
        timeout=30,
    )


@pytest.fixture
def mock_session():
    """Create mock requests session."""
    session = Mock(spec=requests.Session)
    session.headers = {}
    return session


class TestAzureDevOpsAuth:
    """Tests for authentication module."""
    
    def test_auth_initialization(self, azdo_config):
        """Test auth object creation."""
        auth = AzureDevOpsAuth(azdo_config)
        assert auth.config == azdo_config
        assert auth._session is None
    
    def test_create_auth_header(self, azdo_config):
        """Test PAT token auth header creation."""
        auth = AzureDevOpsAuth(azdo_config)
        header = auth._create_auth_header()
        
        assert "Authorization" in header
        assert header["Authorization"].startswith("Basic ")
    
    def test_auth_header_missing_token(self):
        """Test error when PAT token is missing."""
        config = AzureDevOpsConfig(
            organization_url="https://dev.azure.com/test",
            project="Test",
            repository="Repo",
            pat_token=None,
        )
        
        auth = AzureDevOpsAuth(config)
        
        with pytest.raises(ValueError, match="PAT token is required"):
            auth._create_auth_header()
    
    def test_session_creation(self, azdo_config):
        """Test session is created with correct configuration."""
        auth = AzureDevOpsAuth(azdo_config)
        session = auth.get_session()
        
        assert session is not None
        assert "Authorization" in session.headers
        assert session.verify == azdo_config.verify_ssl
    
    def test_session_reuse(self, azdo_config):
        """Test session is reused on subsequent calls."""
        auth = AzureDevOpsAuth(azdo_config)
        session1 = auth.get_session()
        session2 = auth.get_session()
        
        assert session1 is session2
    
    def test_context_manager(self, azdo_config):
        """Test auth can be used as context manager."""
        with AzureDevOpsAuth(azdo_config) as auth:
            assert auth is not None
        
        # Session should be closed after context exit
        assert auth._session is None


class TestModels:
    """Tests for data models."""
    
    def test_user_from_api(self):
        """Test User model creation from API data."""
        api_data = {
            "id": "user-123",
            "displayName": "John Doe",
            "uniqueName": "john.doe@example.com",
            "emailAddress": "john.doe@example.com",
        }
        
        user = User.from_api(api_data)
        
        assert user.id == "user-123"
        assert user.display_name == "John Doe"
        assert user.email == "john.doe@example.com"
    
    def test_file_diff_from_api(self):
        """Test FileDiff model creation from API data."""
        api_data = {
            "changeType": "edit",
            "item": {
                "path": "/src/main.py"
            }
        }
        
        file_diff = FileDiff.from_api(api_data)
        
        assert file_diff.path == "/src/main.py"
        assert file_diff.change_type == FileDiffOperation.EDIT
    
    def test_file_diff_is_binary(self):
        """Test binary file detection."""
        binary_file = FileDiff(
            path="/images/logo.png",
            change_type=FileDiffOperation.ADD
        )
        
        text_file = FileDiff(
            path="/src/main.py",
            change_type=FileDiffOperation.EDIT
        )
        
        assert binary_file.is_binary is True
        assert text_file.is_binary is False
    
    def test_pull_request_from_api(self):
        """Test PullRequest model creation from API data."""
        api_data = {
            "pullRequestId": 123,
            "title": "Test PR",
            "description": "Test description",
            "sourceRefName": "refs/heads/feature",
            "targetRefName": "refs/heads/main",
            "status": "active",
            "createdBy": {
                "id": "user-123",
                "displayName": "John Doe",
                "uniqueName": "john.doe@example.com"
            },
            "repository": {
                "id": "repo-123",
                "name": "TestRepo",
                "url": "https://dev.azure.com/test/repo",
                "project": {
                    "id": "proj-123"
                }
            },
            "reviewers": [],
            "labels": []
        }
        
        pr = PullRequest.from_api(api_data)
        
        assert pr.pull_request_id == 123
        assert pr.title == "Test PR"
        assert pr.status == PullRequestStatus.ACTIVE
        assert pr.is_active is True
    
    def test_review_comment_formatting(self):
        """Test ReviewComment formatting with different styles."""
        comment = ReviewComment(
            file_path="/src/main.py",
            line_number=42,
            content="This could be improved.",
            severity="major",
            category="code_quality"
        )
        
        # Test constructive style
        constructive = comment.format_content("constructive")
        assert "Code Quality" in constructive
        assert "major" in constructive.lower()
        
        # Test concise style
        concise = comment.format_content("concise")
        assert "Code Quality" in concise
        assert len(concise) < len(constructive)
        
        # Test detailed style
        detailed = comment.format_content("detailed")
        assert "AI-generated" in detailed
    
    def test_review_comment_thread_context(self):
        """Test thread context generation for review comment."""
        comment = ReviewComment(
            file_path="/src/main.py",
            line_number=42,
            content="Test comment",
        )
        
        context = comment.to_thread_context()
        
        assert context["filePath"] == "/src/main.py"
        assert context["rightFileStart"]["line"] == 42
        assert context["rightFileEnd"]["line"] == 42


class TestAzureDevOpsClient:
    """Tests for main Azure DevOps client."""
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_client_initialization(self, mock_get_session, azdo_config):
        """Test client initialization."""
        client = AzureDevOpsClient(azdo_config)
        
        assert client.config == azdo_config
        assert client.auth is not None
        assert client.pr_client is not None
        assert client.comment_client is not None
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    @patch('src.azure_devops.pr_client.PullRequestClient.get_pull_request')
    def test_get_pull_request(self, mock_get_pr, mock_get_session, azdo_config):
        """Test getting pull request."""
        # Mock PR data
        mock_pr = Mock(spec=PullRequest)
        mock_pr.pull_request_id = 123
        mock_pr.title = "Test PR"
        mock_get_pr.return_value = mock_pr
        
        client = AzureDevOpsClient(azdo_config)
        pr = client.get_pull_request(123)
        
        assert pr is not None
        assert pr.pull_request_id == 123
        mock_get_pr.assert_called_once_with(123)
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_filter_reviewable_files(self, mock_get_session, azdo_config):
        """Test filtering reviewable files."""
        file_changes = [
            FileDiff(path="/src/main.py", change_type=FileDiffOperation.EDIT),
            FileDiff(path="/src/test.js", change_type=FileDiffOperation.ADD),
            FileDiff(path="/dist/bundle.min.js", change_type=FileDiffOperation.EDIT),
            FileDiff(path="/images/logo.png", change_type=FileDiffOperation.ADD),
            FileDiff(path="/deleted.py", change_type=FileDiffOperation.DELETE),
        ]
        
        client = AzureDevOpsClient(azdo_config)
        
        # Filter with allowed extensions
        reviewable = client.filter_reviewable_files(
            file_changes,
            allowed_extensions=[".py", ".js"],
            exclude_patterns=["*/dist/*"],
            max_files=50
        )
        
        # Should include main.py and test.js
        # Should exclude: bundle.min.js (pattern), logo.png (binary), deleted.py (deleted)
        assert len(reviewable) == 2
        paths = [f.path for f in reviewable]
        assert "/src/main.py" in paths
        assert "/src/test.js" in paths
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_filter_reviewable_files_max_limit(self, mock_get_session, azdo_config):
        """Test max files limit in filtering."""
        # Create 100 Python files
        file_changes = [
            FileDiff(path=f"/src/file{i}.py", change_type=FileDiffOperation.EDIT)
            for i in range(100)
        ]
        
        client = AzureDevOpsClient(azdo_config)
        
        # Filter with max 10 files
        reviewable = client.filter_reviewable_files(
            file_changes,
            max_files=10
        )
        
        assert len(reviewable) == 10
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_context_manager(self, mock_get_session, azdo_config):
        """Test client can be used as context manager."""
        with AzureDevOpsClient(azdo_config) as client:
            assert client is not None
        
        # Should call close
        # (We can't easily test this without more mocking)


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_http_404_error(self, mock_get_session, azdo_config):
        """Test handling of 404 errors."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session
        
        from src.azure_devops.pr_client import PullRequestClient
        from src.azure_devops.auth import AzureDevOpsAuth
        
        auth = AzureDevOpsAuth(azdo_config)
        pr_client = PullRequestClient(azdo_config, auth)
        
        # Should return None for 404
        pr = pr_client.get_pull_request(999)
        assert pr is None
    
    @patch('src.azure_devops.auth.AzureDevOpsAuth.get_session')
    def test_network_error(self, mock_get_session, azdo_config):
        """Test handling of network errors."""
        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError()
        mock_get_session.return_value = mock_session
        
        from src.azure_devops.pr_client import PullRequestClient
        from src.azure_devops.auth import AzureDevOpsAuth
        
        auth = AzureDevOpsAuth(azdo_config)
        pr_client = PullRequestClient(azdo_config, auth)
        
        # Should raise the exception
        with pytest.raises(requests.exceptions.ConnectionError):
            pr_client.get_pull_request(123)
