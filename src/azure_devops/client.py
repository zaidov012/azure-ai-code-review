"""Main Azure DevOps client orchestrating all operations."""

from typing import List, Optional, Dict, Any
import logging

from ..config.config import AzureDevOpsConfig
from ..utils.logger import setup_logger
from .auth import AzureDevOpsAuth
from .pr_client import PullRequestClient
from .comment_client import CommentClient
from .models import PullRequest, FileDiff, CommentThread, ReviewComment

logger = setup_logger(__name__)


class AzureDevOpsClient:
    """
    Main client for Azure DevOps operations.
    
    Provides high-level interface for PR review operations,
    orchestrating authentication, PR fetching, and comment posting.
    """
    
    def __init__(self, config: AzureDevOpsConfig):
        """
        Initialize Azure DevOps client.
        
        Args:
            config: Azure DevOps configuration
        """
        self.config = config
        self.auth = AzureDevOpsAuth(config)
        self.pr_client = PullRequestClient(config, self.auth)
        self.comment_client = CommentClient(config, self.auth)
        
        logger.info(
            f"Initialized Azure DevOps client for {config.organization_url}/"
            f"{config.project}/{config.repository}"
        )
    
    def test_connection(self) -> bool:
        """
        Test connection to Azure DevOps.
        
        Returns:
            True if connection successful, False otherwise
        """
        return self.auth.test_connection()
    
    def get_pull_request(self, pr_id: int) -> Optional[PullRequest]:
        """
        Get pull request details.
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            PullRequest object or None if not found
        """
        return self.pr_client.get_pull_request(pr_id)
    
    def get_pull_request_changes(self, pr_id: int) -> List[FileDiff]:
        """
        Get file changes for a pull request.
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            List of FileDiff objects
        """
        return self.pr_client.get_pull_request_changes(pr_id)
    
    def get_pull_request_context(self, pr_id: int) -> Dict[str, Any]:
        """
        Get complete context for a PR (details + changes + threads).
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            Dictionary with PR details, file changes, and existing threads
        """
        logger.info(f"Fetching complete context for PR #{pr_id}")
        
        pr = self.pr_client.get_pull_request(pr_id)
        if not pr:
            logger.error(f"PR #{pr_id} not found")
            return {}
        
        changes = self.pr_client.get_pull_request_changes(pr_id)
        threads = self.pr_client.get_pull_request_threads(pr_id)
        
        context = {
            "pull_request": pr,
            "file_changes": changes,
            "comment_threads": threads,
            "stats": {
                "total_files": len(changes),
                "additions": sum(f.additions for f in changes),
                "deletions": sum(f.deletions for f in changes),
                "existing_threads": len(threads),
            }
        }
        
        logger.info(
            f"PR context: {context['stats']['total_files']} files, "
            f"+{context['stats']['additions']}/-{context['stats']['deletions']} lines, "
            f"{context['stats']['existing_threads']} existing threads"
        )
        
        return context
    
    def filter_reviewable_files(
        self,
        file_changes: List[FileDiff],
        allowed_extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        max_files: int = 50
    ) -> List[FileDiff]:
        """
        Filter files that should be reviewed based on configuration.
        
        Args:
            file_changes: List of file changes
            allowed_extensions: List of allowed file extensions (None = all)
            exclude_patterns: List of glob patterns to exclude
            max_files: Maximum number of files to review
        
        Returns:
            Filtered list of FileDiff objects
        """
        import fnmatch
        
        reviewable = []
        
        for file_diff in file_changes:
            # Skip binary files
            if file_diff.is_binary:
                logger.debug(f"Skipping binary file: {file_diff.path}")
                continue
            
            # Skip deleted files
            if file_diff.change_type.value == "delete":
                logger.debug(f"Skipping deleted file: {file_diff.path}")
                continue
            
            # Check file extension
            if allowed_extensions:
                if not any(file_diff.path.endswith(ext) for ext in allowed_extensions):
                    logger.debug(f"Skipping file (extension not allowed): {file_diff.path}")
                    continue
            
            # Check exclude patterns
            if exclude_patterns:
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(file_diff.path, pattern):
                        logger.debug(f"Skipping file (matches exclude pattern): {file_diff.path}")
                        excluded = True
                        break
                if excluded:
                    continue
            
            reviewable.append(file_diff)
        
        # Limit number of files
        if len(reviewable) > max_files:
            logger.warning(
                f"Too many files to review ({len(reviewable)}). "
                f"Limiting to {max_files} files."
            )
            reviewable = reviewable[:max_files]
        
        logger.info(f"Filtered to {len(reviewable)} reviewable files")
        return reviewable
    
    def post_review_comments(
        self,
        pr_id: int,
        comments: List[ReviewComment],
        comment_style: str = "constructive"
    ) -> Dict[str, Any]:
        """
        Post review comments to a pull request.
        
        Args:
            pr_id: Pull request ID
            comments: List of review comments
            comment_style: Comment formatting style
        
        Returns:
            Dictionary with posting results
        """
        return self.comment_client.post_review_comments(
            pr_id,
            comments,
            comment_style
        )
    
    def post_summary_comment(
        self,
        pr_id: int,
        summary: str
    ) -> Optional[CommentThread]:
        """
        Post a general summary comment to PR.
        
        Args:
            pr_id: Pull request ID
            summary: Summary content
        
        Returns:
            Created CommentThread or None
        """
        return self.comment_client.create_general_comment(pr_id, summary)
    
    def close(self) -> None:
        """Close the client and release resources."""
        self.auth.close()
        logger.info("Closed Azure DevOps client")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def create_client(config: AzureDevOpsConfig) -> AzureDevOpsClient:
    """
    Helper function to create an Azure DevOps client.
    
    Args:
        config: Azure DevOps configuration
    
    Returns:
        Configured AzureDevOpsClient
    """
    return AzureDevOpsClient(config)
