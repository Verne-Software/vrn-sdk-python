from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..._core.http import AsyncHttpClient, SyncHttpClient, rfc3339, seg
from ..._core.types import NOT_GIVEN, NotGiven, Paginated
from ._types import AuthorizeResult, Member, Organization, Role

_PATH_ORGANIZATIONS = "/v1/gate/organizations"
_PATH_AUTHORIZE = "/v1/gate/authorize"

#: ``expires_at`` of a membership: a time (``str`` RFC 3339 or ``datetime``), ``None``
#: for no deadline, or :data:`NOT_GIVEN` to leave it as it is.
ExpiresAt = Union[str, datetime, None, NotGiven]


def _org_path(org_id: str) -> str:
    return f"{_PATH_ORGANIZATIONS}/{seg(org_id)}"


def _page(limit: Optional[int], cursor: Optional[str]) -> Dict[str, Any]:
    return {"limit": limit, "cursor": cursor}


def _authorize_body(org_id: str, identity_id: str, permission: str) -> Dict[str, Any]:
    return {
        "subject": identity_id,
        "action": permission,
        "resource": f"organization:{org_id}",
    }


def _role_body(name: Optional[str], permissions: Optional[List[str]]) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if permissions is not None:
        body["permissions"] = list(permissions)
    return body


def _put_expires_at(body: Dict[str, Any], expires_at: ExpiresAt) -> None:
    if isinstance(expires_at, NotGiven):
        return
    body["expires_at"] = None if expires_at is None else rfc3339(expires_at)


def _member_add_body(identity_id: str, role_id: str, expires_at: ExpiresAt) -> Dict[str, Any]:
    body: Dict[str, Any] = {"identity_id": identity_id, "role_id": role_id}
    _put_expires_at(body, expires_at)
    return body


def _member_update_body(role_id: Optional[str], expires_at: ExpiresAt) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if role_id is not None:
        body["role_id"] = role_id
    _put_expires_at(body, expires_at)
    return body


# ===========================================================================
# Synchronous
# ===========================================================================


class RolesResource:
    """Roles of one organization: named sets of permissions."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def create(self, org_id: str, *, name: str, permissions: Optional[List[str]] = None) -> Role:
        """Define a role.

        ``name``: 1–64 characters, lowercase letters, digits, ``_`` and ``-``, starting
        with a letter or digit; unique in the organization (``409 conflict``), at most
        100 roles per organization (``409 limit_reached``). ``permissions``: lowercase
        segments joined by ``:`` (e.g. ``"invoices:write"``), at most 64 characters and
        100 per role; ``*`` and the ``nautilus:`` prefix are reserved. They come back
        de-duplicated and sorted.
        """
        body: Dict[str, Any] = {"name": name}
        if permissions is not None:
            body["permissions"] = list(permissions)
        return Role.from_dict(self._http.post(f"{_org_path(org_id)}/roles", body=body))

    def list(
        self, org_id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Role]:
        """One page of the organization's roles."""
        data = self._http.get(f"{_org_path(org_id)}/roles", params=_page(limit, cursor))
        return Paginated.from_dict(data, Role.from_dict)

    def get(self, org_id: str, role_id: str) -> Role:
        return Role.from_dict(self._http.get(f"{_org_path(org_id)}/roles/{seg(role_id)}"))

    def update(
        self,
        org_id: str,
        role_id: str,
        *,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Role:
        """Rename a role and/or **replace** its permissions. Everyone who holds it has the
        new permissions the next time they are read."""
        data = self._http.patch(
            f"{_org_path(org_id)}/roles/{seg(role_id)}", body=_role_body(name, permissions)
        )
        return Role.from_dict(data)

    def delete(self, org_id: str, role_id: str) -> None:
        """Delete a role. A role someone holds is refused with ``409 conflict``."""
        self._http.delete(f"{_org_path(org_id)}/roles/{seg(role_id)}")


class MembersResource:
    """Members of one organization: end users holding one role each."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def add(
        self,
        org_id: str,
        *,
        identity_id: str,
        role_id: str,
        expires_at: ExpiresAt = NOT_GIVEN,
    ) -> Member:
        """Give an end user a role in the organization.

        ``expires_at`` (a future time, at most 10 years ahead) ends the membership
        automatically. ``404`` if the identity is not one of your end users, ``409`` if
        they already are a member (change the role with :meth:`update`).
        """
        data = self._http.post(
            f"{_org_path(org_id)}/members",
            body=_member_add_body(identity_id, role_id, expires_at),
        )
        return Member.from_dict(data)

    def list(
        self, org_id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Member]:
        """One page of the organization's members."""
        data = self._http.get(f"{_org_path(org_id)}/members", params=_page(limit, cursor))
        return Paginated.from_dict(data, Member.from_dict)

    def update(
        self,
        org_id: str,
        identity_id: str,
        *,
        role_id: Optional[str] = None,
        expires_at: ExpiresAt = NOT_GIVEN,
    ) -> Member:
        """Change a member's role and/or deadline.

        ``expires_at``: leave it out to keep the deadline, ``None`` to remove it, a time
        to set it. Passing neither ``role_id`` nor ``expires_at`` is a ``400``.
        """
        data = self._http.patch(
            f"{_org_path(org_id)}/members/{seg(identity_id)}",
            body=_member_update_body(role_id, expires_at),
        )
        return Member.from_dict(data)

    def remove(self, org_id: str, identity_id: str) -> None:
        """Remove the membership. The person stays your end user."""
        self._http.delete(f"{_org_path(org_id)}/members/{seg(identity_id)}")


class OrganizationsResource:
    """Organizations of your end users — their teams, workspaces, companies — with named
    roles and members. Everything here acts on the project the API key belongs to.

    Gate keeps the data and reports it (introspection, the session check, the signed
    token's ``orgs`` claim); it does not enforce permissions. Ask with :meth:`can`.
    """

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http
        self.roles = RolesResource(http)
        self.members = MembersResource(http)

    def create(self, *, name: str) -> Organization:
        """Create an organization. ``name`` is free text, 1–120 characters, not unique."""
        return Organization.from_dict(self._http.post(_PATH_ORGANIZATIONS, body={"name": name}))

    def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Organization]:
        """One page of the project's organizations, oldest first."""
        data = self._http.get(_PATH_ORGANIZATIONS, params=_page(limit, cursor))
        return Paginated.from_dict(data, Organization.from_dict)

    def get(self, org_id: str) -> Organization:
        return Organization.from_dict(self._http.get(_org_path(org_id)))

    def update(self, org_id: str, *, name: str) -> Organization:
        """Rename an organization."""
        return Organization.from_dict(self._http.patch(_org_path(org_id), body={"name": name}))

    def delete(self, org_id: str) -> None:
        """Delete an organization with its roles and memberships."""
        self._http.delete(_org_path(org_id))

    def authorize(self, org_id: str, identity_id: str, permission: str) -> AuthorizeResult:
        """*May this end user do this in this organization?* — answered from the role they
        hold there and its permissions, as they are now.

        ``permission`` must match exactly (no wildcards). ``reason`` is one of
        ``member_with_permission``, ``member_without_permission``, ``not_a_member``,
        ``subject_inactive``, ``no_such_organization`` (an organization of another
        project looks like a missing one). An invalid permission (upper case, ``*``, the
        ``nautilus:`` prefix) raises ``400``, never ``allowed=False``.
        """
        data = self._http.post(
            _PATH_AUTHORIZE, body=_authorize_body(org_id, identity_id, permission)
        )
        return AuthorizeResult.from_dict(data)

    def can(self, org_id: str, identity_id: str, permission: str) -> bool:
        """``True`` when the end user holds ``permission`` in the organization — the
        boolean of :meth:`authorize`. Errors are raised, not turned into ``False``."""
        return self.authorize(org_id, identity_id, permission).allowed


# ===========================================================================
# Asynchronous
# ===========================================================================


class AsyncRolesResource:
    """Roles of one organization (async). See :class:`RolesResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def create(
        self, org_id: str, *, name: str, permissions: Optional[List[str]] = None
    ) -> Role:
        """Define a role. See :meth:`RolesResource.create`."""
        body: Dict[str, Any] = {"name": name}
        if permissions is not None:
            body["permissions"] = list(permissions)
        return Role.from_dict(await self._http.post(f"{_org_path(org_id)}/roles", body=body))

    async def list(
        self, org_id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Role]:
        data = await self._http.get(f"{_org_path(org_id)}/roles", params=_page(limit, cursor))
        return Paginated.from_dict(data, Role.from_dict)

    async def get(self, org_id: str, role_id: str) -> Role:
        return Role.from_dict(await self._http.get(f"{_org_path(org_id)}/roles/{seg(role_id)}"))

    async def update(
        self,
        org_id: str,
        role_id: str,
        *,
        name: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Role:
        """Rename a role and/or **replace** its permissions."""
        data = await self._http.patch(
            f"{_org_path(org_id)}/roles/{seg(role_id)}", body=_role_body(name, permissions)
        )
        return Role.from_dict(data)

    async def delete(self, org_id: str, role_id: str) -> None:
        """Delete a role. A role someone holds is refused with ``409 conflict``."""
        await self._http.delete(f"{_org_path(org_id)}/roles/{seg(role_id)}")


class AsyncMembersResource:
    """Members of one organization (async). See :class:`MembersResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def add(
        self,
        org_id: str,
        *,
        identity_id: str,
        role_id: str,
        expires_at: ExpiresAt = NOT_GIVEN,
    ) -> Member:
        """Give an end user a role in the organization. See :meth:`MembersResource.add`."""
        data = await self._http.post(
            f"{_org_path(org_id)}/members",
            body=_member_add_body(identity_id, role_id, expires_at),
        )
        return Member.from_dict(data)

    async def list(
        self, org_id: str, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Member]:
        data = await self._http.get(f"{_org_path(org_id)}/members", params=_page(limit, cursor))
        return Paginated.from_dict(data, Member.from_dict)

    async def update(
        self,
        org_id: str,
        identity_id: str,
        *,
        role_id: Optional[str] = None,
        expires_at: ExpiresAt = NOT_GIVEN,
    ) -> Member:
        """Change a member's role and/or deadline: ``expires_at`` left out keeps it,
        ``None`` removes it, a time sets it."""
        data = await self._http.patch(
            f"{_org_path(org_id)}/members/{seg(identity_id)}",
            body=_member_update_body(role_id, expires_at),
        )
        return Member.from_dict(data)

    async def remove(self, org_id: str, identity_id: str) -> None:
        """Remove the membership. The person stays your end user."""
        await self._http.delete(f"{_org_path(org_id)}/members/{seg(identity_id)}")


class AsyncOrganizationsResource:
    """Organizations of your end users (async). See :class:`OrganizationsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http
        self.roles = AsyncRolesResource(http)
        self.members = AsyncMembersResource(http)

    async def create(self, *, name: str) -> Organization:
        """Create an organization. ``name`` is free text, 1–120 characters, not unique."""
        return Organization.from_dict(
            await self._http.post(_PATH_ORGANIZATIONS, body={"name": name})
        )

    async def list(
        self, *, limit: Optional[int] = None, cursor: Optional[str] = None
    ) -> Paginated[Organization]:
        data = await self._http.get(_PATH_ORGANIZATIONS, params=_page(limit, cursor))
        return Paginated.from_dict(data, Organization.from_dict)

    async def get(self, org_id: str) -> Organization:
        return Organization.from_dict(await self._http.get(_org_path(org_id)))

    async def update(self, org_id: str, *, name: str) -> Organization:
        """Rename an organization."""
        return Organization.from_dict(
            await self._http.patch(_org_path(org_id), body={"name": name})
        )

    async def delete(self, org_id: str) -> None:
        """Delete an organization with its roles and memberships."""
        await self._http.delete(_org_path(org_id))

    async def authorize(self, org_id: str, identity_id: str, permission: str) -> AuthorizeResult:
        """May this end user do this in this organization? See
        :meth:`OrganizationsResource.authorize`."""
        data = await self._http.post(
            _PATH_AUTHORIZE, body=_authorize_body(org_id, identity_id, permission)
        )
        return AuthorizeResult.from_dict(data)

    async def can(self, org_id: str, identity_id: str, permission: str) -> bool:
        """``True`` when the end user holds ``permission``. Errors are raised."""
        return (await self.authorize(org_id, identity_id, permission)).allowed
