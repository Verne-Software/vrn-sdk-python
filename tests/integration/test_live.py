"""Integration suite: every 1.4.0 resource against a real Nautilus stack.

Opt-in — deselected by the default ``pytest`` run; start it with ``pytest -m integration``.

    VERNE_API_KEY=vrn_…                 key with scopes gate, clockwork, passepartout (required)
    VERNE_BASE_URL=http://api.soft.com  default; any other host needs VERNE_ALLOW_REMOTE=1
    VERNE_EMAIL_PREFIX=e2e-sdkpy-<run>  every end user created is <prefix>-<n>@e2e.soft.com
    VERNE_NARROW_KEY=vrn_…              optional: a key WITHOUT the gate scope (403 check)

``scripts/local_stack_key.py`` makes such a tenant and keys. The suite creates end users,
an organization with roles and members, changes the tenant's security settings and
return URLs for a moment, and removes all of it again. Run it against a local stack,
never production. The cases mirror vrn-sdk-node's ``tests/integration/gate.integration.ts``.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterator, List, Optional
from urllib.parse import urlparse

import httpx
import pytest

from vernesoft import (
    REASON_NOT_A_KNOWN_IDENTITY,
    REASON_OWNED_BY_TENANT,
    REASON_SUBJECT_INACTIVE,
    AsyncVerne,
    Clockwork,
    Gate,
    GateTokenVerifier,
    Identity,
    Member,
    Organization,
    Role,
    Verne,
    VerneAPIError,
    VerneTokenError,
)

KEY = os.environ.get("VERNE_API_KEY")
BASE_URL = os.environ.get("VERNE_BASE_URL", "http://api.soft.com").rstrip("/")
PREFIX = os.environ.get("VERNE_EMAIL_PREFIX", f"e2e-sdkpy-{int(time.time()):x}")
NARROW_KEY = os.environ.get("VERNE_NARROW_KEY")

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


def new_password() -> str:
    return f"Pw-{uuid.uuid4().hex[:13]}-Zq9!x"


def expect_api_error(
    call: Callable[[], Any], status: int, code: Optional[str] = None
) -> VerneAPIError:
    with pytest.raises(VerneAPIError) as exc_info:
        call()
    err = exc_info.value
    assert err.status == status, f"expected {status}, got {err.status} {err.code}: {err}"
    if code is not None:
        assert err.code == code, f"expected {code}, got {err.code}: {err}"
    return err


def password_login(gate: Gate, identifier: str, secret: str) -> str:
    """A password login through the flow's ``ui.action`` — the part an SDK leaves to the
    browser."""
    flow = gate.create_login_flow()
    res = httpx.post(
        flow["ui"]["action"],
        headers={"Accept": "application/json"},
        json={"method": "password", "identifier": identifier, "password": secret},
        timeout=30,
    )
    token = res.json().get("session_token") if res.is_success else None
    if not token:
        raise AssertionError(f"login failed: HTTP {res.status_code}")
    return str(token)


class State:
    tenant_id: str
    member: Identity
    outsider: Identity
    member_password: str
    org: Organization
    admin: Role
    viewer: Role


S = State()


@pytest.fixture(scope="module")
def gate() -> Iterator[Gate]:
    verne = Verne(api_key=KEY, base_url=BASE_URL)
    gate = verne.gate
    cleanup: List[Callable[[], Any]] = []

    S.member_password = new_password()
    S.member = gate.identities.create(
        traits={"email": email("member")},
        credentials={"password": {"config": {"password": S.member_password}}},
    )
    cleanup.append(lambda: gate.identities.delete(S.member.id))
    S.outsider = gate.identities.create(traits={"email": email("outsider")})
    cleanup.append(lambda: gate.identities.delete(S.outsider.id))
    cleanup.append(lambda: gate.lifecycle.delete_rule("delete_unverified"))
    cleanup.append(lambda: gate.organizations.delete(S.org.id) if hasattr(S, "org") else None)

    yield gate

    for step in reversed(cleanup):
        try:
            step()
        except Exception:
            pass


# ===========================================================================
# Gate
# ===========================================================================


def test_tokens_create_authenticates_with_the_header(gate: Gate) -> None:
    token = gate.tokens.create(subject="sdk-integration")
    assert token.access_token.startswith("gat_")
    S.tenant_id = token.tenant_id
    assert len(S.tenant_id) == 36


def test_a_key_without_the_gate_scope_gets_the_403_envelope() -> None:
    if not NARROW_KEY:
        pytest.skip("VERNE_NARROW_KEY is not set")
    narrow = Gate(api_key=NARROW_KEY, base_url=BASE_URL)
    err = expect_api_error(narrow.organizations.list, 403, "forbidden")
    assert str(err) == "This API key is not authorized for Gate."
    assert err.request_id is not None and err.request_id.startswith("req_")


def test_409_is_you_already_have_this_end_user(gate: Gate) -> None:
    expect_api_error(
        lambda: gate.identities.create(traits={"email": email("member")}), 409, "conflict"
    )


def test_custom_data_trait_is_refused(gate: Gate) -> None:
    expect_api_error(
        lambda: gate.identities.create(
            traits={"email": email("custom"), "custom_data": {"a": 1}}  # type: ignore[typeddict-unknown-key]
        ),
        400,
        "invalid_payload",
    )


def test_custom_metadata_read_merge_delete_a_key(gate: Gate) -> None:
    assert gate.identities.get_metadata(S.member.id) == {}
    assert gate.identities.update_metadata(S.member.id, {"plan": "pro", "seats": 5}) == {
        "plan": "pro",
        "seats": 5,
    }
    assert gate.identities.update_metadata(S.member.id, {"seats": None}) == {"plan": "pro"}


def test_identity_patch_on_the_email_trait(gate: Gate) -> None:
    patched = gate.identities.patch(
        S.outsider.id,
        [{"op": "replace", "path": "/traits/email", "value": email("outsider2")}],
    )
    assert patched.traits["email"] == email("outsider2")


def test_organizations_create_list_get_rename(gate: Gate) -> None:
    S.org = gate.organizations.create(name="Acme")
    assert S.org.name == "Acme"
    listed = gate.organizations.list(limit=100)
    assert S.org.id in [o.id for o in listed.data]
    assert gate.organizations.get(S.org.id).id == S.org.id
    S.org = gate.organizations.update(S.org.id, name="Acme Corp")
    assert S.org.name == "Acme Corp"
    expect_api_error(lambda: gate.organizations.create(name=""), 400, "invalid_payload")


def test_roles_create_list_get_update(gate: Gate) -> None:
    roles = gate.organizations.roles
    S.admin = roles.create(
        S.org.id, name="admin", permissions=["invoices:write", "invoices:read", "invoices:read"]
    )
    assert S.admin.permissions == ["invoices:read", "invoices:write"]
    S.viewer = roles.create(S.org.id, name="viewer")
    S.viewer = roles.update(S.org.id, S.viewer.id, permissions=["invoices:read"])
    assert S.viewer.permissions == ["invoices:read"]

    first = roles.list(S.org.id, limit=1)
    assert len(first.data) == 1 and first.has_more is True
    assert first.next_cursor is not None
    second = roles.list(S.org.id, limit=1, cursor=first.next_cursor)
    assert second.data[0].id != first.data[0].id

    assert roles.get(S.org.id, S.admin.id).name == "admin"
    expect_api_error(lambda: roles.create(S.org.id, name="admin"), 409, "conflict")
    expect_api_error(lambda: roles.create(S.org.id, name="Admin"), 400, "invalid_payload")


def test_members_add_list_deadline_refuse_a_second_membership(gate: Gate) -> None:
    members = gate.organizations.members
    added = members.add(S.org.id, identity_id=S.member.id, role_id=S.admin.id)
    assert isinstance(added, Member) and added.expires_at is None
    expect_api_error(
        lambda: members.add(S.org.id, identity_id=S.member.id, role_id=S.viewer.id),
        409,
        "conflict",
    )

    deadline = (datetime.now(timezone.utc) + timedelta(days=30)).replace(microsecond=0)
    dated = members.update(S.org.id, S.member.id, expires_at=deadline)
    assert dated.expires_at is not None
    assert datetime.fromisoformat(dated.expires_at.replace("Z", "+00:00")) == deadline
    kept = members.update(S.org.id, S.member.id, role_id=S.admin.id)
    assert kept.expires_at is not None
    cleared = members.update(S.org.id, S.member.id, expires_at=None)
    assert cleared.expires_at is None

    assert [m.identity_id for m in members.list(S.org.id).data] == [S.member.id]

    held = gate.identities.list_organizations(S.member.id)
    assert [(o.id, o.role, o.permissions) for o in held.data] == [
        (S.org.id, "admin", ["invoices:read", "invoices:write"])
    ]
    assert gate.identities.list_organizations(S.outsider.id).data == []


def test_a_role_somebody_holds_cannot_be_deleted(gate: Gate) -> None:
    err = expect_api_error(
        lambda: gate.organizations.roles.delete(S.org.id, S.admin.id), 409, "conflict"
    )
    assert "held by 1 member" in str(err)


def test_authorize_and_can_every_reason(gate: Gate) -> None:
    orgs = gate.organizations
    yes = orgs.authorize(S.org.id, S.member.id, "invoices:write")
    assert (yes.allowed, yes.reason, yes.role) == (True, "member_with_permission", "admin")
    assert yes.decision_id.startswith("dec_")

    no = orgs.authorize(S.org.id, S.member.id, "members:invite")
    assert (no.allowed, no.reason, no.role) == (False, "member_without_permission", "admin")

    stranger = orgs.authorize(S.org.id, S.outsider.id, "invoices:read")
    assert (stranger.allowed, stranger.reason, stranger.role) == (False, "not_a_member", None)

    missing = orgs.authorize(str(uuid.uuid4()), S.member.id, "invoices:read")
    assert (missing.allowed, missing.reason) == (False, "no_such_organization")

    gate.identities.deactivate(S.member.id)
    try:
        inactive = orgs.authorize(S.org.id, S.member.id, "invoices:write")
        assert (inactive.allowed, inactive.reason, inactive.role) == (
            False,
            "subject_inactive",
            "admin",
        )
    finally:
        gate.identities.activate(S.member.id)

    assert orgs.can(S.org.id, S.member.id, "invoices:write") is True
    assert orgs.can(S.org.id, S.member.id, "members:invite") is False
    expect_api_error(lambda: orgs.can(S.org.id, S.member.id, "Invoices:*"), 400, "invalid_payload")

    # The plain ownership check: a code in `reason`, the sentence in `message`.
    owned = gate.authorize(subject=S.member.id, action="read", resource="doc:1")
    assert (owned.allowed, owned.reason) == (True, REASON_OWNED_BY_TENANT)
    assert "is an identity owned by tenant" in (owned.message or "")
    nobody = gate.authorize(subject=str(uuid.uuid4()), action="read", resource="doc:1")
    assert (nobody.allowed, nobody.reason) == (False, REASON_NOT_A_KNOWN_IDENTITY)
    not_an_id = gate.authorize(subject="usr_123", action="read", resource="doc:1")
    assert not_an_id.reason == REASON_NOT_A_KNOWN_IDENTITY
    gate.identities.deactivate(S.outsider.id)
    try:
        off = gate.authorize(subject=S.outsider.id, action="read", resource="doc:1")
        assert (off.allowed, off.reason) == (False, REASON_SUBJECT_INACTIVE)
    finally:
        gate.identities.activate(S.outsider.id)


def test_a_malformed_token_request_is_invalid_payload_with_a_request_id(gate: Gate) -> None:
    err = expect_api_error(lambda: gate.tokens.create(subject=""), 400, "invalid_payload")
    assert (err.request_id or "").startswith("req_")


def test_identities_no_longer_carry_the_owner_stamp(gate: Gate) -> None:
    read = gate.identities.get(S.member.id)
    assert "verne_tenant_id" not in repr(read.raw)


def test_introspection_lists_the_end_users_organizations(gate: Gate) -> None:
    token = gate.tokens.create(subject=S.member.id)
    info = gate.tokens.introspect(token.access_token)
    assert info.active is True
    assert info.orgs is not None
    assert [(o.id, o.role, o.permissions) for o in info.orgs] == [
        (S.org.id, "admin", ["invoices:read", "invoices:write"])
    ]
    inactive = gate.tokens.introspect("gat_live_not_a_token")
    assert inactive.active is False
    assert inactive.subject is None and inactive.orgs is None


def test_sessions_check_mfa_signed_token_verify_revoke(gate: Gate) -> None:
    session_token = password_login(gate, email("member"), S.member_password)

    check = gate.sessions.check(session_token)
    assert (check.active, check.identity_id, check.mfa_satisfied) == (True, S.member.id, True)
    assert check.orgs is not None and [o.id for o in check.orgs] == [S.org.id]

    security = gate.settings.get_security()
    gate.settings.update_security(
        passwordless_enabled=security.passwordless_enabled, mfa_enabled=True
    )
    try:
        err = expect_api_error(lambda: gate.sessions.check(session_token), 403, "mfa_required")
        assert err.details.get("required_aal") == "aal2"
        assert err.details.get("current_aal") == "aal1"
    finally:
        gate.settings.update_security(
            passwordless_enabled=security.passwordless_enabled,
            mfa_enabled=security.mfa_enabled,
        )

    signed = gate.tokens.create_signed(session_token)
    assert signed.session.id
    claims = gate.tokens.verify_signed(signed.token, tenant_id=S.tenant_id)
    assert (claims.sub, claims.tenant_id, claims.role, claims.sid) == (
        S.member.id,
        S.tenant_id,
        "authenticated",
        signed.session.id,
    )
    assert [(o.id, o.role) for o in claims.orgs] == [(S.org.id, "admin")]
    assert claims.iss == f"{BASE_URL}/auth/{S.tenant_id}"

    # Another tenant id means another issuer: the same token is refused.
    foreign = GateTokenVerifier(tenant_id=str(uuid.uuid4()), base_url=BASE_URL)
    with pytest.raises(VerneTokenError) as exc_info:
        foreign.verify(signed.token)
    assert exc_info.value.reason == "wrong_issuer"

    assert signed.session.id in [s.id for s in gate.sessions.list(S.member.id)]

    gate.sessions.revoke(signed.session.id)
    gate.sessions.revoke(signed.session.id)  # idempotent
    expect_api_error(lambda: gate.tokens.create_signed(session_token), 401)
    expect_api_error(lambda: gate.sessions.check(session_token), 401, "unauthorized")
    expect_api_error(lambda: gate.sessions.revoke(str(uuid.uuid4())), 404, "not_found")

    # "Log out everywhere" ends every session of the user...
    second = password_login(gate, email("member"), S.member_password)
    assert gate.sessions.check(second).active is True
    gate.sessions.revoke_all(S.member.id)
    expect_api_error(lambda: gate.sessions.check(second), 401, "unauthorized")
    # ...is idempotent — a user who never signed in is a success, twice over...
    gate.sessions.revoke_all(S.outsider.id)
    gate.sessions.revoke_all(S.outsider.id)
    # ...and an id that is not one of your users (unknown, or deleted through the API) is 403.
    expect_api_error(lambda: gate.sessions.revoke_all(str(uuid.uuid4())), 403, "forbidden")
    gone = gate.identities.create(traits={"email": email("gone")})
    gate.identities.delete(gone.id)
    expect_api_error(lambda: gate.sessions.revoke_all(gone.id), 403, "forbidden")


def test_audit_log_records_membership_changes_filtered_and_paged(gate: Gate) -> None:
    added = gate.audit_log.list(action="organization.member_added", target_id=S.member.id)
    assert len(added.data) == 1
    entry = added.data[0]
    assert entry.action == "organization.member_added"
    assert entry.actor.type == "api_key"
    assert entry.target is not None
    assert (entry.target.type, entry.target.id) == ("identity", S.member.id)

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    first = gate.audit_log.list(limit=1, from_=since)
    assert len(first.data) == 1 and first.has_more is True
    assert first.next_cursor is not None
    second = gate.audit_log.list(limit=1, cursor=first.next_cursor, from_=since)
    assert second.data[0].id != first.data[0].id

    expect_api_error(lambda: gate.audit_log.list(action="nope"), 400, "invalid_payload")


def test_lifecycle_list_set_preview_delete_actions(gate: Gate) -> None:
    rules = gate.lifecycle.list_rules()
    assert sorted(r.kind for r in rules.rules) == [
        "delete_inactive",
        "delete_unverified",
        "expire_roles",
        "remind_unverified",
    ]

    saved = gate.lifecycle.set_rule(
        "delete_unverified",
        enabled=False,
        params={"delete_after_days": 14, "warn_before_days": 3},
    )
    assert (saved.kind, saved.configured, saved.enabled) == ("delete_unverified", True, False)
    assert saved.params == {"delete_after_days": 14, "warn_before_days": 3}

    preview = gate.lifecycle.preview_rule(
        "delete_unverified", {"delete_after_days": 14, "warn_before_days": 3}
    )
    assert preview.kind == "delete_unverified" and preview.capped is False
    assert isinstance(preview.matching_now, int)
    assert gate.lifecycle.preview_rule("expire_roles").kind == "expire_roles"

    gate.lifecycle.delete_rule("delete_unverified")
    assert isinstance(gate.lifecycle.list_actions(limit=5).data, list)

    if rules.tier == "free":
        expect_api_error(
            lambda: gate.lifecycle.set_rule(
                "remind_unverified", enabled=True, params={"remind_after_hours": 24}
            ),
            403,
            "plan_required",
        )
    expect_api_error(
        lambda: gate.lifecycle.set_rule(
            "delete_unverified",
            enabled=True,
            params={"delete_after_days": 1, "warn_before_days": 1},
        ),
        400,
        "invalid_payload",
    )


def test_return_urls_round_trip_and_drive_the_login_flow(gate: Gate) -> None:
    before = gate.settings.get_return_urls()
    try:
        urls = gate.settings.update_return_urls(["http://localhost:3000/auth/callback"])
        assert urls == ["http://localhost:3000/auth/callback"]
        flow = gate.create_login_flow(
            return_to="http://localhost:3000/auth/callback", state="sdk-integration-1"
        )
        assert flow["id"]
        expect_api_error(
            lambda: gate.create_login_flow(return_to="https://elsewhere.example/cb"), 400
        )
    finally:
        gate.settings.update_return_urls(before)
    assert gate.create_registration_flow()["id"]
    expect_api_error(lambda: gate.exchange_oidc_code("gxc_not_a_code"), 404)


def test_removing_a_member_a_role_and_the_organization(gate: Gate) -> None:
    gate.organizations.members.remove(S.org.id, S.member.id)
    assert gate.organizations.can(S.org.id, S.member.id, "invoices:read") is False
    gate.organizations.roles.delete(S.org.id, S.admin.id)
    gate.organizations.roles.delete(S.org.id, S.viewer.id)
    gate.organizations.delete(S.org.id)
    expect_api_error(lambda: gate.organizations.get(S.org.id), 404, "not_found")


# ===========================================================================
# Clockwork
# ===========================================================================


def test_clockwork_usage_reports_the_plan() -> None:
    usage = Clockwork(api_key=KEY or "", base_url=BASE_URL).usage()
    assert isinstance(usage.plan, str) and usage.plan
    assert isinstance(usage.cron.active, int)
    assert isinstance(usage.delayed.pending, int)


def test_clockwork_error_is_the_standard_envelope() -> None:
    clockwork = Clockwork(api_key=KEY or "", base_url=BASE_URL)
    err = expect_api_error(
        lambda: clockwork.jobs.create(
            name="sdkpy-bad", schedule="not a schedule", url="https://example.com"
        ),
        400,
        "invalid_payload",
    )
    assert "cron" in str(err).lower()
    assert (err.request_id or "").startswith("req_")


# ===========================================================================
# Async smoke: the same transport, awaited
# ===========================================================================


async def test_async_client_against_the_stack(gate: Gate) -> None:
    verne = AsyncVerne(api_key=KEY, base_url=BASE_URL)
    org = await verne.gate.organizations.create(name="Async Acme")
    try:
        role = await verne.gate.organizations.roles.create(
            org.id, name="reader", permissions=["docs:read"]
        )
        assert role.name == "reader"
        assert (await verne.clockwork.usage()).plan
        decision = await verne.gate.organizations.authorize(org.id, S.outsider.id, "docs:read")
        assert (decision.allowed, decision.reason) == (False, "not_a_member")
        assert await verne.gate.organizations.can(org.id, S.outsider.id, "docs:read") is False
    finally:
        await verne.gate.organizations.delete(org.id)
