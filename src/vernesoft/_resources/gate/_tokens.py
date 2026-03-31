from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import AccessToken, IntrospectResult

_PATH_TOKENS = "/v1/gate/tokens"
_PATH_INTROSPECT = "/v1/gate/tokens/introspect"


class TokensResource:
    """Synchronous Gate token operations."""

    def __init__(self, http: SyncHttpClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    def create(
        self,
        *,
        subject: str,
        scopes: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AccessToken:
        """Create an access token. API key is sent in the body; no Authorization header."""
        body: Dict[str, Any] = {
            "api_key": self._api_key,
            "subject": subject,
        }
        if scopes is not None:
            body["scopes"] = scopes
        if ttl_seconds is not None:
            body["ttl_seconds"] = ttl_seconds
        data = self._http.post(_PATH_TOKENS, body=body, skip_auth=True)
        return AccessToken.from_dict(data)

    def introspect(self, access_token: str) -> IntrospectResult:
        """Introspect an access token."""
        body: Dict[str, Any] = {"access_token": access_token}
        data = self._http.post(_PATH_INTROSPECT, body=body)
        return IntrospectResult.from_dict(data)


class AsyncTokensResource:
    """Asynchronous Gate token operations."""

    def __init__(self, http: AsyncHttpClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def create(
        self,
        *,
        subject: str,
        scopes: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AccessToken:
        """Create an access token. API key is sent in the body; no Authorization header."""
        body: Dict[str, Any] = {
            "api_key": self._api_key,
            "subject": subject,
        }
        if scopes is not None:
            body["scopes"] = scopes
        if ttl_seconds is not None:
            body["ttl_seconds"] = ttl_seconds
        data = await self._http.post(_PATH_TOKENS, body=body, skip_auth=True)
        return AccessToken.from_dict(data)

    async def introspect(self, access_token: str) -> IntrospectResult:
        """Introspect an access token."""
        body: Dict[str, Any] = {"access_token": access_token}
        data = await self._http.post(_PATH_INTROSPECT, body=body)
        return IntrospectResult.from_dict(data)
