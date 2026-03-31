"""Tests for the Relay resource (sync and async)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncRelay, Relay, VerneAPIError
from vernesoft._resources.relay._types import ListMessagesResponse, Message

_API_KEY = "vrn_relay_test_sk_testkey"
_BASE_URL = "https://api.vernesoft.com"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def relay() -> Relay:
    return Relay(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_relay() -> AsyncRelay:
    return AsyncRelay(api_key=_API_KEY, base_url=_BASE_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MSG_PAYLOAD = {
    "id": "msg_2hV9kLmNpQ",
    "event_type": "user.created",
    "status": "accepted",
    "timestamp": "2026-03-17T12:00:00Z",
}

_LIST_PAYLOAD = {
    "data": [_MSG_PAYLOAD],
    "has_more": True,
    "next_cursor": "cursor_abc",
}


# ===========================================================================
# send() — synchronous
# ===========================================================================


def test_send_success(httpx_mock: HTTPXMock, relay: Relay) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    msg = relay.messages.send(
        event_type="user.created",
        payload={"id": "123"},
        idempotency_key="evt_abc",
        channels=["team-a"],
    )

    assert isinstance(msg, Message)
    assert msg.id == "msg_2hV9kLmNpQ"
    assert msg.event_type == "user.created"
    assert msg.status == "accepted"
    assert msg.timestamp == "2026-03-17T12:00:00Z"

    # Verify auth header was sent
    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


def test_send_400_error(httpx_mock: HTTPXMock, relay: Relay) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=400,
        json={
            "error": {
                "code": "invalid_payload",
                "message": "Field 'event_type' is required.",
                "request_id": "req_abc123",
            }
        },
    )

    with pytest.raises(VerneAPIError) as exc_info:
        relay.messages.send(event_type="", payload={})

    err = exc_info.value
    assert err.status == 400
    assert err.code == "invalid_payload"
    assert err.request_id == "req_abc123"
    assert "event_type" in str(err)


def test_send_409_duplicate(httpx_mock: HTTPXMock, relay: Relay) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=409,
        json={
            "error": {
                "code": "duplicate_idempotency_key",
                "message": "Event already processed.",
                "request_id": "req_dup",
            }
        },
    )

    with pytest.raises(VerneAPIError) as exc_info:
        relay.messages.send(event_type="user.created", payload={}, idempotency_key="dup_key")

    assert exc_info.value.status == 409
    assert exc_info.value.code == "duplicate_idempotency_key"


def test_send_429_retries_and_succeeds(httpx_mock: HTTPXMock, relay: Relay) -> None:
    # First attempt: 429 with Retry-After
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=429,
        headers={"Retry-After": "0"},
        json={"error": {"code": "rate_limited", "message": "slow down", "request_id": "req_rl"}},
    )
    # Second attempt: 202 success
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    msg = relay.messages.send(event_type="user.created", payload={"id": "123"})
    assert msg.id == "msg_2hV9kLmNpQ"


def test_send_429_retry_still_fails(httpx_mock: HTTPXMock, relay: Relay) -> None:
    """When both the initial call and the retry return 429, raise VerneAPIError."""
    for _ in range(2):
        httpx_mock.add_response(
            method="POST",
            url=f"{_BASE_URL}/v1/relay/messages",
            status_code=429,
            headers={"Retry-After": "0"},
            json={
                "error": {
                    "code": "rate_limited",
                    "message": "still too fast",
                    "request_id": "req_rl2",
                }
            },
        )

    with pytest.raises(VerneAPIError) as exc_info:
        relay.messages.send(event_type="user.created", payload={})

    assert exc_info.value.status == 429


# ===========================================================================
# list() — synchronous
# ===========================================================================


def test_list_no_filters(httpx_mock: HTTPXMock, relay: Relay) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/relay/messages?limit=20",
        status_code=200,
        json=_LIST_PAYLOAD,
    )

    page = relay.messages.list()

    assert isinstance(page, ListMessagesResponse)
    assert page.has_more is True
    assert page.next_cursor == "cursor_abc"
    assert len(page.data) == 1
    assert page.data[0].id == "msg_2hV9kLmNpQ"


def test_list_with_filters(httpx_mock: HTTPXMock, relay: Relay) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/relay/messages?limit=5&cursor=cursor_abc&event_type=user.created",
        status_code=200,
        json={
            "data": [],
            "has_more": False,
            "next_cursor": None,
        },
    )

    page = relay.messages.list(limit=5, cursor="cursor_abc", event_type="user.created")
    assert page.has_more is False
    assert page.next_cursor is None
    assert page.data == []


def test_list_pagination_cursor(httpx_mock: HTTPXMock, relay: Relay) -> None:
    """list() with a cursor parameter returns the next page."""
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/relay/messages?limit=20&cursor=cur_1",
        status_code=200,
        json={
            "data": [_MSG_PAYLOAD],
            "has_more": False,
            "next_cursor": None,
        },
    )

    page = relay.messages.list(cursor="cur_1")
    assert page.has_more is False
    assert len(page.data) == 1


# ===========================================================================
# Async variants
# ===========================================================================


async def test_async_send_success(httpx_mock: HTTPXMock, async_relay: AsyncRelay) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    msg = await async_relay.messages.send(event_type="user.created", payload={"id": "123"})
    assert msg.id == "msg_2hV9kLmNpQ"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


async def test_async_send_429_retries(httpx_mock: HTTPXMock, async_relay: AsyncRelay) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=429,
        headers={"Retry-After": "0"},
        json={"error": {"code": "rate_limited", "message": "slow", "request_id": "rq"}},
    )
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/relay/messages",
        status_code=202,
        json=_MSG_PAYLOAD,
    )

    msg = await async_relay.messages.send(event_type="user.created", payload={})
    assert msg.id == "msg_2hV9kLmNpQ"


async def test_async_list(httpx_mock: HTTPXMock, async_relay: AsyncRelay) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/relay/messages?limit=10",
        status_code=200,
        json=_LIST_PAYLOAD,
    )

    page = await async_relay.messages.list(limit=10)
    assert page.has_more is True
    assert len(page.data) == 1
