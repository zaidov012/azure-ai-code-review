"""Comment operations for Azure DevOps pull requests."""

import requests
from typing import List, Optional, Dict, Any

from ..config.config import AzureDevOpsConfig
from ..utils.logger import setup_logger
from .models import CommentThread, ReviewComment, CommentThreadStatus
from .auth import AzureDevOpsAuth

logger = setup_logger(__name__)


class CommentClient:
    """Client for posting and managing comments on pull requests."""

    def __init__(self, config: AzureDevOpsConfig, auth: AzureDevOpsAuth):
        """
        Initialize comment client.

        Args:
            config: Azure DevOps configuration
            auth: Authentication handler
        """
        self.config = config
        self.auth = auth
        self.base_url = (
            f"{config.organization_url}/{config.project}/"
            f"_apis/git/repositories/{config.repository}"
        )
        self.api_version = "7.0"

    def create_comment_thread(
        self, pr_id: int, review_comment: ReviewComment, comment_style: str = "constructive"
    ) -> Optional[CommentThread]:
        """
        Create a new comment thread on a pull request.

        Args:
            pr_id: Pull request ID
            review_comment: Review comment to post
            comment_style: Style of comment formatting

        Returns:
            Created CommentThread or None on failure

        Raises:
            requests.RequestException: On API errors
        """
        url = f"{self.base_url}/pullrequests/{pr_id}/threads?" f"api-version={self.api_version}"

        # Format the comment content
        formatted_content = review_comment.format_content(comment_style)

        # Build the request payload
        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": formatted_content,
                    "commentType": 1,  # 1 = text comment
                }
            ],
            "status": 1,  # 1 = active
            "threadContext": review_comment.to_thread_context(),
            "properties": {
                "ai_generated": {"$type": "System.String", "$value": "true"},
                "severity": {"$type": "System.String", "$value": review_comment.severity},
                "category": {"$type": "System.String", "$value": review_comment.category},
            },
        }

        logger.info(
            f"Creating comment thread on PR #{pr_id} at {review_comment.file_path}:"
            f"{review_comment.line_number}"
        )
        logger.debug(
            f"Comment severity: {review_comment.severity}, category: {review_comment.category}"
        )

        try:
            session = self.auth.get_session()
            response = session.post(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()

            data = response.json()
            thread = CommentThread.from_api(data)

            logger.info(f"Successfully created comment thread #{thread.id}")
            return thread

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating comment thread: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def add_comment_to_thread(
        self, pr_id: int, thread_id: int, content: str, parent_comment_id: int = 0
    ) -> bool:
        """
        Add a comment to an existing thread.

        Args:
            pr_id: Pull request ID
            thread_id: Thread ID
            content: Comment content
            parent_comment_id: Parent comment ID for replies (0 for top-level)

        Returns:
            True if successful, False otherwise

        Raises:
            requests.RequestException: On API errors
        """
        url = (
            f"{self.base_url}/pullrequests/{pr_id}/threads/{thread_id}/comments?"
            f"api-version={self.api_version}"
        )

        payload = {
            "content": content,
            "parentCommentId": parent_comment_id,
            "commentType": 1,  # text comment
        }

        logger.info(f"Adding comment to thread #{thread_id} on PR #{pr_id}")

        try:
            session = self.auth.get_session()
            response = session.post(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()

            logger.info(f"Successfully added comment to thread #{thread_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding comment to thread: {e}")
            raise

    def update_thread_status(self, pr_id: int, thread_id: int, status: CommentThreadStatus) -> bool:
        """
        Update the status of a comment thread.

        Args:
            pr_id: Pull request ID
            thread_id: Thread ID
            status: New status

        Returns:
            True if successful, False otherwise

        Raises:
            requests.RequestException: On API errors
        """
        url = (
            f"{self.base_url}/pullrequests/{pr_id}/threads/{thread_id}?"
            f"api-version={self.api_version}"
        )

        # Map enum to API status code
        status_map = {
            CommentThreadStatus.ACTIVE: 1,
            CommentThreadStatus.FIXED: 2,
            CommentThreadStatus.WONT_FIX: 3,
            CommentThreadStatus.CLOSED: 4,
            CommentThreadStatus.BY_DESIGN: 5,
            CommentThreadStatus.PENDING: 6,
        }

        status_code = status_map.get(status, 1)

        payload = {"status": status_code}

        logger.info(f"Updating thread #{thread_id} status to {status.value}")

        try:
            session = self.auth.get_session()
            response = session.patch(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()

            logger.info(f"Successfully updated thread #{thread_id} status")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating thread status: {e}")
            raise

    def post_review_comments(
        self,
        pr_id: int,
        comments: List[ReviewComment],
        comment_style: str = "constructive",
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Post multiple review comments to a pull request.

        Args:
            pr_id: Pull request ID
            comments: List of review comments to post
            comment_style: Style of comment formatting
            batch_size: Number of comments to post in parallel (not implemented yet)

        Returns:
            Dictionary with success count, failure count, and errors
        """
        results: Dict[str, Any] = {"total": len(comments), "success": 0, "failed": 0, "errors": []}

        logger.info(f"Posting {len(comments)} review comments to PR #{pr_id}")

        for i, comment in enumerate(comments, 1):
            try:
                logger.debug(f"Posting comment {i}/{len(comments)}")
                self.create_comment_thread(pr_id, comment, comment_style)
                results["success"] += 1

            except Exception as e:
                results["failed"] += 1
                error_msg = (
                    f"Failed to post comment at {comment.file_path}:{comment.line_number}: {str(e)}"
                )
                results["errors"].append(error_msg)  # type: ignore[union-attr]
                logger.error(error_msg)

        logger.info(
            f"Posted {results['success']}/{results['total']} comments successfully. "
            f"{results['failed']} failed."
        )

        return results

    def create_general_comment(self, pr_id: int, content: str) -> Optional[CommentThread]:
        """
        Create a general comment (not attached to a specific line).

        Args:
            pr_id: Pull request ID
            content: Comment content

        Returns:
            Created CommentThread or None on failure

        Raises:
            requests.RequestException: On API errors
        """
        url = f"{self.base_url}/pullrequests/{pr_id}/threads?" f"api-version={self.api_version}"

        payload = {
            "comments": [{"parentCommentId": 0, "content": content, "commentType": 1}],
            "status": 1,  # active
            "properties": {"ai_generated": {"$type": "System.String", "$value": "true"}},
        }

        logger.info(f"Creating general comment on PR #{pr_id}")
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request payload: {payload}")

        try:
            session = self.auth.get_session()
            response = session.post(url, json=payload, timeout=self.config.timeout)
            response.raise_for_status()

            data = response.json()
            thread = CommentThread.from_api(data)

            logger.info(f"Successfully created general comment thread #{thread.id}")
            return thread

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating general comment: {e}")
            raise

    def delete_comment_thread(self, pr_id: int, thread_id: int) -> bool:
        """
        Delete a comment thread.

        Args:
            pr_id: Pull request ID
            thread_id: Thread ID to delete

        Returns:
            True if successful, False otherwise

        Raises:
            requests.RequestException: On API errors
        """
        url = (
            f"{self.base_url}/pullrequests/{pr_id}/threads/{thread_id}?"
            f"api-version={self.api_version}"
        )

        logger.info(f"Deleting comment thread #{thread_id} from PR #{pr_id}")

        try:
            session = self.auth.get_session()
            response = session.delete(url, timeout=self.config.timeout)
            response.raise_for_status()

            logger.info(f"Successfully deleted thread #{thread_id}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting thread: {e}")
            raise
