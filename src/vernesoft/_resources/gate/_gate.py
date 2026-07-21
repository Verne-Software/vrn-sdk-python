from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._identities import AsyncIdentitiesResource, IdentitiesResource
from ._settings import AsyncSettingsResource, SettingsResource
from ._tokens import AsyncTokensResource, TokensResource
from ._types import AuthorizeResult

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0
_PATH_AUTHORIZE = "/v1/gate/authorize"
_PATH_LOGIN_FLOW = "/v1/gate/auth/login"


def _providers_path(tenant_id: str) -> str:
    return f"/public/gate/providers/{tenant_id}"


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
        self._settings: SettingsResource | None = None

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

    @property
    def settings(self) -> SettingsResource:
        if self._settings is None:
            self._settings = SettingsResource(self._http)
        return self._settings

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

    def get_enabled_providers(self, tenant_id: str) -> List[str]:
        """Return the social login providers currently enabled for a tenant.

        This is a public, unauthenticated endpoint — call it from your login /
        registration page to decide which social buttons to render.
        """
        data = self._http.get(_providers_path(tenant_id))
        return data.get("providers", [])

    def create_login_flow(self) -> Dict[str, Any]:
        """Initialize a Kratos login flow using your Gate API key.

        Call this from your server and pass the returned flow to your
        browser-side code to render social login buttons. The flow already
        contains only the providers your tenant has enabled.
        """
        return self._http.get(_PATH_LOGIN_FLOW)


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
        self._settings: AsyncSettingsResource | None = None

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

    @property
    def settings(self) -> AsyncSettingsResource:
        if self._settings is None:
            self._settings = AsyncSettingsResource(self._http)
        return self._settings

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

    async def get_enabled_providers(self, tenant_id: str) -> List[str]:
        """Return the social login providers currently enabled for a tenant.

        This is a public, unauthenticated endpoint — call it from your login /
        registration page to decide which social buttons to render.
        """
        data = await self._http.get(_providers_path(tenant_id))
        return data.get("providers", [])

    async def create_login_flow(self) -> Dict[str, Any]:
        """Initialize a Kratos login flow using your Gate API key.

        Call this from your server and pass the returned flow to your
        browser-side code to render social login buttons. The flow already
        contains only the providers your tenant has enabled.
        """
        return await self._http.get(_PATH_LOGIN_FLOW)
