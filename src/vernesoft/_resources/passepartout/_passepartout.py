from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlencode

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import LoginStart, LoginStatus, TokenIntrospection

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0
_PATH_LOGIN_START = "/v1/passepartout/login/start"
_PATH_LOGIN_STATUS = "/v1/passepartout/login/status"
_PATH_INTROSPECT = "/v1/passepartout/tokens/introspect"


def _login_status_path(nonce: str) -> str:
    return f"{_PATH_LOGIN_STATUS}?{urlencode({'nonce': nonce})}"


class Passepartout:
    """Synchronous client for the Verne Passepartout service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = SyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)

    def login_start(self) -> LoginStart:
        """Start a Telegram login flow and return the nonce and deep link."""
        data = self._http.post(_PATH_LOGIN_START)
        return LoginStart.from_dict(data)

    def login_status(self, nonce: str) -> LoginStatus:
        """Poll the status of a Telegram login flow by its nonce."""
        data = self._http.get(_login_status_path(nonce))
        return LoginStatus.from_dict(data)

    def introspect(self, access_token: str) -> TokenIntrospection:
        """Introspect a Passepartout access token."""
        body: Dict[str, Any] = {"access_token": access_token}
        data = self._http.post(_PATH_INTROSPECT, body=body)
        return TokenIntrospection.from_dict(data)


class AsyncPassepartout:
    """Asynchronous client for the Verne Passepartout service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = AsyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)

    async def login_start(self) -> LoginStart:
        """Start a Telegram login flow and return the nonce and deep link."""
        data = await self._http.post(_PATH_LOGIN_START)
        return LoginStart.from_dict(data)

    async def login_status(self, nonce: str) -> LoginStatus:
        """Poll the status of a Telegram login flow by its nonce."""
        data = await self._http.get(_login_status_path(nonce))
        return LoginStatus.from_dict(data)

    async def introspect(self, access_token: str) -> TokenIntrospection:
        """Introspect a Passepartout access token."""
        body: Dict[str, Any] = {"access_token": access_token}
        data = await self._http.post(_PATH_INTROSPECT, body=body)
        return TokenIntrospection.from_dict(data)
