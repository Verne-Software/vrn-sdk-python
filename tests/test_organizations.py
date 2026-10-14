"""Tests for Gate organizations, roles, members and the organization permission check."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
import pytest
from pytest_httpx import HTTPXMock

from vernesoft import (
    NOT_GIVEN,
    REASON_MEMBER_WITH_PERMISSION,
    REASON_NOT_A_MEMBER,
    AsyncGate,
    Gate,
    Member,
    Organization,
    OrgClaim,
    Paginated,
    Role,
    VerneAPIError,
)

_API_KEY = "vrn_3b1e5d7a9c0f2e4d"
_BASE_URL = "https://api.vernesoft.com"
_ORGS = f"{_BASE_URL}/v1/gate/organizations"
_ORG_ID = "0b6f8f9e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"
_ROLE_ID = "7a1e2b3c-4d5e-4f60-8a71-b2c3d4e5f607"
_IDENTITY_ID = "c0ffee00-1111-4222-8333-444455556666"

_ORG = {
    "id": _ORG_ID,
    "name": "Acme",
    "created_at": "2026-10-14T09:00:00Z",
    "updated_at": "2026-10-14T09:00:00Z",
}
_ROLE = {
    "id": _ROLE_ID,
    "organization_id": _ORG_ID,
    "name": "admin",
    "permissions": ["invoices:read", "invoices:write"],
    "created_at": "2026-10-14T09:00:00Z",
    "updated_at": "2026-10-14T09:00:00Z",
}
_MEMBER = {
    "organization_id": _ORG_ID,
    "identity_id": _IDENTITY_ID,
    "role_id": _ROLE_ID,
    "expires_at": None,
    "created_at": "2026-10-14T09:00:00Z",
    "updated_at": "2026-10-14T09:00:00Z",
}


@pytest.fixture()
def gate() -> Gate:
    return Gate(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_gate() -> AsyncGate:
    return AsyncGate(api_key=_API_KEY, base_url=_BASE_URL)


def _body(request: httpx.Request | None) -> Dict[str, Any]:
    assert request is not None
    loaded: Dict[str, Any] = json.loads(request.content)
    return loaded


def _page(item: Dict[str, Any], has_more: bool = False) -> Dict[str, Any]:
    return {"data": [item], "has_more": has_more, "next_cursor": "cur_2" if has_more else None}


# ===========================================================================
# Organizations
# ===========================================================================


def test_create(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="POST", url=_ORGS, status_code=201, json=_ORG)
    org = gate.organizations.create(name="Acme")
    assert org == Organization(
        id=_ORG_ID,
        name="Acme",
        created_at="2026-10-14T09:00:00Z",
        updated_at="2026-10-14T09:00:00Z",
    )
    request = httpx_mock.get_request()
    assert _body(request) == {"name": "Acme"}
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


def test_list_pages_and_drops_unset_params(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="GET", url=_ORGS, json=_page(_ORG, has_more=True))
    httpx_mock.add_response(method="GET", url=f"{_ORGS}?limit=1&cursor=cur_2", json=_page(_ORG))
    first = gate.organizations.list()
    assert isinstance(first, Paginated)
    assert first.has_more is True and first.next_cursor == "cur_2"
    assert isinstance(first.data[0], Organization)
    last = gate.organizations.list(limit=1, cursor="cur_2")
    assert last.has_more is False and last.next_cursor is None


def test_get_update_delete(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="GET", url=f"{_ORGS}/{_ORG_ID}", json=_ORG)
    httpx_mock.add_response(
        method="PATCH", url=f"{_ORGS}/{_ORG_ID}", json={**_ORG, "name": "Acme Corp"}
    )
    httpx_mock.add_response(method="DELETE", url=f"{_ORGS}/{_ORG_ID}", status_code=204)
    assert gate.organizations.get(_ORG_ID).name == "Acme"
    assert gate.organizations.update(_ORG_ID, name="Acme Corp").name == "Acme Corp"
    assert _body(httpx_mock.get_requests()[1]) == {"name": "Acme Corp"}
    assert gate.organizations.delete(_ORG_ID) is None


def test_org_id_is_url_encoded(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="GET", url=f"{_ORGS}/a%2Fb/roles/r%3F", json=_ROLE)
    gate.organizations.roles.get("a/b", "r?")


# ===========================================================================
# Roles
# ===========================================================================


def test_role_create_and_parse(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/roles", json=_ROLE)
    role = gate.organizations.roles.create(
        _ORG_ID, name="admin", permissions=["invoices:write", "invoices:read"]
    )
    assert isinstance(role, Role)
    assert role.permissions == ["invoices:read", "invoices:write"]
    assert role.organization_id == _ORG_ID
    assert _body(httpx_mock.get_request()) == {
        "name": "admin",
        "permissions": ["invoices:write", "invoices:read"],
    }


def test_role_create_without_permissions(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/roles", json=_ROLE)
    gate.organizations.roles.create(_ORG_ID, name="viewer")
    assert _body(httpx_mock.get_request()) == {"name": "viewer"}


def test_role_list_get_update_delete(httpx_mock: HTTPXMock, gate: Gate) -> None:
    role_url = f"{_ORGS}/{_ORG_ID}/roles/{_ROLE_ID}"
    httpx_mock.add_response(method="GET", url=f"{_ORGS}/{_ORG_ID}/roles?limit=1", json=_page(_ROLE))
    httpx_mock.add_response(method="GET", url=role_url, json=_ROLE)
    httpx_mock.add_response(method="PATCH", url=role_url, json=_ROLE)
    httpx_mock.add_response(method="DELETE", url=role_url, status_code=204)
    roles = gate.organizations.roles
    assert roles.list(_ORG_ID, limit=1).data[0].name == "admin"
    assert roles.get(_ORG_ID, _ROLE_ID).id == _ROLE_ID
    roles.update(_ORG_ID, _ROLE_ID, permissions=["invoices:read"])
    assert _body(httpx_mock.get_requests()[2]) == {"permissions": ["invoices:read"]}
    roles.delete(_ORG_ID, _ROLE_ID)


def test_role_delete_held_is_conflict(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_ORGS}/{_ORG_ID}/roles/{_ROLE_ID}",
        status_code=409,
        json={
            "error": {
                "code": "conflict",
                "message": "The role is held by 1 member.",
                "request_id": "req_1",
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        gate.organizations.roles.delete(_ORG_ID, _ROLE_ID)
    assert exc_info.value.status == 409
    assert exc_info.value.code == "conflict"


# ===========================================================================
# Members
# ===========================================================================


def test_member_add_without_deadline(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/members", json=_MEMBER)
    member = gate.organizations.members.add(_ORG_ID, identity_id=_IDENTITY_ID, role_id=_ROLE_ID)
    assert isinstance(member, Member)
    assert member.expires_at is None
    assert _body(httpx_mock.get_request()) == {"identity_id": _IDENTITY_ID, "role_id": _ROLE_ID}


def test_member_add_with_datetime_deadline(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/members", json=_MEMBER)
    gate.organizations.members.add(
        _ORG_ID,
        identity_id=_IDENTITY_ID,
        role_id=_ROLE_ID,
        expires_at=datetime(2026, 12, 31, 23, 0, tzinfo=timezone.utc),
    )
    assert _body(httpx_mock.get_request())["expires_at"] == "2026-12-31T23:00:00Z"


def test_member_update_absent_vs_null_vs_time(httpx_mock: HTTPXMock, gate: Gate) -> None:
    url = f"{_ORGS}/{_ORG_ID}/members/{_IDENTITY_ID}"
    for _ in range(4):
        httpx_mock.add_response(method="PATCH", url=url, json=_MEMBER)
    members = gate.organizations.members

    members.update(_ORG_ID, _IDENTITY_ID, role_id=_ROLE_ID)  # absent: keep the deadline
    members.update(_ORG_ID, _IDENTITY_ID, expires_at=None)  # null: remove it
    members.update(_ORG_ID, _IDENTITY_ID, expires_at="2027-01-01T00:00:00Z")  # set it
    members.update(_ORG_ID, _IDENTITY_ID, role_id=_ROLE_ID, expires_at=NOT_GIVEN)

    bodies = [_body(r) for r in httpx_mock.get_requests()]
    assert bodies[0] == {"role_id": _ROLE_ID}
    assert bodies[1] == {"expires_at": None}
    assert bodies[2] == {"expires_at": "2027-01-01T00:00:00Z"}
    assert bodies[3] == {"role_id": _ROLE_ID}


def test_member_list_and_remove(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="GET", url=f"{_ORGS}/{_ORG_ID}/members", json=_page(_MEMBER))
    httpx_mock.add_response(
        method="DELETE", url=f"{_ORGS}/{_ORG_ID}/members/{_IDENTITY_ID}", status_code=204
    )
    assert gate.organizations.members.list(_ORG_ID).data[0].identity_id == _IDENTITY_ID
    gate.organizations.members.remove(_ORG_ID, _IDENTITY_ID)


# ===========================================================================
# Authorize / can
# ===========================================================================


def test_authorize_builds_the_organization_resource(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        json={
            "allowed": True,
            "decision_id": "dec_1",
            "reason": "member_with_permission",
            "role": "admin",
        },
    )
    decision = gate.organizations.authorize(_ORG_ID, _IDENTITY_ID, "invoices:write")
    assert decision.allowed is True
    assert decision.reason == REASON_MEMBER_WITH_PERMISSION
    assert decision.role == "admin"
    assert _body(httpx_mock.get_request()) == {
        "subject": _IDENTITY_ID,
        "action": "invoices:write",
        "resource": f"organization:{_ORG_ID}",
    }


def test_can_returns_the_boolean(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        json={"allowed": False, "decision_id": "dec_2", "reason": "not_a_member"},
    )
    assert gate.organizations.can(_ORG_ID, _IDENTITY_ID, "invoices:read") is False
    assert _body(httpx_mock.get_request())["resource"] == f"organization:{_ORG_ID}"


def test_can_raises_instead_of_false(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        status_code=400,
        json={
            "error": {
                "code": "invalid_payload",
                "message": "Invalid permission.",
                "request_id": "r",
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        gate.organizations.can(_ORG_ID, _IDENTITY_ID, "Invoices:*")
    assert exc_info.value.code == "invalid_payload"


# ===========================================================================
# A user's organizations
# ===========================================================================


def test_identity_list_organizations(httpx_mock: HTTPXMock, gate: Gate) -> None:
    claim = {"id": _ORG_ID, "role": "admin", "permissions": ["invoices:read"]}
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/identities/{_IDENTITY_ID}/organizations?limit=50",
        json=_page(claim),
    )
    page = gate.identities.list_organizations(_IDENTITY_ID, limit=50)
    assert page.data == [OrgClaim(id=_ORG_ID, role="admin", permissions=["invoices:read"])]


# ===========================================================================
# Async
# ===========================================================================


async def test_async_organizations_roundtrip(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(method="POST", url=_ORGS, json=_ORG)
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/roles", json=_ROLE)
    httpx_mock.add_response(method="POST", url=f"{_ORGS}/{_ORG_ID}/members", json=_MEMBER)
    httpx_mock.add_response(
        method="PATCH", url=f"{_ORGS}/{_ORG_ID}/members/{_IDENTITY_ID}", json=_MEMBER
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        json={"allowed": False, "decision_id": "d", "reason": "not_a_member"},
    )
    orgs = async_gate.organizations
    org = await orgs.create(name="Acme")
    role = await orgs.roles.create(org.id, name="admin")
    await orgs.members.add(org.id, identity_id=_IDENTITY_ID, role_id=role.id)
    await orgs.members.update(org.id, _IDENTITY_ID, expires_at=None)
    decision = await orgs.authorize(org.id, _IDENTITY_ID, "invoices:read")
    assert decision.reason == REASON_NOT_A_MEMBER and decision.role is None
    assert _body(httpx_mock.get_requests()[3]) == {"expires_at": None}


async def test_async_can(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        json={"allowed": True, "decision_id": "d", "reason": "member_with_permission"},
    )
    assert await async_gate.organizations.can(_ORG_ID, _IDENTITY_ID, "invoices:read") is True
