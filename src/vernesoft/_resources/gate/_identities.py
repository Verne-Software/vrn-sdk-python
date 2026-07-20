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

    def set_state(self, identity_id: str, state: str) -> Identity:
        """Activate or deactivate an identity.

        An ``inactive`` identity cannot log in — Kratos rejects its credentials
        automatically — until it is reactivated. The identity is not deleted.
        Fires the ``identity.state_changed`` webhook event.

        :param state: ``"active"`` or ``"inactive"``.
        """
        data = self._http.patch(f"{_PATH_IDENTITIES}/{identity_id}/state", body={"state": state})
        return Identity.from_dict(data)

    def activate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "active")``."""
        return self.set_state(identity_id, "active")

    def deactivate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "inactive")``."""
        return self.set_state(identity_id, "inactive")

    def resend_verification(self, identity_id: str) -> None:
        """Trigger a new email verification flow for an identity.

        Useful when the original verification email expired or was never
        received. The user receives a fresh verification email.
        """
        self._http.post(f"{_PATH_IDENTITIES}/{identity_id}/resend-verification")


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

    async def set_state(self, identity_id: str, state: str) -> Identity:
        """Activate or deactivate an identity.

        An ``inactive`` identity cannot log in — Kratos rejects its credentials
        automatically — until it is reactivated. The identity is not deleted.
        Fires the ``identity.state_changed`` webhook event.

        :param state: ``"active"`` or ``"inactive"``.
        """
        data = await self._http.patch(
            f"{_PATH_IDENTITIES}/{identity_id}/state", body={"state": state}
        )
        return Identity.from_dict(data)

    async def activate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "active")``."""
        return await self.set_state(identity_id, "active")

    async def deactivate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "inactive")``."""
        return await self.set_state(identity_id, "inactive")

    async def resend_verification(self, identity_id: str) -> None:
        """Trigger a new email verification flow for an identity.

        Useful when the original verification email expired or was never
        received. The user receives a fresh verification email.
        """
        await self._http.post(f"{_PATH_IDENTITIES}/{identity_id}/resend-verification")
