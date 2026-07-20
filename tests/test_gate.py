"""Tests for the Gate resource (sync and async)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncGate, Gate, VerneAPIError
from vernesoft._resources.gate._types import (
    AccessToken,
    AuthorizeResult,
    Identity,
    IntrospectResult,
    SecuritySettings,
)

_API_KEY = "vrn_gate_test_sk_testkey"
_BASE_URL = "https://api.vernesoft.com"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def gate() -> Gate:
    return Gate(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_gate() -> AsyncGate:
    return AsyncGate(api_key=_API_KEY, base_url=_BASE_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_IDENTITY_PAYLOAD = {
    "id": "identity_123",
    "schema_id": "user",
    "state": "active",
    "traits": {
        "email": "user@example.com",
        "tenant_id": "ten_001",
        "custom_data": {"role": "editor"},
    },
}

_TOKEN_PAYLOAD = {
    "access_token": "gat_test_at_abc123",
    "expires_at": "2026-03-17T12:00:00Z",
    "subject": "usr_123",
    "tenant_id": "ten_001",
}

_INTROSPECT_PAYLOAD = {
    "active": True,
    "subject": "usr_123",
    "tenant_id": "ten_001",
    "scopes": ["gate.tokens.read"],
    "expires_at": "2026-03-17T12:00:00Z",
}

_AUTHORIZE_PAYLOAD = {
    "allowed": True,
    "decision_id": "dec_9f8a7c",
    "reason": "subject has role=admin on tenant:ten_001",
}


# ===========================================================================
# Identity CRUD — synchronous
# ===========================================================================


def test_identity_create(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    identity = gate.identities.create(
        schema_id="user",
        traits={"email": "user@example.com", "custom_data": {"role": "editor"}},
        credentials={"password": {"config": {"password": "Secret123!"}}},
        state="active",
    )

    assert isinstance(identity, Identity)
    assert identity.id == "identity_123"
    assert identity.schema_id == "user"
    assert identity.state == "active"
    assert identity.traits["email"] == "user@example.com"
    assert identity.traits["tenant_id"] == "ten_001"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


def test_identity_get(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123",
        status_code=200,
        json=_IDENTITY_PAYLOAD,
    )

    identity = gate.identities.get("identity_123")
    assert identity.id == "identity_123"


def test_identity_patch(httpx_mock: HTTPXMock, gate: Gate) -> None:
    patched = dict(_IDENTITY_PAYLOAD)
    patched["traits"] = {**_IDENTITY_PAYLOAD["traits"], "custom_data": {"role": "admin"}}

    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123",
        status_code=200,
        json=patched,
    )

    updated = gate.identities.patch(
        "identity_123",
        [{"op": "replace", "path": "/traits/custom_data/role", "value": "admin"}],
    )

    assert updated.traits["custom_data"]["role"] == "admin"


def test_identity_delete(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123",
        status_code=204,
    )

    result = gate.identities.delete("identity_123")
    assert result is None


def test_identity_set_state(httpx_mock: HTTPXMock, gate: Gate) -> None:
    import json

    deactivated = {**_IDENTITY_PAYLOAD, "state": "inactive"}
    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/state",
        status_code=200,
        json=deactivated,
    )

    identity = gate.identities.set_state("identity_123", "inactive")

    assert identity.state == "inactive"
    request = httpx_mock.get_request()
    assert request is not None
    assert json.loads(request.content) == {"state": "inactive"}


def test_identity_activate(httpx_mock: HTTPXMock, gate: Gate) -> None:
    import json

    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/state",
        status_code=200,
        json=_IDENTITY_PAYLOAD,
    )

    gate.identities.activate("identity_123")

    assert json.loads(httpx_mock.get_request().content) == {"state": "active"}


def test_identity_deactivate(httpx_mock: HTTPXMock, gate: Gate) -> None:
    import json

    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/state",
        status_code=200,
        json={**_IDENTITY_PAYLOAD, "state": "inactive"},
    )

    gate.identities.deactivate("identity_123")

    assert json.loads(httpx_mock.get_request().content) == {"state": "inactive"}


def test_identity_resend_verification(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/resend-verification",
        status_code=204,
    )

    result = gate.identities.resend_verification("identity_123")
    assert result is None


def test_identity_get_not_found(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/identities/missing_id",
        status_code=404,
        json={
            "error": {
                "code": "not_found",
                "message": "Identity not found.",
                "request_id": "req_404",
            }
        },
    )

    with pytest.raises(VerneAPIError) as exc_info:
        gate.identities.get("missing_id")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "not_found"


# ===========================================================================
# Tokens — synchronous
# ===========================================================================


def test_tokens_create_no_auth_header(httpx_mock: HTTPXMock, gate: Gate) -> None:
    """POST /v1/gate/tokens must NOT send Authorization header; api_key goes in body."""
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens",
        status_code=200,
        json=_TOKEN_PAYLOAD,
    )

    token = gate.tokens.create(subject="usr_123", scopes=["gate.tokens.read"])

    assert isinstance(token, AccessToken)
    assert token.access_token == "gat_test_at_abc123"
    assert token.subject == "usr_123"
    assert token.tenant_id == "ten_001"

    request = httpx_mock.get_request()
    assert request is not None
    # The crucial assertion: no Authorization header
    assert "Authorization" not in request.headers
    # api_key should be in the request body
    import json

    body = json.loads(request.content)
    assert body["api_key"] == _API_KEY
    assert body["subject"] == "usr_123"
    assert body["scopes"] == ["gate.tokens.read"]


def test_tokens_create_with_ttl(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens",
        status_code=200,
        json=_TOKEN_PAYLOAD,
    )

    import json

    token = gate.tokens.create(subject="usr_123", ttl_seconds=7200)
    assert token.access_token == "gat_test_at_abc123"

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content)
    assert body["ttl_seconds"] == 7200


def test_tokens_introspect(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens/introspect",
        status_code=200,
        json=_INTROSPECT_PAYLOAD,
    )

    info = gate.tokens.introspect("gat_test_at_abc123")

    assert isinstance(info, IntrospectResult)
    assert info.active is True
    assert info.subject == "usr_123"
    assert info.tenant_id == "ten_001"
    assert info.scopes == ["gate.tokens.read"]
    assert info.expires_at == "2026-03-17T12:00:00Z"

    # introspect uses regular auth header
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


# ===========================================================================
# Authorize — synchronous
# ===========================================================================


def test_authorize_allowed(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        status_code=200,
        json=_AUTHORIZE_PAYLOAD,
    )

    result = gate.authorize(
        subject="usr_123",
        action="relay.messages.read",
        resource="tenant:ten_001",
    )

    assert isinstance(result, AuthorizeResult)
    assert result.allowed is True
    assert result.decision_id == "dec_9f8a7c"
    assert result.reason == "subject has role=admin on tenant:ten_001"


def test_authorize_denied(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        status_code=200,
        json={
            "allowed": False,
            "decision_id": "dec_deny",
            "reason": "insufficient permissions",
        },
    )

    result = gate.authorize(
        subject="usr_456",
        action="relay.messages.write",
        resource="tenant:ten_001",
    )

    assert result.allowed is False
    assert result.decision_id == "dec_deny"


def test_authorize_with_context(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        status_code=200,
        json=_AUTHORIZE_PAYLOAD,
    )

    import json

    result = gate.authorize(
        subject="usr_123",
        action="relay.messages.read",
        resource="tenant:ten_001",
        context={"ip": "1.2.3.4"},
    )
    assert result.allowed is True

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content)
    assert body["context"] == {"ip": "1.2.3.4"}


# ===========================================================================
# Settings — synchronous
# ===========================================================================


def test_settings_get_security(httpx_mock: HTTPXMock, gate: Gate) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/settings/security",
        status_code=200,
        json={"passwordless_enabled": True, "mfa_enabled": False},
    )

    settings = gate.settings.get_security()

    assert isinstance(settings, SecuritySettings)
    assert settings.passwordless_enabled is True
    assert settings.mfa_enabled is False


def test_settings_update_security(httpx_mock: HTTPXMock, gate: Gate) -> None:
    import json

    httpx_mock.add_response(
        method="PUT",
        url=f"{_BASE_URL}/v1/gate/settings/security",
        status_code=200,
        json={"status": "ok"},
    )

    result = gate.settings.update_security(passwordless_enabled=True, mfa_enabled=True)
    assert result is None

    request = httpx_mock.get_request()
    assert request is not None
    assert json.loads(request.content) == {
        "passwordless_enabled": True,
        "mfa_enabled": True,
    }


# ===========================================================================
# Async variants
# ===========================================================================


async def test_async_identity_create(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    identity = await async_gate.identities.create(
        schema_id="user",
        traits={"email": "a@b.com"},
    )
    assert identity.id == "identity_123"
    assert identity.state == "active"


async def test_async_tokens_create_no_auth_header(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens",
        status_code=200,
        json=_TOKEN_PAYLOAD,
    )

    token = await async_gate.tokens.create(subject="usr_123")
    assert token.access_token == "gat_test_at_abc123"

    request = httpx_mock.get_request()
    assert request is not None
    assert "Authorization" not in request.headers


async def test_async_tokens_introspect(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens/introspect",
        status_code=200,
        json=_INTROSPECT_PAYLOAD,
    )

    info = await async_gate.tokens.introspect("gat_test_at_abc123")
    assert info.active is True
    assert info.scopes == ["gate.tokens.read"]


async def test_async_authorize(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/authorize",
        status_code=200,
        json=_AUTHORIZE_PAYLOAD,
    )

    result = await async_gate.authorize(
        subject="usr_123",
        action="relay.messages.read",
        resource="tenant:ten_001",
    )
    assert result.allowed is True


async def test_async_identity_delete(httpx_mock: HTTPXMock, async_gate: AsyncGate) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123",
        status_code=204,
    )

    result = await async_gate.identities.delete("identity_123")
    assert result is None


async def test_async_identity_deactivate(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    import json

    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/state",
        status_code=200,
        json={**_IDENTITY_PAYLOAD, "state": "inactive"},
    )

    identity = await async_gate.identities.deactivate("identity_123")

    assert identity.state == "inactive"
    assert json.loads(httpx_mock.get_request().content) == {"state": "inactive"}


async def test_async_identity_resend_verification(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities/identity_123/resend-verification",
        status_code=204,
    )

    result = await async_gate.identities.resend_verification("identity_123")
    assert result is None


async def test_async_settings_get_security(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/settings/security",
        status_code=200,
        json={"passwordless_enabled": False, "mfa_enabled": True},
    )

    settings = await async_gate.settings.get_security()
    assert settings.passwordless_enabled is False
    assert settings.mfa_enabled is True


async def test_async_settings_update_security(
    httpx_mock: HTTPXMock, async_gate: AsyncGate
) -> None:
    import json

    httpx_mock.add_response(
        method="PUT",
        url=f"{_BASE_URL}/v1/gate/settings/security",
        status_code=200,
        json={"status": "ok"},
    )

    await async_gate.settings.update_security(passwordless_enabled=True, mfa_enabled=False)

    assert json.loads(httpx_mock.get_request().content) == {
        "passwordless_enabled": True,
        "mfa_enabled": False,
    }
