"""Integration suite for 1.6.0: what the organization routes say since Nautilus v1.10.44 —
``member_count`` on organizations and roles, ``email`` and ``display_name`` on members,
``total`` on the three lists, the ``reason`` of their 404s and 409s, and the audit entries
for creating and renaming an organization. Opt-in (``pytest -m integration``), same
environment as ``test_live.py``; it deletes everything it creates.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Callable, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import pytest

from vernesoft import AsyncVerne, Gate, Verne, VerneAPIError

KEY = os.environ.get("VERNE_API_KEY")
BASE_URL = os.environ.get("VERNE_BASE_URL", "http://api.soft.com").rstrip("/")
PREFIX = os.environ.get("VERNE_EMAIL_PREFIX", f"e2e-sdkpy-{int(time.time()):x}")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not KEY, reason="VERNE_API_KEY is not set"),
]

if KEY and urlparse(BASE_URL).hostname not in ("api.soft.com", "localhost", "127.0.0.1"):
    if os.environ.get("VERNE_ALLOW_REMOTE") != "1":
        raise RuntimeError(
            f"Refusing to run the integration suite against {BASE_URL}; "
            "set VERNE_ALLOW_REMOTE=1 to insist."
        )


def email(name: str) -> str:
    return f"{PREFIX}-{name}@e2e.soft.com"


def refusal(call: Callable[[], object]) -> Tuple[int, str, Optional[str]]:
    with pytest.raises(VerneAPIError) as exc_info:
        call()
    err = exc_info.value
    return err.status, err.code, err.reason


@pytest.fixture(scope="module")
def gate() -> Iterator[Gate]:
    yield Verne(api_key=KEY, base_url=BASE_URL).gate


def test_organization_fields(gate: Gate) -> None:
    cleanup: List[Callable[[], object]] = []
    try:
        alice = gate.identities.create(schema_id="user", traits={"email": email("org-alice")})
        cleanup.append(lambda: gate.identities.delete(alice.id))
        bob = gate.identities.create(schema_id="user", traits={"email": email("org-bob")})
        cleanup.append(lambda: gate.identities.delete(bob.id))
        orgs = gate.organizations

        # A new organization and its roles count nobody; the lists carry total.
        before = orgs.list(limit=1).total
        assert before is not None
        name = f"{PREFIX} Acme"
        org = orgs.create(name=name)
        cleanup.append(lambda: orgs.delete(org.id))
        assert org.member_count == 0
        after = orgs.list(limit=1)
        assert after.total == before + 1
        assert len(after.data) == 1

        admin = orgs.roles.create(org.id, name="admin", permissions=["invoices:write"])
        viewer = orgs.roles.create(org.id, name="viewer")
        assert admin.member_count == 0
        roles = orgs.roles.list(org.id, limit=1)
        assert len(roles.data) == 1
        assert roles.total == 2

        # A member answer carries the person's email and display_name.
        added = orgs.members.add(org.id, identity_id=alice.id, role_id=admin.id)
        assert added.email == email("org-alice")
        # The `user` schema has no name trait: an API-created user has none.
        assert added.display_name is None
        moved = orgs.members.update(org.id, alice.id, role_id=viewer.id)
        assert moved.email == email("org-alice")
        orgs.members.update(org.id, alice.id, role_id=admin.id)
        members = orgs.members.list(org.id)
        assert members.total == 1
        assert [(m.identity_id, m.email) for m in members.data] == [(alice.id, email("org-alice"))]

        # member_count follows the memberships.
        assert orgs.get(org.id).member_count == 1
        assert orgs.roles.get(org.id, admin.id).member_count == 1
        assert orgs.roles.get(org.id, viewer.id).member_count == 0
        listed = [o for o in orgs.list(limit=100).data if o.id == org.id]
        assert listed[0].member_count == 1

        # Every 409 says why.
        assert refusal(lambda: orgs.roles.create(org.id, name="admin")) == (
            409,
            "conflict",
            "role_name_taken",
        )
        assert refusal(
            lambda: orgs.members.add(org.id, identity_id=alice.id, role_id=viewer.id)
        ) == (409, "conflict", "already_member")
        assert refusal(lambda: orgs.roles.delete(org.id, admin.id)) == (
            409,
            "conflict",
            "role_held",
        )

        # Every 404 says what.
        assert refusal(lambda: orgs.get(str(uuid.uuid4()))) == (404, "not_found", "organization")
        assert refusal(lambda: orgs.roles.get(org.id, str(uuid.uuid4()))) == (
            404,
            "not_found",
            "role",
        )
        assert refusal(lambda: orgs.members.update(org.id, bob.id, role_id=viewer.id)) == (
            404,
            "not_found",
            "member",
        )
        assert refusal(
            lambda: orgs.members.add(org.id, identity_id=str(uuid.uuid4()), role_id=viewer.id)
        ) == (404, "not_found", "end_user")

        # The audit log records creating and renaming the organization.
        renamed = orgs.update(org.id, name=f"{name} Corp")
        assert renamed.member_count == 1
        created = gate.audit_log.list(action="organization.created", target_id=org.id)
        assert len(created.data) == 1
        assert created.data[0].details["name"] == name
        updated = gate.audit_log.list(action="organization.updated", target_id=org.id)
        assert len(updated.data) == 1
        assert updated.data[0].details["previous_name"] == name
        assert updated.data[0].details["name"] == f"{name} Corp"
    finally:
        for step in reversed(cleanup):
            try:
                step()
            except VerneAPIError:
                pass


async def test_async_lists_carry_total_and_reasons() -> None:
    gate = AsyncVerne(api_key=KEY, base_url=BASE_URL).gate
    org = await gate.organizations.create(name=f"{PREFIX} Async")
    try:
        role = await gate.organizations.roles.create(org.id, name="admin")
        page = await gate.organizations.roles.list(org.id)
        assert page.total == 1
        assert page.data[0].member_count == 0
        members = await gate.organizations.members.list(org.id)
        assert members.total == 0
        with pytest.raises(VerneAPIError) as exc_info:
            await gate.organizations.roles.create(org.id, name=role.name)
        assert exc_info.value.reason == "role_name_taken"
    finally:
        await gate.organizations.delete(org.id)
