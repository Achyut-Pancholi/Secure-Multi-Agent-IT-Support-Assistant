import httpx
from typing import Dict, Any, Optional
import time
from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

class InternalAPIError(Exception):
    pass

class InternalAPIClient:
    """
    Client for communicating with the mock internal IT API.
    Implements bounded retries and strict timeouts.
    """
    
    def __init__(self):
        self.base_url = settings.internal_api_url.rstrip("/")
        # Using a hardcoded token for the POC
        self.token = "mock-internal-token-secret"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.timeout = 5.0  # 5 seconds timeout for all network calls
        self.max_retries = 2

    def _request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Executes an HTTP request with bounded retries for transient failures.
        Does NOT retry non-idempotent operations like POST if the failure is ambiguous (like a timeout).
        """
        url = f"{self.base_url}{endpoint}"
        retries = 0
        
        while retries <= self.max_retries:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    start_time = time.time()
                    response = client.request(method, url, headers=self.headers, **kwargs)
                    duration = time.time() - start_time
                    
                    logger.info(f"API Call {method} {endpoint} completed in {duration:.2f}s with status {response.status_code}")
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on {method} {endpoint} (Attempt {retries + 1}/{self.max_retries + 1})")
                if method.upper() == "POST":
                    logger.error("Timeout on POST request. Not retrying non-idempotent operation.")
                    raise InternalAPIError("Operation timed out. Ticket creation status unknown.")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error {e.response.status_code} on {method} {endpoint}: {e.response.text}")
                # Don't retry 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    raise InternalAPIError(f"Client error: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                logger.warning(f"Request Error on {method} {endpoint} (Attempt {retries + 1}/{self.max_retries + 1}): {str(e)}")
            
            retries += 1
            if retries <= self.max_retries:
                time.sleep(1) # simple backoff
                
        raise InternalAPIError(f"Failed to communicate with internal API after {self.max_retries + 1} attempts")

    def get_user_access(self, user_id: str) -> Dict[str, Any]:
        """Check user access rights"""
        return self._request_with_retry("GET", f"/internal/users/{user_id}/access")

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Check status of a specific service"""
        return self._request_with_retry("GET", f"/internal/services/{service_name}/status")

    def create_ticket(self, user_id: str, description: str, category: str, priority: str) -> Dict[str, Any]:
        """Create a new support ticket"""
        payload = {
            "user_id": user_id,
            "description": description,
            "category": category,
            "priority": priority
        }
        return self._request_with_retry("POST", "/internal/tickets", json=payload)

