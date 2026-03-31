from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import Identity

_PATH_IDENTITIES = "/v1/gate/identities"


class IdentitiesResource:
    """Synchronous Gate identities CRUD operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def create(
        self,
        *,
        schema_id: str,
        traits: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        state: str = "active",
    ) -> Identity:
        """Create a new identity."""
        body: Dict[str, Any] = {
            "schema_id": schema_id,
            "traits": traits,
            "state": state,
        }
        if credentials is not None:
            body["credentials"] = credentials
        data = self._http.post(_PATH_IDENTITIES, body=body)
        return Identity.from_dict(data)

    def get(self, identity_id: str) -> Identity:
        """Retrieve an identity by ID."""
        data = self._http.get(f"{_PATH_IDENTITIES}/{identity_id}")
        return Identity.from_dict(data)

    def patch(self, identity_id: str, operations: List[Dict[str, Any]]) -> Identity:
        """Patch an identity using JSON Patch (RFC 6902) operations."""
        data = self._http.patch(f"{_PATH_IDENTITIES}/{identity_id}", body=operations)
        return Identity.from_dict(data)

    def delete(self, identity_id: str) -> None:
        """Delete an identity."""
        self._http.delete(f"{_PATH_IDENTITIES}/{identity_id}")


class AsyncIdentitiesResource:
    """Asynchronous Gate identities CRUD operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def create(
        self,
        *,
        schema_id: str,
        traits: Dict[str, Any],
        credentials: Optional[Dict[str, Any]] = None,
        state: str = "active",
    ) -> Identity:
        """Create a new identity."""
        body: Dict[str, Any] = {
            "schema_id": schema_id,
            "traits": traits,
            "state": state,
        }
        if credentials is not None:
            body["credentials"] = credentials
        data = await self._http.post(_PATH_IDENTITIES, body=body)
        return Identity.from_dict(data)

    async def get(self, identity_id: str) -> Identity:
        """Retrieve an identity by ID."""
        data = await self._http.get(f"{_PATH_IDENTITIES}/{identity_id}")
        return Identity.from_dict(data)

    async def patch(self, identity_id: str, operations: List[Dict[str, Any]]) -> Identity:
        """Patch an identity using JSON Patch (RFC 6902) operations."""
        data = await self._http.patch(f"{_PATH_IDENTITIES}/{identity_id}", body=operations)
        return Identity.from_dict(data)

    async def delete(self, identity_id: str) -> None:
        """Delete an identity."""
        await self._http.delete(f"{_PATH_IDENTITIES}/{identity_id}")
