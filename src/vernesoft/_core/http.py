from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Mapping, Optional, Union
from urllib.parse import quote

import httpx

from .errors import VerneAPIError, VerneError

DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_BASE_URL = DEFAULT_BASE_URL
_DEFAULT_TIMEOUT = 30.0

#: Waited out before the one retry of a ``POST`` answered ``429`` without ``Retry-After``.
_DEFAULT_RETRY_WAIT = 1.0
#: The longest ``Retry-After`` the client waits out on its own. Anything longer — Relay's
#: monthly limit answers with the seconds until the 1st of next month — is raised at once,
#: with ``retry_after`` on the error, for the caller to decide.
_MAX_AUTO_RETRY_AFTER_SECONDS = 60.0
#: A ``429`` that waiting a few seconds does not lift.
_NON_RETRYABLE_429_CODES = frozenset({"RELAY_MESSAGE_LIMIT_REACHED"})

QueryValue = Union[str, int, float, bool, datetime, None]


def seg(value: str) -> str:
    """One URL path segment, percent-encoded: ids come from callers and must not
    reshape the path."""
    return quote(str(value), safe="")


def rfc3339(value: Union[str, datetime]) -> str:
    """A time as RFC 3339 UTC. A naive ``datetime`` is taken to be UTC already."""
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_query(params: Optional[Mapping[str, QueryValue]]) -> Optional[Dict[str, str]]:
    """Query parameters with ``None`` dropped, a ``datetime`` as RFC 3339, a bool as
    ``true``/``false``."""
    if not params:
        return None
    out: Dict[str, str] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, datetime):
            out[key] = rfc3339(value)
        else:
            out[key] = str(value)
    return out or None


def parse_retry_after(raw: Optional[str]) -> Optional[float]:
    """Seconds from a ``Retry-After`` header (delta-seconds or an HTTP date), or None."""
    if raw is None or not raw.strip():
        return None
    try:
        seconds = float(raw.strip())
    except ValueError:
        seconds = -1.0
    else:
        if seconds >= 0 and seconds == seconds and seconds != float("inf"):
            return seconds
        return None
    try:
        at = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return float(max(0, int((at - datetime.now(timezone.utc)).total_seconds() + 0.999)))


def _build_headers(
    api_key: str, skip_auth: bool = False, session_token: Optional[str] = None
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if not skip_auth:
        headers["Authorization"] = f"Bearer {api_key}"
    if session_token is not None:
        headers["X-Session-Token"] = session_token
    return headers


def _parse_error(response: httpx.Response) -> VerneAPIError:
    """Turn an error response into a VerneAPIError. Never raises on its own."""
    retry_after = parse_retry_after(response.headers.get("Retry-After"))
    try:
        body: Any = response.json()
    except Exception:
        body = None
    return VerneAPIError.from_response(response.status_code, body, retry_after)


def _retry_wait(method: str, attempt: int, error: VerneAPIError) -> Optional[float]:
    """Seconds to wait before the one retry, or None when the error must be raised.

    Only a ``POST`` answered ``429`` is retried, once, and only when the wait is short
    (``Retry-After`` ≤ 60 s, 1 s when absent) and the limit is not one that lifts at the
    end of the month. A ``402`` is never retried.
    """
    if error.status != 429 or attempt != 1 or method != "POST":
        return None
    if error.code in _NON_RETRYABLE_429_CODES:
        return None
    wait = error.retry_after if error.retry_after is not None else _DEFAULT_RETRY_WAIT
    if wait > _MAX_AUTO_RETRY_AFTER_SECONDS:
        return None
    return wait


def _decode(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise VerneError(f"Response was not JSON (HTTP {response.status_code}): {exc}") from exc


class _Base:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        """The API base URL, without a trailing slash."""
        return self._base_url

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _request_kwargs(
        self,
        params: Optional[Mapping[str, QueryValue]],
        body: Any,
        skip_auth: bool,
        session_token: Optional[str],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "headers": _build_headers(self._api_key, skip_auth, session_token),
        }
        query = build_query(params)
        if query is not None:
            kwargs["params"] = query
        if body is not None:
            kwargs["json"] = body
        return kwargs


class SyncHttpClient(_Base):
    """Synchronous HTTP client wrapping httpx.Client."""

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, QueryValue]] = None,
        body: Any = None,
        skip_auth: bool = False,
        session_token: Optional[str] = None,
    ) -> Any:
        kwargs = self._request_kwargs(params, body, skip_auth, session_token)
        attempt = 1
        while True:
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.request(method, self._url(path), **kwargs)
            except httpx.TimeoutException as exc:
                raise VerneError(f"Request timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise VerneError(f"Network error: {exc}") from exc
            if response.is_success:
                return _decode(response)
            error = _parse_error(response)
            wait = _retry_wait(method, attempt, error)
            if wait is None:
                raise error
            time.sleep(wait)
            attempt += 1

    def get(
        self,
        path: str,
        params: Optional[Mapping[str, QueryValue]] = None,
        *,
        skip_auth: bool = False,
        session_token: Optional[str] = None,
    ) -> Any:
        return self.request(
            "GET", path, params=params, skip_auth=skip_auth, session_token=session_token
        )

    def post(
        self,
        path: str,
        body: Any = None,
        skip_auth: bool = False,
        *,
        session_token: Optional[str] = None,
    ) -> Any:
        return self.request(
            "POST", path, body=body, skip_auth=skip_auth, session_token=session_token
        )

    def put(self, path: str, body: Any = None) -> Any:
        return self.request("PUT", path, body=body)

    def patch(self, path: str, body: Any = None) -> Any:
        return self.request("PATCH", path, body=body)

    def delete(self, path: str, params: Optional[Mapping[str, QueryValue]] = None) -> Any:
        return self.request("DELETE", path, params=params)


class AsyncHttpClient(_Base):
    """Asynchronous HTTP client wrapping httpx.AsyncClient."""

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, QueryValue]] = None,
        body: Any = None,
        skip_auth: bool = False,
        session_token: Optional[str] = None,
    ) -> Any:
        kwargs = self._request_kwargs(params, body, skip_auth, session_token)
        attempt = 1
        while True:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(method, self._url(path), **kwargs)
            except httpx.TimeoutException as exc:
                raise VerneError(f"Request timed out: {exc}") from exc
            except httpx.RequestError as exc:
                raise VerneError(f"Network error: {exc}") from exc
            if response.is_success:
                return _decode(response)
            error = _parse_error(response)
            wait = _retry_wait(method, attempt, error)
            if wait is None:
                raise error
            await asyncio.sleep(wait)
            attempt += 1

    async def get(
        self,
        path: str,
        params: Optional[Mapping[str, QueryValue]] = None,
        *,
        skip_auth: bool = False,
        session_token: Optional[str] = None,
    ) -> Any:
        return await self.request(
            "GET", path, params=params, skip_auth=skip_auth, session_token=session_token
        )

    async def post(
        self,
        path: str,
        body: Any = None,
        skip_auth: bool = False,
        *,
        session_token: Optional[str] = None,
    ) -> Any:
        return await self.request(
            "POST", path, body=body, skip_auth=skip_auth, session_token=session_token
        )

    async def put(self, path: str, body: Any = None) -> Any:
        return await self.request("PUT", path, body=body)

    async def patch(self, path: str, body: Any = None) -> Any:
        return await self.request("PATCH", path, body=body)

    async def delete(self, path: str, params: Optional[Mapping[str, QueryValue]] = None) -> Any:
        return await self.request("DELETE", path, params=params)
