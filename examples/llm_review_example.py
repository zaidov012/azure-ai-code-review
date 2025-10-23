"""
Example: End-to-end AI-powered PR review workflow.

This example demonstrates how to:
1. Load configuration from YAML and environment
2. Connect to Azure DevOps
3. Fetch a pull request
4. Review files with LLM
5. Post review comments back to Azure DevOps
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config
from src.azure_devops.client import AzureDevOpsClient
from src.llm.review_client import LLMReviewClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Run end-to-end PR review example."""
    
    print("=" * 80)
    print("Azure DevOps AI PR Review - Example")
    print("=" * 80)
    print()
    
    # Step 1: Load configuration
    print("Step 1: Loading configuration...")
    try:
        config = load_config("config/config.yaml")
        print(f"✓ Configuration loaded")
        print(f"  - LLM Provider: {config.llm.provider.value}")
        print(f"  - Model: {config.llm.model}")
        print(f"  - Azure DevOps: {config.azure_devops.organization_url}")
        print()
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return
    
    # Step 2: Initialize clients
    print("Step 2: Initializing clients...")
    try:
        # Initialize Azure DevOps client
        ado_client = AzureDevOpsClient(config.azure_devops)
        print(f"✓ Azure DevOps client initialized")
        
        # Initialize LLM client
        llm_client = LLMReviewClient(config.llm)
        print(f"✓ LLM client initialized")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize clients: {e}")
        return
    
    # Step 3: Test connections
    print("Step 3: Testing connections...")
    try:
        # Test Azure DevOps
        if ado_client.test_connection():
            print(f"✓ Azure DevOps connection successful")
        else:
            print(f"✗ Azure DevOps connection failed")
            return
        
        # Test LLM
        if llm_client.test_connection():
            print(f"✓ LLM connection successful")
        else:
            print(f"✗ LLM connection failed")
            return
        print()
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return
    
    # Step 4: Get pull request
    print("Step 4: Fetching pull request...")
    
    # You can specify PR ID via environment variable
    pr_id = os.environ.get("PR_ID")
    
    try:
        if pr_id:
            # Fetch specific PR
            pr = ado_client.get_pull_request(int(pr_id))
            if not pr:
                print(f"✗ PR #{pr_id} not found")
                return
            print(f"✓ Found PR #{pr.pull_request_id}: {pr.title}")
        else:
            print(f"✗ Please set PR_ID environment variable")
            return
        
        print(f"  - Source: {pr.source_branch} → {pr.target_branch}")
        print(f"  - Status: {pr.status.value}")
        print()
    except Exception as e:
        print(f"✗ Failed to fetch PR: {e}")
        return
    
    # Step 5: Get file changes
    print("Step 5: Getting file changes...")
    try:
        file_diffs = ado_client.get_pull_request_changes(pr.pull_request_id)
        
        # Filter reviewable files
        reviewable_files = ado_client.filter_reviewable_files(
            file_diffs,
            config.review.file_extensions,
            config.review.exclude_patterns
        )
        
        print(f"✓ Found {len(file_diffs)} total changes")
        print(f"✓ Filtered to {len(reviewable_files)} reviewable files")
        
        if not reviewable_files:
            print(f"✗ No reviewable files found")
            return
        
        for file_diff in reviewable_files[:5]:  # Show first 5
            print(f"  - {file_diff.path} (+{file_diff.additions}/-{file_diff.deletions})")
        
        if len(reviewable_files) > 5:
            print(f"  ... and {len(reviewable_files) - 5} more")
        print()
    except Exception as e:
        print(f"✗ Failed to get file changes: {e}")
        return
    
    # Step 6: Get file contents
    print("Step 6: Fetching file contents...")
    try:
        file_contents = {}
        
        # For this example, we'll use simplified content fetching
        # In a real build pipeline task, you'd read from the working directory
        for file_diff in reviewable_files:
            # Placeholder: In real usage, read files from the PR's source branch
            file_contents[file_diff.path] = f"# Content of {file_diff.path}\n# (Would be actual file content in production)"
        
        print(f"✓ Prepared content for {len(file_contents)} files")
        print()
    except Exception as e:
        print(f"✗ Failed to fetch file contents: {e}")
        return
    
    # Step 7: Review with LLM
    print("Step 7: Performing AI review...")
    print(f"  Using {config.llm.provider} ({config.llm.model})")
    print()
    
    try:
        # Determine review mode
        quick_mode = config.review.review_scope == ["security", "critical"]
        
        # Review PR
        review_comments = llm_client.review_pull_request(
            pull_request=pr,
            file_diffs=reviewable_files,
            file_contents=file_contents,
            review_scope=config.review.review_scope,
            quick_mode=quick_mode
        )
        
        print(f"✓ Review complete!")
        print(f"  - Generated {len(review_comments)} comments")
        print()
        
        # Show sample comments
        if review_comments:
            print("Sample comments:")
            for i, comment in enumerate(review_comments[:3], 1):
                print(f"\n  Comment {i}:")
                print(f"  File: {comment.file_path}")
                print(f"  Line: {comment.line_number}")
                print(f"  Severity: {comment.severity}")
                print(f"  Category: {comment.category}")
                print(f"  Content: {comment.content[:100]}...")
            
            if len(review_comments) > 3:
                print(f"\n  ... and {len(review_comments) - 3} more comments")
        print()
        
    except Exception as e:
        print(f"✗ AI review failed: {e}")
        logger.exception("AI review error")
        return
    
    # Step 8: Generate summary
    print("Step 8: Generating review summary...")
    try:
        summary = llm_client.generate_summary(pr, review_comments)
        print(f"✓ Summary generated")
        print()
        print("Summary:")
        print("-" * 80)
        print(summary)
        print("-" * 80)
        print()
    except Exception as e:
        print(f"⚠ Summary generation failed: {e}")
        print()
    
    # Step 9: Post comments (optional)
    post_comments = os.environ.get("POST_COMMENTS", "false").lower() == "true"
    
    if post_comments and review_comments:
        print("Step 9: Posting comments to Azure DevOps...")
        try:
            result = ado_client.post_review_comments(
                pr.pull_request_id,
                review_comments
            )
            
            posted = result.get("posted", 0)
            print(f"✓ Posted {posted} comments to PR")
            print()
        except Exception as e:
            print(f"✗ Failed to post comments: {e}")
            logger.exception("Comment posting error")
    else:
        print("Step 9: Skipping comment posting (set POST_COMMENTS=true to enable)")
        print()
    
    # Done
    print("=" * 80)
    print("Review complete!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
