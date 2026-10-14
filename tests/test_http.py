"""Tests for the HTTP layer: error parsing, the 429 retry rule, queries and paths."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import List

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncRelay, Clockwork, Gate, Relay, VerneAPIError
from vernesoft._core import http as http_module
from vernesoft._core.http import build_query, parse_retry_after, rfc3339, seg

_API_KEY = "vrn_9f8a7c2d1e0b4a6f"
_BASE_URL = "https://api.vernesoft.com"
_MESSAGES = f"{_BASE_URL}/v1/relay/messages"

_MSG = {
    "id": "msg_1",
    "event_type": "user.created",
    "status": "accepted",
    "timestamp": "2026-03-17T12:00:00Z",
}


@pytest.fixture()
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """Record the client's waits instead of sleeping."""
    recorded: List[float] = []

    def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    async def fake_async_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(http_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(http_module.asyncio, "sleep", fake_async_sleep)
    return recorded


def _send(relay: Relay) -> None:
    relay.messages.send(event_type="user.created", payload={"id": "usr_1"})


# ===========================================================================
# Error parsing
# ===========================================================================


def test_envelope_with_extra_members_goes_to_details(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_MESSAGES,
        status_code=402,
        json={
            "error": {
                "code": "UPGRADE_REQUIRED",
                "message": "Your plan is over its limit.",
                "request_id": "req_42",
                "plan": "free",
                "limit": 1000,
                "current": 1000,
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    err = exc_info.value
    assert err.status == 402
    assert err.code == "UPGRADE_REQUIRED"
    assert str(err) == "Your plan is over its limit."
    assert err.message == "Your plan is over its limit."
    assert err.request_id == "req_42"
    assert err.details == {"plan": "free", "limit": 1000, "current": 1000}
    assert err.body["error"]["code"] == "UPGRADE_REQUIRED"


def test_402_is_never_retried(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_MESSAGES,
        status_code=402,
        headers={"Retry-After": "1"},
        json={"error": {"code": "payment_required", "message": "Pay", "request_id": "r"}},
    )
    with pytest.raises(VerneAPIError) as exc_info:
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert exc_info.value.status == 402
    assert exc_info.value.retry_after == 1.0
    assert sleeps == []
    assert len(httpx_mock.get_requests()) == 1


def test_string_error_keeps_its_sentence(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/clockwork/jobs",
        status_code=400,
        json={"error": "Invalid cron schedule. Expected five fields."},
    )
    clockwork = Clockwork(api_key=_API_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneAPIError) as exc_info:
        clockwork.jobs.create(name="x", schedule="nope", url="https://example.com")
    err = exc_info.value
    assert err.code == "unknown"
    assert err.message == "Invalid cron schedule. Expected five fields."
    assert err.request_id is None
    assert err.details == {}


def test_numeric_kratos_code_is_never_used(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/gate/identities/id_1/sessions",
        status_code=404,
        json={
            "error": {
                "code": 404,
                "status": "Not Found",
                "message": "Unable to locate the resource",
            }
        },
    )
    gate = Gate(api_key=_API_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneAPIError) as exc_info:
        gate.sessions.revoke_all("id_1")
    err = exc_info.value
    assert err.status == 404
    assert err.code == "unknown"
    assert err.message == "Unable to locate the resource"
    assert err.details == {"status": "Not Found"}
    assert err.request_id is None


def test_envelope_without_request_id(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/gate/tokens",
        status_code=400,
        json={"error": {"code": "invalid_request", "message": "subject is required"}},
    )
    with pytest.raises(VerneAPIError) as exc_info:
        Gate(api_key=_API_KEY, base_url=_BASE_URL).tokens.create(subject="")
    assert exc_info.value.code == "invalid_request"
    assert exc_info.value.request_id is None


def test_forbidden_scope_envelope(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/organizations",
        status_code=403,
        json={
            "error": {
                "code": "forbidden",
                "message": "This API key is not authorized for Gate.",
                "request_id": "req_9",
            }
        },
    )
    with pytest.raises(VerneAPIError) as exc_info:
        Gate(api_key=_API_KEY, base_url=_BASE_URL).organizations.list()
    assert exc_info.value.code == "forbidden"
    assert exc_info.value.request_id == "req_9"


def test_non_json_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET", url=f"{_MESSAGES}?limit=20", status_code=502, text="<html>Bad gateway"
    )
    with pytest.raises(VerneAPIError) as exc_info:
        Relay(api_key=_API_KEY, base_url=_BASE_URL).messages.list()
    err = exc_info.value
    assert err.status == 502
    assert err.code == "unknown"
    assert err.message == "HTTP 502"
    assert err.body is None


def test_validation_detail_list(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="POST",
        url=_MESSAGES,
        status_code=422,
        json={"detail": [{"msg": "field required"}, {"msg": "bad type"}]},
    )
    with pytest.raises(VerneAPIError) as exc_info:
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert exc_info.value.message == "field required; bad type"
    assert exc_info.value.code == "unknown"


def test_error_shapes_that_are_not_objects() -> None:
    for body in (None, [], "text", 7, {"error": None}, {"error": {"code": None}}):
        err = VerneAPIError.from_response(500, body)
        assert err.code == "unknown"
        assert err.message == "HTTP 500"
        assert err.details == {}


def test_positional_constructor_still_works() -> None:
    err = VerneAPIError("not_found", "Nope", 404, "req_1")
    assert (err.code, err.status, err.request_id, err.details) == ("not_found", 404, "req_1", {})
    assert VerneAPIError("x", "y", 500).request_id is None


# ===========================================================================
# 429
# ===========================================================================


def _rate_limited(httpx_mock: HTTPXMock, code: str, retry_after: str | None) -> None:
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    httpx_mock.add_response(
        method="POST",
        url=_MESSAGES,
        status_code=429,
        headers=headers,
        json={"error": {"code": code, "message": "Slow down", "request_id": "req_rl"}},
    )


def test_short_429_is_retried_once(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    _rate_limited(httpx_mock, "rate_limited", "2")
    httpx_mock.add_response(method="POST", url=_MESSAGES, status_code=202, json=_MSG)
    _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert sleeps == [2.0]


def test_429_without_retry_after_waits_one_second(
    httpx_mock: HTTPXMock, sleeps: List[float]
) -> None:
    _rate_limited(httpx_mock, "rate_limited", None)
    httpx_mock.add_response(method="POST", url=_MESSAGES, status_code=202, json=_MSG)
    _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert sleeps == [1.0]


def test_429_at_exactly_60_seconds_is_retried(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    _rate_limited(httpx_mock, "rate_limited", "60")
    httpx_mock.add_response(method="POST", url=_MESSAGES, status_code=202, json=_MSG)
    _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert sleeps == [60.0]


def test_long_429_is_raised_at_once(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    _rate_limited(httpx_mock, "rate_limited", "61")
    with pytest.raises(VerneAPIError) as exc_info:
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert exc_info.value.status == 429
    assert exc_info.value.retry_after == 61.0
    assert sleeps == []
    assert len(httpx_mock.get_requests()) == 1


def test_relay_monthly_limit_is_raised_at_once(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    _rate_limited(httpx_mock, "RELAY_MESSAGE_LIMIT_REACHED", "1209600")
    with pytest.raises(VerneAPIError) as exc_info:
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert exc_info.value.code == "RELAY_MESSAGE_LIMIT_REACHED"
    assert exc_info.value.retry_after == 1209600.0
    assert sleeps == []


def test_relay_monthly_limit_with_short_retry_after_is_not_retried(
    httpx_mock: HTTPXMock, sleeps: List[float]
) -> None:
    _rate_limited(httpx_mock, "RELAY_MESSAGE_LIMIT_REACHED", "5")
    with pytest.raises(VerneAPIError):
        _send(Relay(api_key=_API_KEY, base_url=_BASE_URL))
    assert sleeps == []


def test_get_429_is_not_retried(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_MESSAGES}?limit=20",
        status_code=429,
        headers={"Retry-After": "1"},
        json={"error": {"code": "rate_limited", "message": "Slow", "request_id": "r"}},
    )
    with pytest.raises(VerneAPIError):
        Relay(api_key=_API_KEY, base_url=_BASE_URL).messages.list()
    assert sleeps == []


async def test_async_monthly_limit_is_raised_at_once(
    httpx_mock: HTTPXMock, sleeps: List[float]
) -> None:
    _rate_limited(httpx_mock, "RELAY_MESSAGE_LIMIT_REACHED", "1209600")
    relay = AsyncRelay(api_key=_API_KEY, base_url=_BASE_URL)
    with pytest.raises(VerneAPIError) as exc_info:
        await relay.messages.send(event_type="user.created", payload={})
    assert exc_info.value.retry_after == 1209600.0
    assert sleeps == []


async def test_async_short_429_is_retried(httpx_mock: HTTPXMock, sleeps: List[float]) -> None:
    _rate_limited(httpx_mock, "rate_limited", "3")
    httpx_mock.add_response(method="POST", url=_MESSAGES, status_code=202, json=_MSG)
    relay = AsyncRelay(api_key=_API_KEY, base_url=_BASE_URL)
    await relay.messages.send(event_type="user.created", payload={})
    assert sleeps == [3.0]


# ===========================================================================
# Helpers
# ===========================================================================


def test_parse_retry_after() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("120") == 120.0
    assert parse_retry_after("1.5") == 1.5
    assert parse_retry_after("-3") is None
    assert parse_retry_after("soon") is None
    later = datetime.now(timezone.utc) + timedelta(seconds=90)
    parsed = parse_retry_after(format_datetime(later, usegmt=True))
    assert parsed is not None and 85 <= parsed <= 91


def test_build_query_drops_unset_and_formats() -> None:
    query = build_query(
        {
            "limit": 5,
            "cursor": None,
            "flag": True,
            "from": datetime(2026, 10, 14, 9, 30, tzinfo=timezone.utc),
            "to": datetime(2026, 10, 14, 11, 30, tzinfo=timezone(timedelta(hours=2))),
        }
    )
    assert query == {
        "limit": "5",
        "flag": "true",
        "from": "2026-10-14T09:30:00Z",
        "to": "2026-10-14T09:30:00Z",
    }
    assert build_query({"a": None}) is None


def test_rfc3339_treats_naive_as_utc() -> None:
    assert rfc3339(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05Z"
    assert rfc3339("2026-01-02T03:04:05Z") == "2026-01-02T03:04:05Z"


def test_seg_encodes_path_characters() -> None:
    assert seg("a/b?c#d") == "a%2Fb%3Fc%23d"
    assert seg("8c1d3f0e-0000-4000-8000-000000000000") == "8c1d3f0e-0000-4000-8000-000000000000"


def test_ids_are_url_encoded_in_paths(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/gate/identities/a%2F..%2Fb",
        json={"id": "x", "schema_id": "user", "state": "active", "traits": {}},
    )
    Gate(api_key=_API_KEY, base_url=_BASE_URL).identities.get("a/../b")
