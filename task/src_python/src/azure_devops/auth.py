"""Authentication and connection management for Azure DevOps."""

import base64
import requests
from typing import Optional, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config.config import AzureDevOpsConfig
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AzureDevOpsAuth:
    """Handles authentication for Azure DevOps API."""

    def __init__(self, config: AzureDevOpsConfig):
        """
        Initialize authentication.

        Args:
            config: Azure DevOps configuration
        """
        self.config = config
        self._session: Optional[requests.Session] = None

    def get_session(self) -> requests.Session:
        """
        Get or create authenticated session with retry logic.

        Returns:
            Configured requests session
        """
        if self._session is None:
            self._session = self._create_session()

        return self._session

    def _create_session(self) -> requests.Session:
        """
        Create a new authenticated session.

        Returns:
            Configured requests session with auth and retry logic
        """
        session = requests.Session()

        # Set up authentication header
        auth_header = self._create_auth_header()
        session.headers.update(auth_header)

        # Set common headers
        session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Configure SSL verification
        session.verify = self.config.verify_ssl

        if not self.config.verify_ssl:
            # Suppress SSL warnings when verification is disabled
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL verification is disabled. This is not recommended for production.")

        logger.debug("Created new Azure DevOps session")

        return session

    def _create_auth_header(self) -> dict:
        """
        Create authentication header using PAT token.

        Returns:
            Dictionary with Authorization header

        Raises:
            ValueError: If PAT token is not configured
        """
        if not self.config.pat_token:
            raise ValueError(
                "PAT token is required for authentication. "
                "Set it in config.yaml or AZDO_PERSONAL_ACCESS_TOKEN environment variable."
            )

        # Azure DevOps uses Basic Auth with PAT token
        # Username can be empty, password is the PAT token
        credentials = f":{self.config.pat_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        return {"Authorization": f"Basic {encoded_credentials}"}

    def close(self) -> None:
        """Close the session and release resources."""
        if self._session:
            self._session.close()
            self._session = None
            logger.debug("Closed Azure DevOps session")

    def test_connection(self) -> bool:
        """
        Test the connection to Azure DevOps.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            session = self.get_session()

            # Try to access the projects endpoint
            url = f"{self.config.organization_url}/_apis/projects?api-version=7.0"

            logger.debug(f"Testing connection to {url}")
            response = session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            logger.info("Successfully connected to Azure DevOps")
            return True

        except requests.exceptions.SSLError as e:
            logger.error(f"SSL verification failed: {e}")
            logger.error(
                "Consider setting verify_ssl: false in config for self-signed certificates"
            )
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Azure DevOps: {e}")
            return False

    def __enter__(self) -> "AzureDevOpsAuth":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def create_authenticated_session(config: AzureDevOpsConfig) -> requests.Session:
    """
    Helper function to create an authenticated session.

    Args:
        config: Azure DevOps configuration

    Returns:
        Configured and authenticated session
    """
    auth = AzureDevOpsAuth(config)
    return auth.get_session()
