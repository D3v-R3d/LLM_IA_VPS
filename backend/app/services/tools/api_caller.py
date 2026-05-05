"""
API Caller Service

Makes HTTP requests to external APIs.
"""

import httpx
import logging
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class APICallerService:
    """
    Service for making HTTP API requests.

    Supports GET, POST, PUT, PATCH, DELETE methods
    with custom headers and body.
    """

    async def call(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            headers: Optional HTTP headers
            body: Optional request body (for POST/PUT/PATCH)
            timeout: Request timeout in seconds

        Returns:
            Response status, body, and metadata

        Example:
            result = await service.call(
                "https://api.example.com/data",
                method="POST",
                headers={"Authorization": "Bearer token"},
                body={"key": "value"}
            )
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                request_headers = headers or {}
                request_headers["User-Agent"] = "TowerBot/1.0"

                request_kwargs = {
                    "url": url,
                    "headers": request_headers
                }

                if method.upper() in ["POST", "PUT", "PATCH"] and body:
                    request_kwargs["json"] = body

                response = await client.request(method, **request_kwargs)

                return {
                    "success": True,
                    "url": url,
                    "method": method,
                    "status": response.status_code,
                    "body": response.text[:4000],
                    "headers": dict(response.headers)
                }

        except Exception as e:
            logger.error(f"API call error: {e}")
            return {
                "success": False,
                "url": url,
                "method": method,
                "error": str(e)
            }

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return await self.call(url, "GET", headers)

    async def post(
        self,
        url: str,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.call(url, "POST", headers, body)

    async def put(
        self,
        url: str,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.call(url, "PUT", headers, body)

    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.call(url, "DELETE", headers)