#!/usr/bin/env python3
"""
Main script for executing AI-powered PR reviews in Azure Pipelines.

This script is the entry point called by the Azure Pipelines task.
It orchestrates the entire review workflow.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.config import load_config, load_config_from_env, Config
from src.azure_devops.client import AzureDevOpsClient
from src.llm.review_client import LLMReviewClient
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='AI-powered code review for Azure DevOps pull requests'
    )
    
    parser.add_argument(
        '--pr-id',
        type=int,
        required=True,
        help='Pull request ID to review'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (YAML)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run review but do not post comments'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for review results (JSON)'
    )
    
    return parser.parse_args()


def load_configuration(config_path: str = None) -> Config:
    """
    Load configuration from file or environment.
    
    Args:
        config_path: Optional path to config file
    
    Returns:
        Configuration object
    """
    logger.info("Loading configuration...")
    
    try:
        if config_path and os.path.exists(config_path):
            logger.info(f"Loading config from file: {config_path}")
            config = load_config(config_path)
        else:
            logger.info("Loading config from environment variables")
            config = load_config_from_env()
        
        logger.info(f"Configuration loaded successfully")
        logger.info(f"  LLM Provider: {config.llm.provider.value}")
        logger.info(f"  Model: {config.llm.model}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise


def test_connections(ado_client: AzureDevOpsClient, llm_client: LLMReviewClient) -> bool:
    """
    Test connections to Azure DevOps and LLM provider.
    
    Args:
        ado_client: Azure DevOps client
        llm_client: LLM client
    
    Returns:
        True if both connections successful
    """
    logger.info("Testing connections...")
    
    # Test Azure DevOps
    try:
        if not ado_client.test_connection():
            logger.error("Azure DevOps connection test failed")
            return False
        logger.info("✓ Azure DevOps connection successful")
    except Exception as e:
        logger.error(f"Azure DevOps connection error: {e}")
        return False
    
    # Test LLM
    try:
        if not llm_client.test_connection():
            logger.error("LLM connection test failed")
            return False
        logger.info("✓ LLM connection successful")
    except Exception as e:
        logger.error(f"LLM connection error: {e}")
        return False
    
    return True


def get_reviewable_files(
    ado_client: AzureDevOpsClient,
    pr_id: int,
    config: Config
) -> tuple:
    """
    Get list of files to review from the PR.
    
    Args:
        ado_client: Azure DevOps client
        pr_id: Pull request ID
        config: Configuration
    
    Returns:
        Tuple of (file_diffs, file_contents)
    """
    logger.info(f"Fetching files for PR #{pr_id}...")
    
    # Get file changes
    file_diffs = ado_client.get_pull_request_changes(pr_id)
    logger.info(f"Found {len(file_diffs)} changed files")
    
    # Filter reviewable files
    reviewable_files = ado_client.filter_reviewable_files(
        file_diffs,
        config.review.file_extensions,
        config.review.exclude_patterns
    )
    
    logger.info(f"Filtered to {len(reviewable_files)} reviewable files")
    
    if not reviewable_files:
        logger.warning("No reviewable files found")
        return [], {}
    
    # Get file contents
    # In a build pipeline, we read from the working directory
    file_contents = {}
    source_dir = Path(os.environ.get('BUILD_SOURCESDIRECTORY', os.getcwd()))
    
    for file_diff in reviewable_files:
        file_path = source_dir / file_diff.path
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_contents[file_diff.path] = f.read()
                logger.debug(f"Loaded content for {file_diff.path}")
            except Exception as e:
                logger.warning(f"Could not read {file_diff.path}: {e}")
        else:
            logger.warning(f"File not found in working directory: {file_diff.path}")
    
    logger.info(f"Loaded content for {len(file_contents)} files")
    
    return reviewable_files, file_contents


def perform_review(
    llm_client: LLMReviewClient,
    pr,
    file_diffs,
    file_contents: Dict[str, str],
    config: Config
):
    """
    Perform AI code review.
    
    Args:
        llm_client: LLM client
        pr: Pull request object
        file_diffs: List of file changes
        file_contents: Dictionary of file contents
        config: Configuration
    
    Returns:
        List of review comments
    """
    logger.info("Starting AI code review...")
    
    # Determine review mode
    quick_mode = os.environ.get('QUICK_MODE', 'false').lower() == 'true'
    max_issues = int(os.environ.get('MAX_ISSUES_PER_FILE', '10'))
    
    # Perform review
    comments = llm_client.review_pull_request(
        pull_request=pr,
        file_diffs=file_diffs,
        file_contents=file_contents,
        review_scope=config.review.review_scope,
        quick_mode=quick_mode
    )
    
    logger.info(f"Generated {len(comments)} review comments")
    
    # Limit issues per file if configured
    if max_issues > 0:
        comments_by_file = {}
        for comment in comments:
            if comment.file_path not in comments_by_file:
                comments_by_file[comment.file_path] = []
            comments_by_file[comment.file_path].append(comment)
        
        limited_comments = []
        for file_path, file_comments in comments_by_file.items():
            # Sort by severity (critical first)
            severity_order = {'critical': 0, 'error': 1, 'warning': 2, 'suggestion': 3}
            file_comments.sort(key=lambda c: severity_order.get(c.severity, 99))
            
            # Take top N
            limited_comments.extend(file_comments[:max_issues])
        
        if len(limited_comments) < len(comments):
            logger.info(f"Limited to {len(limited_comments)} comments (max {max_issues} per file)")
            comments = limited_comments
    
    return comments


def calculate_statistics(comments: List) -> Dict[str, Any]:
    """Calculate review statistics."""
    stats = {
        'total_issues': len(comments),
        'by_severity': {},
        'by_category': {},
        'critical_count': 0
    }
    
    for comment in comments:
        # Count by severity
        severity = comment.severity
        stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
        
        if severity in ['critical', 'error']:
            stats['critical_count'] += 1
        
        # Count by category
        category = comment.category
        stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
    
    return stats


def post_results(
    ado_client: AzureDevOpsClient,
    llm_client: LLMReviewClient,
    pr,
    pr_id: int,
    comments: List,
    dry_run: bool
) -> Dict[str, Any]:
    """
    Post review comments and summary to Azure DevOps.
    
    Args:
        ado_client: Azure DevOps client
        llm_client: LLM client
        pr: Pull request object
        pr_id: Pull request ID
        comments: List of review comments
        dry_run: If True, don't actually post
    
    Returns:
        Results dictionary
    """
    results = {
        'comments_posted': 0,
        'summary_posted': False
    }
    
    post_comments = os.environ.get('POST_COMMENTS', 'true').lower() == 'true'
    post_summary = os.environ.get('POST_SUMMARY', 'true').lower() == 'true'
    comment_style = os.environ.get('COMMENT_STYLE', 'constructive')
    
    if dry_run:
        logger.info("Dry run mode - skipping comment posting")
        return results
    
    # Post comments
    if post_comments and comments:
        logger.info(f"Posting {len(comments)} comments to PR...")
        try:
            result = ado_client.post_review_comments(
                pr_id,
                comments,
                comment_style
            )
            results['comments_posted'] = result.get('posted', 0)
            logger.info(f"✓ Posted {results['comments_posted']} comments")
        except Exception as e:
            logger.error(f"Failed to post comments: {e}")
    
    # Generate and post summary
    if post_summary and comments:
        logger.info("Generating review summary...")
        try:
            summary = llm_client.generate_summary(pr, comments)
            
            logger.info("Posting summary comment...")
            thread = ado_client.post_summary_comment(pr_id, summary)
            
            if thread:
                results['summary_posted'] = True
                logger.info("✓ Posted summary comment")
            
        except Exception as e:
            logger.error(f"Failed to post summary: {e}")
    
    return results


def save_results(
    output_path: str,
    comments: List,
    stats: Dict[str, Any],
    results: Dict[str, Any]
):
    """Save results to JSON file."""
    logger.info(f"Saving results to {output_path}...")
    
    output_data = {
        'statistics': stats,
        'posting_results': results,
        'comments': [
            {
                'file_path': c.file_path,
                'line_number': c.line_number,
                'severity': c.severity,
                'category': c.category,
                'content': c.content
            }
            for c in comments
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    
    logger.info(f"✓ Results saved to {output_path}")


def set_output_variables(stats: Dict[str, Any], summary: str = None):
    """Set Azure Pipelines output variables."""
    # Set environment variables that the task will read
    os.environ['AI_REVIEW_ISSUE_COUNT'] = str(stats['total_issues'])
    os.environ['AI_REVIEW_CRITICAL_COUNT'] = str(stats['critical_count'])
    
    if summary:
        os.environ['AI_REVIEW_SUMMARY'] = summary
    
    # Also write to Azure Pipelines format
    # ##vso[task.setvariable variable=NAME]VALUE
    print(f"##vso[task.setvariable variable=AI_REVIEW_ISSUE_COUNT]{stats['total_issues']}")
    print(f"##vso[task.setvariable variable=AI_REVIEW_CRITICAL_COUNT]{stats['critical_count']}")


def main():
    """Main execution function."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        logger.info("=" * 80)
        logger.info("AI Code Review - Azure Pipelines Task")
        logger.info("=" * 80)
        logger.info(f"Pull Request ID: {args.pr_id}")
        if args.dry_run:
            logger.info("Mode: DRY RUN (no comments will be posted)")
        logger.info("")
        
        # Load configuration
        config = load_configuration(args.config)
        
        # Initialize clients
        logger.info("Initializing clients...")
        ado_client = AzureDevOpsClient(config.azure_devops)
        llm_client = LLMReviewClient(config.llm)
        logger.info("✓ Clients initialized")
        
        # Test connections
        if not test_connections(ado_client, llm_client):
            logger.error("Connection tests failed")
            sys.exit(1)
        
        # Get PR
        logger.info(f"Fetching PR #{args.pr_id}...")
        pr = ado_client.get_pull_request(args.pr_id)
        
        if not pr:
            logger.error(f"PR #{args.pr_id} not found")
            sys.exit(1)
        
        logger.info(f"✓ Found PR: {pr.title}")
        logger.info(f"  Source: {pr.source_branch} → {pr.target_branch}")
        logger.info("")
        
        # Get reviewable files
        file_diffs, file_contents = get_reviewable_files(ado_client, args.pr_id, config)
        
        if not file_contents:
            logger.warning("No files to review")
            print("\n⚠️  No reviewable files found in this PR")
            sys.exit(0)
        
        # Perform review
        comments = perform_review(llm_client, pr, file_diffs, file_contents, config)
        
        # Calculate statistics
        stats = calculate_statistics(comments)
        
        logger.info("")
        logger.info("📊 Review Statistics:")
        logger.info(f"  Total Issues: {stats['total_issues']}")
        logger.info(f"  Critical/Error: {stats['critical_count']}")
        for severity, count in stats['by_severity'].items():
            logger.info(f"    {severity}: {count}")
        logger.info("")
        
        # Post results
        if comments:
            results = post_results(
                ado_client,
                llm_client,
                pr,
                args.pr_id,
                comments,
                args.dry_run
            )
        else:
            logger.info("✅ No issues found - PR looks good!")
            results = {'comments_posted': 0, 'summary_posted': False}
        
        # Save results to file if requested
        if args.output:
            save_results(args.output, comments, stats, results)
        
        # Set output variables
        set_output_variables(stats)
        
        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ AI Code Review Completed Successfully")
        logger.info(f"   Issues Found: {stats['total_issues']}")
        if not args.dry_run:
            logger.info(f"   Comments Posted: {results['comments_posted']}")
            logger.info(f"   Summary Posted: {'Yes' if results['summary_posted'] else 'No'}")
        logger.info("=" * 80)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.exception("Unexpected error during review")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
