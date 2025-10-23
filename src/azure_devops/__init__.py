"""Azure DevOps API integration module."""

from .client import AzureDevOpsClient, create_client
from .models import (
    PullRequest,
    FileDiff,
    CommentThread,
    Comment,
    ReviewComment,
    User,
    GitRepository,
    PullRequestStatus,
    CommentThreadStatus,
    FileDiffOperation,
)
from .auth import AzureDevOpsAuth

__all__ = [
    "AzureDevOpsClient",
    "create_client",
    "PullRequest",
    "FileDiff",
    "CommentThread",
    "Comment",
    "ReviewComment",
    "User",
    "GitRepository",
    "PullRequestStatus",
    "CommentThreadStatus",
    "FileDiffOperation",
    "AzureDevOpsAuth",
]
