from __future__ import annotations

from typing import Any, Dict, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._identities import AsyncIdentitiesResource, IdentitiesResource
from ._tokens import AsyncTokensResource, TokensResource
from ._types import AuthorizeResult

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0
_PATH_AUTHORIZE = "/v1/gate/authorize"


class Gate:
    """Synchronous client for the Verne Gate service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = SyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._identities: IdentitiesResource | None = None
        self._tokens: TokensResource | None = None

    @property
    def identities(self) -> IdentitiesResource:
        if self._identities is None:
            self._identities = IdentitiesResource(self._http)
        return self._identities

    @property
    def tokens(self) -> TokensResource:
        if self._tokens is None:
            self._tokens = TokensResource(self._http, self._api_key)
        return self._tokens

    def authorize(
        self,
        *,
        subject: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizeResult:
        """Check whether a subject is allowed to perform an action on a resource."""
        body: Dict[str, Any] = {
            "subject": subject,
            "action": action,
            "resource": resource,
        }
        if context is not None:
            body["context"] = context
        data = self._http.post(_PATH_AUTHORIZE, body=body)
        return AuthorizeResult.from_dict(data)


class AsyncGate:
    """Asynchronous client for the Verne Gate service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = AsyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._identities: AsyncIdentitiesResource | None = None
        self._tokens: AsyncTokensResource | None = None

    @property
    def identities(self) -> AsyncIdentitiesResource:
        if self._identities is None:
            self._identities = AsyncIdentitiesResource(self._http)
        return self._identities

    @property
    def tokens(self) -> AsyncTokensResource:
        if self._tokens is None:
            self._tokens = AsyncTokensResource(self._http, self._api_key)
        return self._tokens

    async def authorize(
        self,
        *,
        subject: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizeResult:
        """Check whether a subject is allowed to perform an action on a resource."""
        body: Dict[str, Any] = {
            "subject": subject,
            "action": action,
            "resource": resource,
        }
        if context is not None:
            body["context"] = context
        data = await self._http.post(_PATH_AUTHORIZE, body=body)
        return AuthorizeResult.from_dict(data)
