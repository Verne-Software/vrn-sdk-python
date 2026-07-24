"""Tests for the Passepartout resource (sync and async)."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncPassepartout, Passepartout
from vernesoft._resources.passepartout._types import (
    LoginStart,
    LoginStatus,
    TelegramUser,
    TokenIntrospection,
)

_API_KEY = "vrn_passepartout_test_sk_testkey"
_BASE_URL = "https://api.vernesoft.com"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def passepartout() -> Passepartout:
    return Passepartout(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_passepartout() -> AsyncPassepartout:
    return AsyncPassepartout(api_key=_API_KEY, base_url=_BASE_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOGIN_START_PAYLOAD = {
    "nonce": "nonce_abc123",
    "deep_link": "https://t.me/verne_bot?start=nonce_abc123",
    "expires_at": "2026-03-17T12:00:00Z",
}

_LOGIN_STATUS_PAYLOAD = {
    "status": "confirmed",
    "access_token": "ppt_test_at_abc123",
    "expires_at": "2026-03-17T12:00:00Z",
    "identity_id": "identity_123",
    "user": {
        "id": "tg_555",
        "username": "durov",
        "first_name": "Pavel",
        "photo_url": "https://t.me/i/userpic/320/durov.jpg",
    },
}

_LOGIN_STATUS_PENDING_PAYLOAD = {
    "status": "pending",
}

_INTROSPECT_PAYLOAD = {
    "active": True,
    "subject": "tg_555",
    "tenant_id": "ten_001",
    "scopes": ["passepartout.login"],
    "expires_at": "2026-03-17T12:00:00Z",
}


# ===========================================================================
# login_start — synchronous
# ===========================================================================


def test_login_start(httpx_mock: HTTPXMock, passepartout: Passepartout) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/login/start",
        status_code=200,
        json=_LOGIN_START_PAYLOAD,
    )

    result = passepartout.login_start()

    assert isinstance(result, LoginStart)
    assert result.nonce == "nonce_abc123"
    assert result.deep_link == "https://t.me/verne_bot?start=nonce_abc123"
    assert result.expires_at == "2026-03-17T12:00:00Z"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


# ===========================================================================
# login_status — synchronous
# ===========================================================================


def test_login_status(httpx_mock: HTTPXMock, passepartout: Passepartout) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/passepartout/login/status?nonce=nonce_abc123",
        status_code=200,
        json=_LOGIN_STATUS_PAYLOAD,
    )

    result = passepartout.login_status("nonce_abc123")

    assert isinstance(result, LoginStatus)
    assert result.status == "confirmed"
    assert result.access_token == "ppt_test_at_abc123"
    assert result.expires_at == "2026-03-17T12:00:00Z"
    assert result.identity_id == "identity_123"
    assert isinstance(result.user, TelegramUser)
    assert result.user.id == "tg_555"
    assert result.user.username == "durov"
    assert result.user.first_name == "Pavel"
    assert result.user.photo_url == "https://t.me/i/userpic/320/durov.jpg"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "GET"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"
    assert request.url.params["nonce"] == "nonce_abc123"


def test_login_status_pending_no_user(
    httpx_mock: HTTPXMock, passepartout: Passepartout
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/passepartout/login/status?nonce=nonce_pending",
        status_code=200,
        json=_LOGIN_STATUS_PENDING_PAYLOAD,
    )

    result = passepartout.login_status("nonce_pending")

    assert result.status == "pending"
    assert result.access_token is None
    assert result.user is None


def test_login_status_urlencodes_nonce(
    httpx_mock: HTTPXMock, passepartout: Passepartout
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/passepartout/login/status?nonce=a%2Fb+c",
        status_code=200,
        json=_LOGIN_STATUS_PENDING_PAYLOAD,
    )

    passepartout.login_status("a/b c")

    request = httpx_mock.get_request()
    assert request is not None
    assert request.url.params["nonce"] == "a/b c"


# ===========================================================================
# introspect — synchronous
# ===========================================================================


def test_introspect(httpx_mock: HTTPXMock, passepartout: Passepartout) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/tokens/introspect",
        status_code=200,
        json=_INTROSPECT_PAYLOAD,
    )

    result = passepartout.introspect("ppt_test_at_abc123")

    assert isinstance(result, TokenIntrospection)
    assert result.active is True
    assert result.subject == "tg_555"
    assert result.tenant_id == "ten_001"
    assert result.scopes == ["passepartout.login"]
    assert result.expires_at == "2026-03-17T12:00:00Z"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"
    body = json.loads(request.content)
    assert body == {"access_token": "ppt_test_at_abc123"}


# ===========================================================================
# Async variants
# ===========================================================================


async def test_async_login_start(
    httpx_mock: HTTPXMock, async_passepartout: AsyncPassepartout
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/login/start",
        status_code=200,
        json=_LOGIN_START_PAYLOAD,
    )

    result = await async_passepartout.login_start()

    assert isinstance(result, LoginStart)
    assert result.nonce == "nonce_abc123"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


async def test_async_login_status(
    httpx_mock: HTTPXMock, async_passepartout: AsyncPassepartout
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/passepartout/login/status?nonce=nonce_abc123",
        status_code=200,
        json=_LOGIN_STATUS_PAYLOAD,
    )

    result = await async_passepartout.login_status("nonce_abc123")

    assert result.status == "confirmed"
    assert result.access_token == "ppt_test_at_abc123"
    assert isinstance(result.user, TelegramUser)
    assert result.user.username == "durov"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "GET"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"
    assert request.url.params["nonce"] == "nonce_abc123"


async def test_async_introspect(
    httpx_mock: HTTPXMock, async_passepartout: AsyncPassepartout
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/passepartout/tokens/introspect",
        status_code=200,
        json=_INTROSPECT_PAYLOAD,
    )

    result = await async_passepartout.introspect("ppt_test_at_abc123")

    assert isinstance(result, TokenIntrospection)
    assert result.active is True
    assert result.scopes == ["passepartout.login"]

    request = httpx_mock.get_request()
    assert request is not None
    assert request.method == "POST"
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"
    assert json.loads(request.content) == {"access_token": "ppt_test_at_abc123"}
