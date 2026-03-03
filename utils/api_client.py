"""Async HTTP client with retry logic and rate limiting."""
import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds


class APIError(Exception):
    """Raised when an API call fails after all retries."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """Async HTTP client with retry/back-off and simple token-bucket rate limiting.

    Args:
        base_url: Base URL prepended to all relative paths.
        default_headers: Headers included in every request.
        requests_per_second: Max requests per second (rate limiter).
        timeout: Per-request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = "",
        default_headers: Optional[Dict[str, str]] = None,
        requests_per_second: float = 2.0,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self._min_interval = 1.0 / requests_per_second
        self._last_call: float = 0.0
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Perform an HTTP GET request with retry logic.

        Args:
            path: URL path (relative to *base_url* or absolute).
            params: Query parameters.
            headers: Additional per-request headers.

        Returns:
            Parsed JSON response (dict/list) or raw bytes when content-type
            is not JSON.

        Raises:
            APIError: On non-2xx response after all retries.
        """
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Perform an HTTP POST request with retry logic.

        Args:
            path: URL path (relative to *base_url* or absolute).
            json: JSON-serialisable body dict.
            data: Raw bytes body (mutually exclusive with *json*).
            headers: Additional per-request headers.

        Returns:
            Parsed JSON response or raw bytes.

        Raises:
            APIError: On non-2xx response after all retries.
        """
        return await self._request("POST", path, json=json, data=data, headers=headers)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _rate_limit(self) -> None:
        """Ensure we don't exceed the configured request rate."""
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_call)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call = time.monotonic()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        merged_headers = {**self.default_headers, **(headers or {})}

        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(1, _MAX_RETRIES + 1):
            await self._rate_limit()
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(
                        method,
                        url,
                        params=params,
                        json=json,
                        content=data,
                        headers=merged_headers,
                    )
                if response.status_code < 500:
                    # 4xx — don't retry
                    if not response.is_success:
                        raise APIError(
                            f"HTTP {response.status_code}: {response.text[:200]}",
                            status_code=response.status_code,
                        )
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        return response.json()
                    return response.content
                # 5xx — retry
                last_exc = APIError(
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    status_code=response.status_code,
                )
            except httpx.RequestError as exc:
                last_exc = APIError(f"Request error: {exc}")

            backoff = _BACKOFF_BASE ** attempt
            logger.warning(
                f"Attempt {attempt}/{_MAX_RETRIES} failed for {method} {url}. "
                f"Retrying in {backoff:.1f}s…"
            )
            await asyncio.sleep(backoff)

        raise last_exc
