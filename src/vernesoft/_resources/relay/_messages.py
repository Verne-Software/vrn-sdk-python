from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import ListMessagesResponse, Message

_PATH_MESSAGES = "/v1/relay/messages"


class MessagesResource:
    """Synchronous relay messages operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def send(
        self,
        *,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> Message:
        """Send an event via the relay service."""
        body: Dict[str, Any] = {"event_type": event_type, "payload": payload}
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if channels is not None:
            body["channels"] = channels
        data = self._http.post(_PATH_MESSAGES, body=body)
        return Message.from_dict(data)

    def list(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> ListMessagesResponse:
        """List relay messages with optional filters and cursor pagination."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if event_type is not None:
            params["event_type"] = event_type
        data = self._http.get(_PATH_MESSAGES, params=params)
        return ListMessagesResponse.from_dict(data)


class AsyncMessagesResource:
    """Asynchronous relay messages operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def send(
        self,
        *,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        channels: Optional[List[str]] = None,
    ) -> Message:
        """Send an event via the relay service."""
        body: Dict[str, Any] = {"event_type": event_type, "payload": payload}
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if channels is not None:
            body["channels"] = channels
        data = await self._http.post(_PATH_MESSAGES, body=body)
        return Message.from_dict(data)

    async def list(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> ListMessagesResponse:
        """List relay messages with optional filters and cursor pagination."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if event_type is not None:
            params["event_type"] = event_type
        data = await self._http.get(_PATH_MESSAGES, params=params)
        return ListMessagesResponse.from_dict(data)
