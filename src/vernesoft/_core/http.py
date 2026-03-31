from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from .errors import VerneAPIError, VerneError

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_RETRY_WAIT = 1.0


def _parse_error(response: httpx.Response) -> VerneAPIError:
    """Parse an error response into a VerneAPIError."""
    try:
        body = response.json()
        err = body.get("error", {})
        code = err.get("code", "unknown_error")
        message = err.get("message", response.text)
        request_id = err.get("request_id", "")
    except Exception:
        code = "unknown_error"
        message = response.text
        request_id = ""
    return VerneAPIError(
        code=code, message=message, status=response.status_code, request_id=request_id
    )


def _build_headers(api_key: str, skip_auth: bool = False) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if not skip_auth:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


class SyncHttpClient:
    """Synchronous HTTP client wrapping httpx.Client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        headers = _build_headers(self._api_key)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self._url(path), headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)
        return response.json()

    def post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        skip_auth: bool = False,
    ) -> Any:
        headers = _build_headers(self._api_key, skip_auth=skip_auth)
        return self._post_with_retry(path, body=body, headers=headers)

    def _post_with_retry(
        self,
        path: str,
        body: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Any:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(self._url(path), headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", _DEFAULT_RETRY_WAIT))
            time.sleep(retry_after)
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(self._url(path), headers=headers, json=body)
            except httpx.TimeoutException as exc:
                raise VerneError(f"Request timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise VerneError(f"Network error: {exc}") from exc

        if not response.is_success:
            raise _parse_error(response)
        if response.status_code == 204:
            return None
        return response.json()

    def patch(self, path: str, body: Any) -> Any:
        headers = _build_headers(self._api_key)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.patch(self._url(path), headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)
        return response.json()

    def delete(self, path: str) -> None:
        headers = _build_headers(self._api_key)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.delete(self._url(path), headers=headers)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)


class AsyncHttpClient:
    """Asynchronous HTTP client wrapping httpx.AsyncClient."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        headers = _build_headers(self._api_key)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._url(path), headers=headers, params=params)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)
        return response.json()

    async def post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        skip_auth: bool = False,
    ) -> Any:
        headers = _build_headers(self._api_key, skip_auth=skip_auth)
        return await self._post_with_retry(path, body=body, headers=headers)

    async def _post_with_retry(
        self,
        path: str,
        body: Optional[Dict[str, Any]],
        headers: Dict[str, str],
    ) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url(path), headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", _DEFAULT_RETRY_WAIT))
            await asyncio.sleep(retry_after)
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self._url(path), headers=headers, json=body)
            except httpx.TimeoutException as exc:
                raise VerneError(f"Request timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise VerneError(f"Network error: {exc}") from exc

        if not response.is_success:
            raise _parse_error(response)
        if response.status_code == 204:
            return None
        return response.json()

    async def patch(self, path: str, body: Any) -> Any:
        headers = _build_headers(self._api_key)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.patch(self._url(path), headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)
        return response.json()

    async def delete(self, path: str) -> None:
        headers = _build_headers(self._api_key)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.delete(self._url(path), headers=headers)
        except httpx.TimeoutException as exc:
            raise VerneError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise VerneError(f"Network error: {exc}") from exc
        if not response.is_success:
            raise _parse_error(response)
