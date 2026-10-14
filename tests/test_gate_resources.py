"""Tests for the Gate resources added in 1.4.0: audit log, lifecycle, sessions, signed
tokens, metadata, return URLs and flows; plus introspection ``orgs`` and Clockwork usage."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
import pytest
from pytest_httpx import HTTPXMock

from vernesoft import (
    AsyncClockwork,
    AsyncGate,
    AsyncPassepartout,
    Clockwork,
    Gate,
    OrgClaim,
    Passepartout,
    VerneAPIError,
)

_API_KEY = "vrn_3b1e5d7a9c0f2e4d"
_BASE_URL = "https://api.vernesoft.com"
_ID = "c0ffee00-1111-4222-8333-444455556666"
_ORG = {"id": "0b6f8f9e-1c2d-4e5f-8a9b-0c1d2e3f4a5b", "role": "admin", "permissions": ["a:b"]}


@pytest.fixture()
def gate() -> Gate:
    return Gate(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_gate() -> AsyncGate:
    return AsyncGate(api_key=_API_KEY, base_url=_BASE_URL)


def _body(request: httpx.Request | None) -> Any:
    assert request is not None
    return json.loads(request.content)


# ===========================================================================
# Audit log
# ===========================================================================

_ENTRY = {
    "id": "aud_1",
    "occurred_at": "2026-10-14T09:00:00Z",
    "action": "organization.member_added",
    "actor": {"type": "api_key", "id": "key_1"},
    "target": {"type": "identity", "id": _ID},
    "project_id": None,
    "details": {"role": "admin"},
    "ip": "203.0.113.7",
    "user_agent": "vernesoft-python",
}


def test_audit_log_list_with_filters(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=(
            f"{_BASE_URL}/v1/gate/audit-log?limit=10&action=organization.member_added"
            f"&actor_type=api_key&target_id={_ID}"
            "&from=2026-10-14T08%3A00%3A00Z&to=2026-10-14T10%3A00%3A00Z"
        ),
        json={"data": [_ENTRY], "has_more": False, "next_cursor": None},
    )
    page = gate.audit_log.list(
        limit=10,
        action="organization.member_added",
        actor_type="api_key",
        target_id=_ID,
        from_=datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc),
        to="2026-10-14T10:00:00Z",
    )
    entry = page.data[0]
    assert entry.action == "organization.member_added"
    assert entry.actor.type == "api_key" and entry.actor.id == "key_1"
    assert entry.target is not None and entry.target.id == _ID
    assert entry.details == {"role": "admin"}
    assert entry.ip == "203.0.113.7"


def test_audit_log_list_without_filters_sends_no_query(httpx_mock: HTTPXMock, gate: Gate) -> None:
    system = {**_ENTRY, "actor": {"type": "system", "id": None}, "target": None}
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/audit-log",
        json={"data": [system], "has_more": True, "next_cursor": "c2"},
    )
    page = gate.audit_log.list()
    assert page.has_more and page.next_cursor == "c2"
    assert page.data[0].target is None and page.data[0].actor.id is None


# ===========================================================================
# Lifecycle
# ===========================================================================

_RULE = {
    "kind": "delete_unverified",
    "configured": True,
    "enabled": False,
    "params": {"delete_after_days": 14, "warn_before_days": 3},
    "available": True,
    "disabled_reason": None,
    "enabled_at": None,
    "updated_at": "2026-10-14T09:00:00Z",
    "pending": 0,
}


def test_lifecycle_list_rules(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/lifecycle/rules",
        json={"tier": "free", "rules": [_RULE]},
    )
    rules = gate.lifecycle.list_rules()
    assert rules.tier == "free"
    assert rules.rules[0].params == {"delete_after_days": 14, "warn_before_days": 3}


def test_lifecycle_set_rule_sends_exactly_enabled_and_params(
    httpx_mock: HTTPXMock, gate: Gate
) -> None:
    url = f"{_BASE_URL}/v1/gate/lifecycle/rules/delete_unverified"
    httpx_mock.add_response(method="PUT", url=url, json=_RULE)
    httpx_mock.add_response(method="PUT", url=url, json=_RULE)
    rule = gate.lifecycle.set_rule(
        "delete_unverified",
        enabled=False,
        params={"delete_after_days": 14, "warn_before_days": 3},
    )
    assert rule.configured is True and rule.enabled is False
    gate.lifecycle.set_rule("delete_unverified", enabled=True)
    first, second = (_body(r) for r in httpx_mock.get_requests())
    assert first == {
        "enabled": False,
        "params": {"delete_after_days": 14, "warn_before_days": 3},
    }
    assert second == {"enabled": True}  # params left out keeps the saved settings


def test_lifecycle_preview_delete_and_actions(httpx_mock: HTTPXMock, gate: Gate) -> None:
    base = f"{_BASE_URL}/v1/gate/lifecycle"
    httpx_mock.add_response(
        method="POST",
        url=f"{base}/rules/expire_roles/preview",
        json={"kind": "expire_roles", "available": False, "matching_now": 3, "capped": False},
    )
    httpx_mock.add_response(method="DELETE", url=f"{base}/rules/expire_roles", status_code=204)
    httpx_mock.add_response(
        method="GET",
        url=f"{base}/actions?status=pending&kind=delete_unverified&limit=5",
        json={
            "data": [
                {
                    "id": "act_1",
                    "kind": "delete_unverified",
                    "step": "warn",
                    "identity_id": _ID,
                    "status": "pending",
                    "basis_at": "2026-10-01T00:00:00Z",
                    "due_at": "2026-10-12T00:00:00Z",
                    "reason": None,
                    "created_at": "2026-10-01T00:00:00Z",
                    "finished_at": None,
                }
            ],
            "has_more": False,
            "next_cursor": None,
        },
    )
    preview = gate.lifecycle.preview_rule("expire_roles")
    assert preview.matching_now == 3 and preview.available is False
    assert _body(httpx_mock.get_requests()[0]) == {"params": {}}
    gate.lifecycle.delete_rule("expire_roles")
    actions = gate.lifecycle.list_actions(status="pending", kind="delete_unverified", limit=5)
    assert actions.data[0].step == "warn"


def test_lifecycle_plan_required(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{_BASE_URL}/v1/gate/lifecycle/rules/remind_unverified",
        status_code=403,
        json={
            "error": {
                "code": "plan_required",
                "message": "Your plan does not include this rule.",
                "request_id": "r",
                "plan": "free",
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        gate.lifecycle.set_rule(
            "remind_unverified", enabled=True, params={"remind_after_hours": 24}
        )
    assert exc_info.value.code == "plan_required"
    assert exc_info.value.details == {"plan": "free"}


# ===========================================================================
# Sessions
# ===========================================================================

_SESSION = {
    "id": "ses_1",
    "active": True,
    "authenticated_at": "2026-10-14T09:00:00Z",
    "expires_at": "2026-10-15T09:00:00Z",
    "issued_at": "2026-10-14T09:00:00Z",
    "authenticator_assurance_level": "aal1",
    "authentication_methods": [{"method": "password", "completed_at": "2026-10-14T09:00:00Z"}],
    "devices": [{"id": "dev_1", "ip_address": "203.0.113.7", "user_agent": "x"}],
    "identity": {"id": _ID},
    "tokenized_extra": "kept",
}


def test_sessions_list_revoke_revoke_all(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET", url=f"{_BASE_URL}/v1/gate/identities/{_ID}/sessions", json=[_SESSION]
    )
    httpx_mock.add_response(
        method="DELETE", url=f"{_BASE_URL}/v1/gate/identities/{_ID}/sessions", status_code=204
    )
    httpx_mock.add_response(
        method="DELETE", url=f"{_BASE_URL}/v1/gate/sessions/ses_1", status_code=204
    )
    sessions = gate.sessions.list(_ID)
    assert sessions[0].id == "ses_1"
    assert sessions[0].authentication_methods[0]["method"] == "password"
    assert sessions[0].raw["tokenized_extra"] == "kept"
    gate.sessions.revoke_all(_ID)
    gate.sessions.revoke("ses_1")


def test_session_check_sends_the_session_header(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/auth/session",
        json={
            "active": True,
            "aal": "aal1",
            "mfa_required": False,
            "mfa_satisfied": True,
            "identity_id": _ID,
            "orgs": [_ORG],
        },
    )
    check = gate.sessions.check("ory_st_abc")
    assert check.mfa_satisfied is True
    assert check.orgs == [OrgClaim.from_dict(_ORG)]
    assert check.orgs_truncated is False
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Session-Token"] == "ory_st_abc"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


def test_session_check_mfa_required(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/auth/session",
        status_code=403,
        json={
            "error": {
                "code": "mfa_required",
                "message": "A second factor is required.",
                "request_id": "r",
                "required_aal": "aal2",
                "current_aal": "aal1",
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        gate.sessions.check("ory_st_abc")
    assert exc_info.value.code == "mfa_required"
    assert exc_info.value.details == {"required_aal": "aal2", "current_aal": "aal1"}


# ===========================================================================
# Signed tokens (mint) and introspection orgs
# ===========================================================================


def test_create_signed_uses_the_session_not_the_key(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/auth/sessions/whoami?tokenize_as=gate_jwt",
        json={**_SESSION, "tokenized": "eyJ.a.b"},
    )
    signed = gate.tokens.create_signed("ory_st_abc")
    assert signed.token == "eyJ.a.b"
    assert signed.session.id == "ses_1"
    assert "tokenized" not in signed.session.raw
    request = httpx_mock.get_request()
    assert request is not None
    assert "Authorization" not in request.headers
    assert request.headers["X-Session-Token"] == "ory_st_abc"


def test_create_signed_dead_session_is_401(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/auth/sessions/whoami?tokenize_as=gate_jwt",
        status_code=401,
        json={"error": {"code": 401, "status": "Unauthorized", "message": "No valid session"}},
    )
    with pytest.raises(VerneAPIError) as exc_info:
        gate.tokens.create_signed("dead")
    assert exc_info.value.status == 401 and exc_info.value.code == "unknown"


def test_introspect_inactive_is_only_active_false(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST", url=f"{_BASE_URL}/v1/gate/tokens/introspect", json={"active": False}
    )
    info = gate.tokens.introspect("gat_live_nope")
    assert info.active is False
    assert info.subject is None and info.tenant_id is None and info.expires_at is None
    assert info.orgs is None


def test_introspect_orgs(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens/introspect",
        json={
            "active": True,
            "subject": _ID,
            "tenant_id": "ten_1",
            "scopes": [],
            "expires_at": "2026-10-14T10:00:00Z",
            "orgs": [_ORG],
            "orgs_truncated": True,
        },
    )
    info = gate.tokens.introspect("gat_live_x")
    assert info.orgs == [OrgClaim(id=_ORG["id"], role="admin", permissions=["a:b"])]
    assert info.orgs_truncated is True


def test_passepartout_introspect_orgs(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/tokens/introspect",
        json={"active": True, "subject": _ID, "orgs": [_ORG]},
    )
    info = Passepartout(api_key=_API_KEY, base_url=_BASE_URL).introspect("pp_x")
    assert info.orgs is not None and info.orgs[0].role == "admin"
    assert info.orgs_truncated is False


async def test_async_passepartout_introspect_inactive(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/tokens/introspect",
        json={"active": False},
    )
    info = await AsyncPassepartout(api_key=_API_KEY, base_url=_BASE_URL).introspect("pp_x")
    assert info.active is False and info.orgs is None


# ===========================================================================
# Metadata
# ===========================================================================


def test_metadata_get_and_update(httpx_mock: HTTPXMock, gate: Gate) -> None:
    url = f"{_BASE_URL}/v1/gate/identities/{_ID}/metadata"
    httpx_mock.add_response(method="GET", url=url, json={"metadata_public": {}})
    httpx_mock.add_response(method="PATCH", url=url, json={"metadata_public": {"plan": "pro"}})
    assert gate.identities.get_metadata(_ID) == {}
    assert gate.identities.update_metadata(_ID, {"plan": "pro", "seats": None}) == {"plan": "pro"}
    assert _body(httpx_mock.get_requests()[1]) == {"plan": "pro", "seats": None}


# ===========================================================================
# Return URLs, flows, OIDC exchange
# ===========================================================================


def test_return_urls(httpx_mock: HTTPXMock, gate: Gate) -> None:
    url = f"{_BASE_URL}/v1/gate/settings/return-urls"
    httpx_mock.add_response(method="GET", url=url, json={"return_urls": []})
    httpx_mock.add_response(
        method="PUT", url=url, json={"return_urls": ["https://app.example.com/cb"]}
    )
    assert gate.settings.get_return_urls() == []
    assert gate.settings.update_return_urls(["https://app.example.com/cb"]) == [
        "https://app.example.com/cb"
    ]
    assert _body(httpx_mock.get_requests()[1]) == {"return_urls": ["https://app.example.com/cb"]}


def test_login_flow_without_params_is_unchanged(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE_URL}/v1/gate/auth/login", json={"id": "f"})
    assert gate.create_login_flow() == {"id": "f"}
    request = httpx_mock.get_request()
    assert request is not None and "X-Session-Token" not in request.headers


def test_login_flow_step_up(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=(
            f"{_BASE_URL}/v1/gate/auth/login?return_to=https%3A%2F%2Fapp.example.com%2Fcb"
            "&state=s-1&aal=aal2"
        ),
        json={"id": "f2"},
    )
    flow = gate.create_login_flow(
        return_to="https://app.example.com/cb",
        state="s-1",
        aal="aal2",
        session_token="ory_st_abc",
    )
    assert flow["id"] == "f2"
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["X-Session-Token"] == "ory_st_abc"
    assert "ory_st_abc" not in str(request.url)


def test_registration_flow_and_exchange(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/auth/registration?state=s-2",
        json={"id": "reg"},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/auth/oidc/exchange",
        json={"session_token": "ory_st_new", "session": _SESSION},
    )
    assert gate.create_registration_flow(state="s-2")["id"] == "reg"
    result = gate.exchange_oidc_code("gxc_123")
    assert result.session_token == "ory_st_new"
    assert result.session.id == "ses_1"
    assert _body(httpx_mock.get_requests()[1]) == {"code": "gxc_123"}


def test_enabled_providers_sends_no_key(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET", url=f"{_BASE_URL}/public/gate/providers/ten_1", json={"providers": []}
    )
    gate.get_enabled_providers("ten_1")
    request = httpx_mock.get_request()
    assert request is not None and "Authorization" not in request.headers


# ===========================================================================
# Clockwork usage and Execution.attempt
# ===========================================================================

_USAGE: Dict[str, Any] = {
    "plan": "free",
    "tier": "free",
    "cron": {"active": 2, "limit": 5},
    "delayed": {"pending": 0, "limit": None},
}


def test_clockwork_usage(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE_URL}/v1/clockwork/usage", json=_USAGE)
    usage = Clockwork(api_key=_API_KEY, base_url=_BASE_URL).usage()
    assert usage.plan == "free" and usage.tier == "free"
    assert usage.cron.active == 2 and usage.cron.limit == 5
    assert usage.delayed.pending == 0 and usage.delayed.limit is None


async def test_async_clockwork_usage(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE_URL}/v1/clockwork/usage", json=_USAGE)
    usage = await AsyncClockwork(api_key=_API_KEY, base_url=_BASE_URL).usage()
    assert usage.cron.limit == 5


def test_execution_attempt(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/jobs/job_1/executions",
        json=[
            {
                "id": "ex_1",
                "job_id": "job_1",
                "status": "failed",
                "started_at": "2026-10-14T09:00:00Z",
                "completed_at": None,
                "duration_ms": None,
                "response_status": 500,
                "response_body": None,
                "error_message": "HTTP 500",
                "attempt": 2,
            }
        ],
    )
    executions = Clockwork(api_key=_API_KEY, base_url=_BASE_URL).jobs.executions("job_1")
    assert executions[0].attempt == 2


# ===========================================================================
# Async resources
# ===========================================================================


async def test_async_sessions_audit_lifecycle_metadata(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/auth/session",
        json={"active": True, "aal": "aal1", "mfa_required": False, "mfa_satisfied": True},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/audit-log?limit=1",
        json={"data": [_ENTRY], "has_more": False, "next_cursor": None},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/lifecycle/rules",
        json={"tier": "pro", "rules": [_RULE]},
    )
    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/{_ID}/metadata",
        json={"metadata_public": {"a": 1}},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/auth/sessions/whoami?tokenize_as=gate_jwt",
        json={**_SESSION, "tokenized": "eyJ.a.b"},
    )
    assert (await async_gate.sessions.check("st")).identity_id is None
    assert (await async_gate.audit_log.list(limit=1)).data[0].id == "aud_1"
    assert (await async_gate.lifecycle.list_rules()).tier == "pro"
    assert await async_gate.identities.update_metadata(_ID, {"a": 1}) == {"a": 1}
    assert (await async_gate.tokens.create_signed("st")).token == "eyJ.a.b"
    whoami = httpx_mock.get_requests()[-1]
    assert "Authorization" not in whoami.headers
