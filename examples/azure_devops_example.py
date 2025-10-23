"""
Example script demonstrating Azure DevOps integration.

This script shows how to use the Azure DevOps client to:
1. Fetch PR details
2. Get file changes
3. Post review comments
"""

from src.config import load_config
from src.azure_devops import AzureDevOpsClient, ReviewComment
from src.utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Main example function."""
    # Load configuration
    try:
        config = load_config("config.yaml")
    except FileNotFoundError:
        logger.error("config.yaml not found. Copy config.example.yaml and fill in your settings.")
        return
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Create Azure DevOps client
    with AzureDevOpsClient(config.azure_devops) as client:
        # Test connection
        logger.info("Testing Azure DevOps connection...")
        if not client.test_connection():
            logger.error("Failed to connect to Azure DevOps")
            return
        
        logger.info("✅ Successfully connected to Azure DevOps!")
        
        # Example: Get PR details
        pr_id = 1  # Replace with actual PR ID
        
        logger.info(f"\nFetching PR #{pr_id}...")
        pr = client.get_pull_request(pr_id)
        
        if not pr:
            logger.error(f"PR #{pr_id} not found")
            return
        
        logger.info(f"✅ PR Title: {pr.title}")
        logger.info(f"   Status: {pr.status.value}")
        logger.info(f"   Created by: {pr.created_by.display_name}")
        logger.info(f"   Source: {pr.source_branch}")
        logger.info(f"   Target: {pr.target_branch}")
        
        # Get file changes
        logger.info(f"\nFetching file changes for PR #{pr_id}...")
        changes = client.get_pull_request_changes(pr_id)
        
        logger.info(f"✅ Found {len(changes)} file changes:")
        for change in changes[:5]:  # Show first 5
            logger.info(f"   {change.change_type.value:8s} {change.path}")
        
        if len(changes) > 5:
            logger.info(f"   ... and {len(changes) - 5} more")
        
        # Filter reviewable files
        logger.info("\nFiltering reviewable files...")
        reviewable = client.filter_reviewable_files(
            changes,
            allowed_extensions=config.review.file_extensions,
            exclude_patterns=config.review.exclude_patterns,
            max_files=config.review.max_files_per_review
        )
        
        logger.info(f"✅ {len(reviewable)} files are reviewable")
        
        # Example: Create review comments (not posted, just demonstrated)
        logger.info("\nExample review comments (not posted):")
        
        example_comments = [
            ReviewComment(
                file_path="/src/main.py",
                line_number=10,
                content="Consider adding error handling here.",
                severity="major",
                category="code_quality"
            ),
            ReviewComment(
                file_path="/src/utils.py",
                line_number=25,
                content="This function could benefit from type hints.",
                severity="minor",
                category="best_practices"
            ),
        ]
        
        for comment in example_comments:
            formatted = comment.format_content(config.review.comment_style)
            logger.info(f"\n{comment.file_path}:{comment.line_number}")
            logger.info(f"{formatted}\n")
        
        # To actually post comments (uncomment to use):
        # logger.info(f"\nPosting {len(example_comments)} review comments...")
        # results = client.post_review_comments(
        #     pr_id,
        #     example_comments,
        #     config.review.comment_style
        # )
        # logger.info(f"✅ Posted {results['success']}/{results['total']} comments")
        
        logger.info("\n✅ Example completed successfully!")


if __name__ == "__main__":
    main()
