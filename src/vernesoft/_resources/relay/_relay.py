from __future__ import annotations

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._messages import AsyncMessagesResource, MessagesResource

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0


class Relay:
    """Synchronous client for the Verne Relay service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._http = SyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._messages: MessagesResource | None = None

    @property
    def messages(self) -> MessagesResource:
        if self._messages is None:
            self._messages = MessagesResource(self._http)
        return self._messages


class AsyncRelay:
    """Asynchronous client for the Verne Relay service."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._http = AsyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._messages: AsyncMessagesResource | None = None

    @property
    def messages(self) -> AsyncMessagesResource:
        if self._messages is None:
            self._messages = AsyncMessagesResource(self._http)
        return self._messages
