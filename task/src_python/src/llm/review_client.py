"""Main LLM client for code review operations."""

from typing import List, Dict, Any, Optional

from ..config.config import LLMConfig
from ..azure_devops.models import ReviewComment, FileDiff, PullRequest
from ..utils.logger import setup_logger
from .base import LLMProviderFactory
from .prompts import CodeReviewPrompts, detect_language
from .parser import ResponseParser

logger = setup_logger(__name__, log_level="DEBUG")


class LLMReviewClient:
    """
    Main client for LLM-powered code reviews.

    Coordinates between LLM providers, prompts, and response parsing
    to generate review comments for pull requests.
    """

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM review client.

        Args:
            config: LLM configuration
        """
        self.config = config
        self.provider = LLMProviderFactory.create(config)
        self.parser = ResponseParser()

        logger.info(f"Initialized LLM review client with {self.provider.__class__.__name__}")

    def test_connection(self) -> bool:
        """
        Test connection to LLM provider.

        Returns:
            True if connection successful
        """
        return self.provider.test_connection()

    def review_file(
        self,
        file_diff: FileDiff,
        file_content: str,
        pr_context: Optional[Dict[str, Any]] = None,
        review_scope: Optional[List[str]] = None,
        quick_mode: bool = False,
    ) -> List[ReviewComment]:
        """
        Review a single file and generate comments.

        Args:
            file_diff: File diff information
            file_content: Content of the file
            pr_context: Pull request context (optional)
            review_scope: Aspects to focus on (optional)
            quick_mode: If True, only check critical issues

        Returns:
            List of ReviewComment objects
        """
        pr_title = pr_context.get("title", "") if pr_context else ""
        pr_description = pr_context.get("description", "") if pr_context else ""

        # Detect language
        language = detect_language(file_diff.path)

        # Build prompt
        if quick_mode:
            prompt = CodeReviewPrompts.build_quick_review_prompt(
                file_diff.path, file_content, language
            )
            system_message = CodeReviewPrompts.get_system_message("quick")
        else:
            prompt = CodeReviewPrompts.build_file_review_prompt(
                file_path=file_diff.path,
                file_content=file_content,
                language=language,
                change_type=file_diff.change_type.value,
                pr_title=pr_title,
                pr_description=pr_description,
                review_scope=review_scope,
            )
            system_message = CodeReviewPrompts.get_system_message("default")

        # Optimize prompt to fit token limits
        prompt = self.provider.optimize_prompt(prompt)

        logger.info(f"Reviewing file: {file_diff.path} ({language})")
        logger.debug(
            f"Prompt length: {len(prompt)} chars, {self.provider.count_tokens(prompt)} tokens"
        )

        try:
            # Generate review
            response = self.provider.generate_completion(
                prompt=prompt, system_message=system_message
            )

            logger.info(f"Received response ({response.tokens_used} tokens)")

            # Parse response into comments
            comments = self.parser.parse_review_response(response.content, file_diff.path)

            # Validate comments
            comments = self.parser.validate_comments(comments)

            logger.info(f"Generated {len(comments)} review comments for {file_diff.path}")

            return comments

        except Exception as e:
            logger.error(f"Error reviewing file {file_diff.path}: {e}")
            return []

    def review_pull_request(
        self,
        pull_request: PullRequest,
        file_diffs: List[FileDiff],
        file_contents: Dict[str, str],
        review_scope: Optional[List[str]] = None,
        quick_mode: bool = False,
    ) -> List[ReviewComment]:
        """
        Review an entire pull request.

        Args:
            pull_request: Pull request object
            file_diffs: List of file changes
            file_contents: Dictionary mapping file paths to contents
            review_scope: Review aspects to focus on
            quick_mode: If True, only check critical issues

        Returns:
            List of all review comments
        """
        all_comments = []

        pr_context = {"title": pull_request.title, "description": pull_request.description}

        logger.info(
            f"Reviewing PR #{pull_request.pull_request_id}: {pull_request.title} "
            f"({len(file_diffs)} files)"
        )

        for i, file_diff in enumerate(file_diffs, 1):
            logger.info(f"Processing file {i}/{len(file_diffs)}: {file_diff.path}")

            # Get file content
            file_content = file_contents.get(file_diff.path, "")

            if not file_content:
                logger.warning(f"No content available for {file_diff.path}, skipping")
                continue

            # Review file
            comments = self.review_file(
                file_diff=file_diff,
                file_content=file_content,
                pr_context=pr_context,
                review_scope=review_scope,
                quick_mode=quick_mode,
            )

            all_comments.extend(comments)

        logger.info(
            f"PR review complete. Generated {len(all_comments)} total comments "
            f"across {len(file_diffs)} files"
        )

        return all_comments

    def generate_summary(
        self, pull_request: PullRequest, review_comments: List[ReviewComment]
    ) -> str:
        """
        Generate a summary of the review.

        Args:
            pull_request: Pull request object
            review_comments: List of all review comments

        Returns:
            Summary text
        """
        # Calculate statistics
        stats = self._calculate_stats(review_comments)

        # Build prompt
        prompt = CodeReviewPrompts.build_summary_prompt(pull_request.title, stats)

        system_message = CodeReviewPrompts.get_system_message("default")

        logger.info("Generating review summary")

        try:
            response = self.provider.generate_completion(
                prompt=prompt, system_message=system_message
            )

            summary = self.parser.parse_summary_response(response.content)

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Failed to generate review summary."

    def _calculate_stats(self, comments: List[ReviewComment]) -> Dict[str, Any]:
        """
        Calculate statistics from review comments.

        Args:
            comments: List of review comments

        Returns:
            Statistics dictionary
        """
        by_severity: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        files = set()

        for comment in comments:
            # Count by severity
            severity = comment.severity
            by_severity[severity] = by_severity.get(severity, 0) + 1

            # Count by category
            category = comment.category
            by_category[category] = by_category.get(category, 0) + 1

            # Track files
            files.add(comment.file_path)

        return {
            "total_files": len(files),
            "total_issues": len(comments),
            "by_severity": by_severity,
            "by_category": by_category,
        }

    def close(self) -> None:
        """Close LLM provider connection."""
        if self.provider:
            self.provider.close()

    def __enter__(self) -> "LLMReviewClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def create_review_client(config: LLMConfig) -> LLMReviewClient:
    """
    Helper function to create an LLM review client.

    Args:
        config: LLM configuration

    Returns:
        Configured LLMReviewClient
    """
    return LLMReviewClient(config)
