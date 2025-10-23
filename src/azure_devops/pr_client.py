"""Pull request operations for Azure DevOps."""

import requests
from typing import List, Optional, Dict, Any
import logging

from ..config.config import AzureDevOpsConfig
from ..utils.logger import setup_logger
from .models import PullRequest, FileDiff, CommentThread
from .auth import AzureDevOpsAuth

logger = setup_logger(__name__)


class PullRequestClient:
    """Client for pull request operations."""
    
    def __init__(self, config: AzureDevOpsConfig, auth: AzureDevOpsAuth):
        """
        Initialize PR client.
        
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
    
    def get_pull_request(self, pr_id: int) -> Optional[PullRequest]:
        """
        Get pull request details.
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            PullRequest object or None if not found
        
        Raises:
            requests.RequestException: On API errors
        """
        url = f"{self.base_url}/pullrequests/{pr_id}?api-version={self.api_version}"
        
        logger.info(f"Fetching PR #{pr_id}")
        logger.debug(f"URL: {url}")
        
        try:
            session = self.auth.get_session()
            response = session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            pr = PullRequest.from_api(data)
            
            logger.info(f"Successfully fetched PR #{pr_id}: {pr.title}")
            return pr
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"PR #{pr_id} not found")
                return None
            logger.error(f"HTTP error fetching PR #{pr_id}: {e}")
            raise
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching PR #{pr_id}: {e}")
            raise
    
    def get_pull_request_changes(self, pr_id: int) -> List[FileDiff]:
        """
        Get file changes (diffs) for a pull request.
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            List of FileDiff objects
        
        Raises:
            requests.RequestException: On API errors
        """
        # First, get the iterations (commits) for the PR
        iterations_url = (
            f"{self.base_url}/pullrequests/{pr_id}/iterations?"
            f"api-version={self.api_version}"
        )
        
        logger.info(f"Fetching changes for PR #{pr_id}")
        
        try:
            session = self.auth.get_session()
            
            # Get iterations
            response = session.get(iterations_url, timeout=self.config.timeout)
            response.raise_for_status()
            iterations_data = response.json()
            
            iterations = iterations_data.get("value", [])
            if not iterations:
                logger.warning(f"No iterations found for PR #{pr_id}")
                return []
            
            # Get the latest iteration
            latest_iteration = iterations[-1]
            iteration_id = latest_iteration.get("id")
            
            # Get changes for the latest iteration
            changes_url = (
                f"{self.base_url}/pullrequests/{pr_id}/iterations/{iteration_id}/changes?"
                f"api-version={self.api_version}"
            )
            
            response = session.get(changes_url, timeout=self.config.timeout)
            response.raise_for_status()
            changes_data = response.json()
            
            # Parse file diffs
            file_diffs = []
            for change in changes_data.get("changeEntries", []):
                file_diff = FileDiff.from_api(change)
                file_diffs.append(file_diff)
            
            logger.info(f"Found {len(file_diffs)} file changes for PR #{pr_id}")
            return file_diffs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching changes for PR #{pr_id}: {e}")
            raise
    
    def get_file_diff_content(
        self, 
        pr_id: int, 
        file_path: str,
        base_version: Optional[str] = None,
        target_version: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the actual diff content for a specific file.
        
        Args:
            pr_id: Pull request ID
            file_path: Path to the file
            base_version: Base commit/version (optional)
            target_version: Target commit/version (optional)
        
        Returns:
            Diff content as string or None if not available
        
        Raises:
            requests.RequestException: On API errors
        """
        # Azure DevOps doesn't provide a direct diff endpoint
        # We need to get the file content from both versions and compute diff
        # For now, we'll get the file content from the source branch
        
        logger.debug(f"Fetching diff content for {file_path} in PR #{pr_id}")
        
        try:
            # Get PR details to get source and target branch
            pr = self.get_pull_request(pr_id)
            if not pr:
                return None
            
            # Get file content from source branch
            source_url = (
                f"{self.base_url}/items?path={file_path}&"
                f"versionDescriptor.version={pr.source_branch.replace('refs/heads/', '')}&"
                f"versionDescriptor.versionType=branch&"
                f"api-version={self.api_version}"
            )
            
            session = self.auth.get_session()
            response = session.get(source_url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                source_content = response.text
                logger.debug(f"Retrieved content for {file_path}")
                return source_content
            else:
                logger.warning(f"Could not retrieve content for {file_path}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching diff content for {file_path}: {e}")
            return None
    
    def get_pull_request_threads(self, pr_id: int) -> List[CommentThread]:
        """
        Get all comment threads for a pull request.
        
        Args:
            pr_id: Pull request ID
        
        Returns:
            List of CommentThread objects
        
        Raises:
            requests.RequestException: On API errors
        """
        url = (
            f"{self.base_url}/pullrequests/{pr_id}/threads?"
            f"api-version={self.api_version}"
        )
        
        logger.info(f"Fetching comment threads for PR #{pr_id}")
        
        try:
            session = self.auth.get_session()
            response = session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            threads = []
            
            for thread_data in data.get("value", []):
                thread = CommentThread.from_api(thread_data)
                threads.append(thread)
            
            logger.info(f"Found {len(threads)} comment threads for PR #{pr_id}")
            return threads
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching threads for PR #{pr_id}: {e}")
            raise
    
    def list_pull_requests(
        self,
        status: str = "active",
        creator_id: Optional[str] = None,
        reviewer_id: Optional[str] = None,
        top: int = 100
    ) -> List[PullRequest]:
        """
        List pull requests with filters.
        
        Args:
            status: PR status (active, completed, abandoned, all)
            creator_id: Filter by creator ID
            reviewer_id: Filter by reviewer ID
            top: Maximum number of results
        
        Returns:
            List of PullRequest objects
        
        Raises:
            requests.RequestException: On API errors
        """
        params = {
            "api-version": self.api_version,
            "searchCriteria.status": status,
            "$top": top,
        }
        
        if creator_id:
            params["searchCriteria.creatorId"] = creator_id
        
        if reviewer_id:
            params["searchCriteria.reviewerId"] = reviewer_id
        
        url = f"{self.base_url}/pullrequests"
        
        logger.info(f"Listing pull requests (status: {status}, top: {top})")
        
        try:
            session = self.auth.get_session()
            response = session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            data = response.json()
            pull_requests = []
            
            for pr_data in data.get("value", []):
                pr = PullRequest.from_api(pr_data)
                pull_requests.append(pr)
            
            logger.info(f"Found {len(pull_requests)} pull requests")
            return pull_requests
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error listing pull requests: {e}")
            raise
