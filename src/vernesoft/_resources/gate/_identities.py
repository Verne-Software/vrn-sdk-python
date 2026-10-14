from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient, seg
from ..._core.types import Paginated
from ._types import Identity, IdentityTraitsInput, OrgClaim

_PATH_IDENTITIES = "/v1/gate/identities"


def _identity_path(identity_id: str) -> str:
    return f"{_PATH_IDENTITIES}/{seg(identity_id)}"


def _create_body(
    schema_id: str,
    traits: IdentityTraitsInput,
    credentials: Optional[Dict[str, Any]],
    state: str,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"schema_id": schema_id, "traits": dict(traits), "state": state}
    if credentials is not None:
        body["credentials"] = credentials
    return body


def _metadata(data: Any) -> Dict[str, Any]:
    metadata = data.get("metadata_public") if isinstance(data, dict) else None
    return dict(metadata) if isinstance(metadata, dict) else {}


class IdentitiesResource:
    """Synchronous Gate identities (end users) operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def create(
        self,
        *,
        traits: IdentityTraitsInput,
        schema_id: str = "user",
        credentials: Optional[Dict[str, Any]] = None,
        state: str = "active",
    ) -> Identity:
        """Create an end user bound to your tenant.

        ``traits`` are ``email`` (required) and ``locale`` — the ``user`` schema has no
        other; keep your own fields in custom metadata (:meth:`update_metadata`). A
        ``409 conflict`` means you already have an end user with this address; the same
        address at another tenant is a different person and does not conflict.
        """
        data = self._http.post(
            _PATH_IDENTITIES, body=_create_body(schema_id, traits, credentials, state)
        )
        return Identity.from_dict(data)

    def get(self, identity_id: str) -> Identity:
        """Retrieve an identity by ID."""
        return Identity.from_dict(self._http.get(_identity_path(identity_id)))

    def patch(self, identity_id: str, operations: List[Dict[str, Any]]) -> Identity:
        """Patch an identity using JSON Patch (RFC 6902) operations, e.g.
        ``[{"op": "replace", "path": "/traits/email", "value": "new@example.com"}]``."""
        data = self._http.patch(_identity_path(identity_id), body=operations)
        return Identity.from_dict(data)

    def delete(self, identity_id: str) -> None:
        """Delete an identity, its sessions and its memberships."""
        self._http.delete(_identity_path(identity_id))

    def set_state(self, identity_id: str, state: str) -> Identity:
        """Activate or deactivate an identity.

        An ``inactive`` identity cannot sign in, its sessions stop working (until it is
        active again), its access tokens introspect as ``active=False`` and no signed
        token is issued for it. Nothing is deleted. Fires ``identity.state_changed``.
        """
        data = self._http.patch(f"{_identity_path(identity_id)}/state", body={"state": state})
        return Identity.from_dict(data)

    def activate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "active")``."""
        return self.set_state(identity_id, "active")

    def deactivate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "inactive")``."""
        return self.set_state(identity_id, "inactive")

    def resend_verification(self, identity_id: str) -> None:
        """Send the end user a fresh email verification link."""
        self._http.post(f"{_identity_path(identity_id)}/resend-verification")

    def get_metadata(self, identity_id: str) -> Dict[str, Any]:
        """Read an end user's custom metadata — the place for your own fields about a
        user. ``{}`` when nothing is set. An identity that is not yours is
        ``403 forbidden``."""
        return _metadata(self._http.get(f"{_identity_path(identity_id)}/metadata"))

    def update_metadata(self, identity_id: str, patch: Mapping[str, Any]) -> Dict[str, Any]:
        """Merge ``patch`` into an end user's custom metadata and return the result.

        Keys you leave out are kept; a key set to ``None`` is removed.
        """
        data = self._http.patch(f"{_identity_path(identity_id)}/metadata", body=dict(patch))
        return _metadata(data)

    def list_organizations(
        self,
        identity_id: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Paginated[OrgClaim]:
        """The organizations of the key's project an end user belongs to, with the role
        held in each and its permissions — live, oldest membership first, cursor-paged.
        The complete list that ``orgs_truncated=True`` points to. Another tenant's user
        is ``403 forbidden``."""
        data = self._http.get(
            f"{_identity_path(identity_id)}/organizations",
            params={"limit": limit, "cursor": cursor},
        )
        return Paginated.from_dict(data, OrgClaim.from_dict)


class AsyncIdentitiesResource:
    """Asynchronous Gate identities (end users) operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def create(
        self,
        *,
        traits: IdentityTraitsInput,
        schema_id: str = "user",
        credentials: Optional[Dict[str, Any]] = None,
        state: str = "active",
    ) -> Identity:
        """Create an end user bound to your tenant. See
        :meth:`IdentitiesResource.create`."""
        data = await self._http.post(
            _PATH_IDENTITIES, body=_create_body(schema_id, traits, credentials, state)
        )
        return Identity.from_dict(data)

    async def get(self, identity_id: str) -> Identity:
        """Retrieve an identity by ID."""
        return Identity.from_dict(await self._http.get(_identity_path(identity_id)))

    async def patch(self, identity_id: str, operations: List[Dict[str, Any]]) -> Identity:
        """Patch an identity using JSON Patch (RFC 6902) operations."""
        data = await self._http.patch(_identity_path(identity_id), body=operations)
        return Identity.from_dict(data)

    async def delete(self, identity_id: str) -> None:
        """Delete an identity, its sessions and its memberships."""
        await self._http.delete(_identity_path(identity_id))

    async def set_state(self, identity_id: str, state: str) -> Identity:
        """Activate or deactivate an identity. See :meth:`IdentitiesResource.set_state`."""
        data = await self._http.patch(f"{_identity_path(identity_id)}/state", body={"state": state})
        return Identity.from_dict(data)

    async def activate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "active")``."""
        return await self.set_state(identity_id, "active")

    async def deactivate(self, identity_id: str) -> Identity:
        """Convenience wrapper for ``set_state(identity_id, "inactive")``."""
        return await self.set_state(identity_id, "inactive")

    async def resend_verification(self, identity_id: str) -> None:
        """Send the end user a fresh email verification link."""
        await self._http.post(f"{_identity_path(identity_id)}/resend-verification")

    async def get_metadata(self, identity_id: str) -> Dict[str, Any]:
        """Read an end user's custom metadata. ``{}`` when nothing is set."""
        return _metadata(await self._http.get(f"{_identity_path(identity_id)}/metadata"))

    async def update_metadata(self, identity_id: str, patch: Mapping[str, Any]) -> Dict[str, Any]:
        """Merge ``patch`` into an end user's custom metadata; a key set to ``None`` is
        removed."""
        data = await self._http.patch(f"{_identity_path(identity_id)}/metadata", body=dict(patch))
        return _metadata(data)

    async def list_organizations(
        self,
        identity_id: str,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Paginated[OrgClaim]:
        """The organizations an end user belongs to. See
        :meth:`IdentitiesResource.list_organizations`."""
        data = await self._http.get(
            f"{_identity_path(identity_id)}/organizations",
            params={"limit": limit, "cursor": cursor},
        )
        return Paginated.from_dict(data, OrgClaim.from_dict)
