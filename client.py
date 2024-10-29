import requests
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger('werkzeug').setLevel(logging.ERROR)

class JobStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class StatusResponse:
    status: JobStatus
    raw_response: dict

class StatusError(Exception):
    """Custom exception for status-related errors"""
    pass

class RetryConfig:
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        max_retries: int = 10,
        backoff_factor: float = 1.5
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

class StatusClient:
    def __init__(
        self,
        base_url: str,
        retry_config: Optional[RetryConfig] = None,
        status_callback: Optional[Callable[[StatusResponse], None]] = None
    ):
        """
        Initialize the Status Client
        
        Args:
            base_url: Base URL of the status API
            retry_config: Configuration for retry behavior
            status_callback: Optional callback function for status updates
        """
        self.base_url = base_url.rstrip('/')
        self.retry_config = retry_config or RetryConfig()
        self.status_callback = status_callback
        self.session = requests.Session()
    
    def _make_request(self) -> requests.Response:
        """Make HTTP request with error handling"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise StatusError(f"Failed to fetch status: {str(e)}")

    def get_status(self) -> StatusResponse:
        """Get current status without polling"""
        response = self._make_request()
        data = response.json()
        status = JobStatus(data["result"])
        return StatusResponse(status=status, raw_response=data)

    def wait_for_completion(
        self,
        timeout: Optional[float] = None
    ) -> StatusResponse:
        """
        Poll for status until completion or timeout
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            Final status response
        
        Raises:
            StatusError: If timeout occurs or max retries exceeded
        """
        start_time = time.time()
        current_delay = self.retry_config.initial_delay
        attempts = 0

        while True:
            if timeout and (time.time() - start_time) > timeout:
                raise StatusError("Timeout waiting for completion")

            if attempts >= self.retry_config.max_retries:
                raise StatusError("Max retry attempts exceeded")

            status_response = self.get_status()
            
            if self.status_callback:
                self.status_callback(status_response)

            if status_response.status in (JobStatus.COMPLETED, JobStatus.ERROR):
                logger.info("Status returned")
                return status_response

            logger.info(f"Status still pending, waiting {current_delay}s before retry")
            time.sleep(current_delay)
            
            # exponential backoff
            current_delay = min(
                current_delay * self.retry_config.backoff_factor,
                self.retry_config.max_delay
            )
            attempts += 1