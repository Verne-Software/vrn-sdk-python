"""Tests for the unified Verne / AsyncVerne client (lazy init, missing keys)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncVerne, Verne, VerneError
from vernesoft._resources.gate._gate import AsyncGate, Gate
from vernesoft._resources.relay._relay import AsyncRelay, Relay

_RELAY_KEY = "vrn_9f8a7c2d1e0b4a6f"
_GATE_KEY = "vrn_3b1e5d7a9c0f2e4d"
_BASE_URL = "https://api.vernesoft.com"

_MSG_PAYLOAD = {
    "id": "msg_abc",
    "event_type": "user.created",
    "status": "accepted",
    "timestamp": "2026-03-17T12:00:00Z",
}

_IDENTITY_PAYLOAD = {
    "id": "identity_456",
    "schema_id": "user",
    "state": "active",
    "traits": {"email": "x@y.com"},
}


# ===========================================================================
# Lazy initialization — sync
# ===========================================================================


def test_relay_lazy_init_returns_relay_instance() -> None:
    verne = Verne(relay=_RELAY_KEY, base_url=_BASE_URL)
    # Before first access, internal cache is None
    assert verne._relay_client is None
    relay = verne.relay
    assert isinstance(relay, Relay)
    # Second access returns the same object
    assert verne.relay is relay


def test_gate_lazy_init_returns_gate_instance() -> None:
    verne = Verne(gate=_GATE_KEY, base_url=_BASE_URL)
    assert verne._gate_client is None
    gate = verne.gate
    assert isinstance(gate, Gate)
    assert verne.gate is gate


def test_missing_relay_key_raises_verne_error() -> None:
    verne = Verne(gate=_GATE_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneError, match="relay"):
        _ = verne.relay


def test_missing_gate_key_raises_verne_error() -> None:
    verne = Verne(relay=_RELAY_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneError, match="gate"):
        _ = verne.gate


def test_no_keys_raises_verne_error_on_relay() -> None:
    verne = Verne()
    with pytest.raises(VerneError):
        _ = verne.relay


def test_no_keys_raises_verne_error_on_gate() -> None:
    verne = Verne()
    with pytest.raises(VerneError):
        _ = verne.gate


# ===========================================================================
# Lazy initialization — async
# ===========================================================================


def test_async_relay_lazy_init() -> None:
    verne = AsyncVerne(relay=_RELAY_KEY, base_url=_BASE_URL)
    assert verne._relay_client is None
    relay = verne.relay
    assert isinstance(relay, AsyncRelay)
    assert verne.relay is relay


def test_async_gate_lazy_init() -> None:
    verne = AsyncVerne(gate=_GATE_KEY, base_url=_BASE_URL)
    assert verne._gate_client is None
    gate = verne.gate
    assert isinstance(gate, AsyncGate)
    assert verne.gate is gate


def test_async_missing_relay_key_raises() -> None:
    verne = AsyncVerne(gate=_GATE_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneError, match="relay"):
        _ = verne.relay


def test_async_missing_gate_key_raises() -> None:
    verne = AsyncVerne(relay=_RELAY_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneError, match="gate"):
        _ = verne.gate


# ===========================================================================
# Full round-trips through the unified client — sync
# ===========================================================================


def test_verne_relay_send(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    verne = Verne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    msg = verne.relay.messages.send(event_type="user.created", payload={"id": "123"})
    assert msg.id == "msg_abc"


def test_verne_gate_identity_create(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    verne = Verne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    identity = verne.gate.identities.create(
        schema_id="user",
        traits={"email": "x@y.com"},
    )
    assert identity.id == "identity_456"


def test_verne_both_services_work(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    verne = Verne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    msg = verne.relay.messages.send(event_type="user.created", payload={})
    identity = verne.gate.identities.create(schema_id="user", traits={"email": "x@y.com"})

    assert msg.id == "msg_abc"
    assert identity.id == "identity_456"


# ===========================================================================
# Full round-trips through the unified client — async
# ===========================================================================


async def test_async_verne_relay_send(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    verne = AsyncVerne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    msg = await verne.relay.messages.send(event_type="user.created", payload={})
    assert msg.id == "msg_abc"


async def test_async_verne_gate_identity_create(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    verne = AsyncVerne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    identity = await verne.gate.identities.create(schema_id="user", traits={"email": "x@y.com"})
    assert identity.id == "identity_456"


async def test_async_verne_both_services(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    verne = AsyncVerne(relay=_RELAY_KEY, gate=_GATE_KEY, base_url=_BASE_URL)
    msg = await verne.relay.messages.send(event_type="user.created", payload={})
    identity = await verne.gate.identities.create(schema_id="user", traits={"email": "x@y.com"})

    assert msg.event_type == "user.created"
    assert identity.schema_id == "user"


# ===========================================================================
# One shared key (api_key), per-service keys override it
# ===========================================================================

_SHARED_KEY = "vrn_0a1b2c3d4e5f6a7b"


def test_shared_key_reaches_every_service(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST", url=f"{_BASE_URL}/v1/relay/messages", status_code=202, json=_MSG_PAYLOAD
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )
    httpx_mock.add_response(method="GET", url=f"{_BASE_URL}/v1/clockwork/jobs", json=[])
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/login/start",
        json={"nonce": "n", "deep_link": "tg://x", "expires_at": "2026-10-14T10:00:00Z"},
    )

    verne = Verne(api_key=_SHARED_KEY, base_url=_BASE_URL)
    verne.relay.messages.send(event_type="user.created", payload={})
    verne.gate.identities.create(traits={"email": "x@y.com"})
    verne.clockwork.jobs.list()
    verne.passepartout.login_start()

    for request in httpx_mock.get_requests():
        assert request.headers["Authorization"] == f"Bearer {_SHARED_KEY}"


def test_per_service_key_overrides_the_shared_one(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST", url=f"{_BASE_URL}/v1/relay/messages", status_code=202, json=_MSG_PAYLOAD
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/identities",
        status_code=201,
        json=_IDENTITY_PAYLOAD,
    )

    verne = Verne(api_key=_SHARED_KEY, relay=_RELAY_KEY, base_url=_BASE_URL)
    verne.relay.messages.send(event_type="user.created", payload={})
    verne.gate.identities.create(traits={"email": "x@y.com"})

    relay_request, gate_request = httpx_mock.get_requests()
    assert relay_request.headers["Authorization"] == f"Bearer {_RELAY_KEY}"
    assert gate_request.headers["Authorization"] == f"Bearer {_SHARED_KEY}"


async def test_async_shared_key(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE_URL}/v1/clockwork/jobs", json=[])
    verne = AsyncVerne(api_key=_SHARED_KEY, base_url=_BASE_URL)
    await verne.clockwork.jobs.list()
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_SHARED_KEY}"


def test_no_key_names_api_key_first() -> None:
    with pytest.raises(VerneError) as exc_info:
        _ = Verne().clockwork
    message = str(exc_info.value)
    assert message.index("api_key") < message.index("clockwork=")
    with pytest.raises(VerneError, match="api_key"):
        _ = AsyncVerne().passepartout
