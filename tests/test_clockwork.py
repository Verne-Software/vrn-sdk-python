"""Tests for the Clockwork resource (sync and async)."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from vernesoft import AsyncClockwork, Clockwork, VerneAPIError
from vernesoft._resources.clockwork._types import CronJob, DelayedJob, Execution

_API_KEY = "vrn_clockwork_test_sk_testkey"
_BASE_URL = "https://api.vernesoft.com"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def clockwork() -> Clockwork:
    return Clockwork(api_key=_API_KEY, base_url=_BASE_URL)


@pytest.fixture()
def async_clockwork() -> AsyncClockwork:
    return AsyncClockwork(api_key=_API_KEY, base_url=_BASE_URL)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CRON_PAYLOAD = {
    "id": "cron_123",
    "tenant_id": "ten_001",
    "name": "nightly-report",
    "schedule": "0 2 * * *",
    "url": "https://example.com/hook",
    "method": "POST",
    "headers": {"X-Api-Key": "secret"},
    "body": '{"kind":"report"}',
    "is_active": True,
    "last_run_at": "2026-07-24T02:00:00Z",
    "next_run_at": "2026-07-25T02:00:00Z",
    "created_at": "2026-07-01T00:00:00Z",
    "updated_at": "2026-07-24T02:00:00Z",
}

_DELAYED_PAYLOAD = {
    "id": "dly_123",
    "tenant_id": "ten_001",
    "name": "welcome-email",
    "run_at": "2026-07-26T09:00:00Z",
    "url": "https://example.com/send",
    "method": "POST",
    "headers": None,
    "body": '{"template":"welcome"}',
    "status": "pending",
    "created_at": "2026-07-25T09:00:00Z",
    "updated_at": "2026-07-25T09:00:00Z",
}

_EXECUTION_PAYLOAD = {
    "id": "exe_123",
    "job_id": "cron_123",
    "status": "success",
    "started_at": "2026-07-24T02:00:00Z",
    "completed_at": "2026-07-24T02:00:01Z",
    "duration_ms": 812,
    "response_status": 200,
    "response_body": "OK",
    "error_message": None,
}


# ===========================================================================
# Cron Jobs — synchronous
# ===========================================================================


def test_jobs_list(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/jobs",
        status_code=200,
        json=[_CRON_PAYLOAD],
    )

    jobs = clockwork.jobs.list()

    assert isinstance(jobs, list)
    assert len(jobs) == 1
    assert isinstance(jobs[0], CronJob)
    assert jobs[0].id == "cron_123"
    assert jobs[0].schedule == "0 2 * * *"
    assert jobs[0].is_active is True

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["Authorization"] == f"Bearer {_API_KEY}"


def test_jobs_create(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/clockwork/jobs",
        status_code=201,
        json=_CRON_PAYLOAD,
    )

    job = clockwork.jobs.create(
        name="nightly-report",
        schedule="0 2 * * *",
        url="https://example.com/hook",
        method="POST",
        body='{"kind":"report"}',
    )

    assert isinstance(job, CronJob)
    assert job.name == "nightly-report"

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content)
    assert body == {
        "name": "nightly-report",
        "schedule": "0 2 * * *",
        "url": "https://example.com/hook",
        "method": "POST",
        "body": '{"kind":"report"}',
    }
    # optional headers omitted when not provided
    assert "headers" not in body


def test_jobs_update(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123",
        status_code=200,
        json={**_CRON_PAYLOAD, "is_active": False},
    )

    job = clockwork.jobs.update("cron_123", is_active=False, schedule="0 3 * * *")

    assert job.is_active is False

    request = httpx_mock.get_request()
    assert request is not None
    # partial PATCH — only provided fields present
    assert json.loads(request.content) == {"is_active": False, "schedule": "0 3 * * *"}


def test_jobs_delete(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123",
        status_code=204,
    )

    result = clockwork.jobs.delete("cron_123")
    assert result is None


def test_jobs_executions(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123/executions",
        status_code=200,
        json=[_EXECUTION_PAYLOAD],
    )

    executions = clockwork.jobs.executions("cron_123")

    assert isinstance(executions, list)
    assert isinstance(executions[0], Execution)
    assert executions[0].id == "exe_123"
    assert executions[0].status == "success"
    assert executions[0].duration_ms == 812
    assert executions[0].response_status == 200


def test_jobs_get_not_found(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/jobs/missing_id",
        status_code=404,
        json={
            "error": {
                "code": "not_found",
                "message": "Cron job not found.",
                "request_id": "req_404",
            }
        },
    )

    with pytest.raises(VerneAPIError) as exc_info:
        clockwork.jobs.delete("missing_id")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "not_found"


# ===========================================================================
# Delayed Jobs — synchronous
# ===========================================================================


def test_delayed_list(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/delayed",
        status_code=200,
        json=[_DELAYED_PAYLOAD],
    )

    jobs = clockwork.delayed.list()

    assert isinstance(jobs, list)
    assert isinstance(jobs[0], DelayedJob)
    assert jobs[0].id == "dly_123"
    assert jobs[0].status == "pending"
    assert jobs[0].headers is None


def test_delayed_create(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/clockwork/delayed",
        status_code=201,
        json=_DELAYED_PAYLOAD,
    )

    job = clockwork.delayed.create(
        name="welcome-email",
        run_at="2026-07-26T09:00:00Z",
        url="https://example.com/send",
        body='{"template":"welcome"}',
    )

    assert isinstance(job, DelayedJob)
    assert job.name == "welcome-email"

    request = httpx_mock.get_request()
    assert request is not None
    assert json.loads(request.content) == {
        "name": "welcome-email",
        "run_at": "2026-07-26T09:00:00Z",
        "url": "https://example.com/send",
        "body": '{"template":"welcome"}',
    }


def test_delayed_cancel(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/delayed/dly_123",
        status_code=204,
    )

    result = clockwork.delayed.cancel("dly_123")
    assert result is None


def test_delayed_executions(httpx_mock: HTTPXMock, clockwork: Clockwork) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/delayed/dly_123/executions",
        status_code=200,
        json=[{**_EXECUTION_PAYLOAD, "job_id": "dly_123"}],
    )

    executions = clockwork.delayed.executions("dly_123")

    assert isinstance(executions[0], Execution)
    assert executions[0].job_id == "dly_123"


# ===========================================================================
# Async variants
# ===========================================================================


async def test_async_jobs_list(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/jobs",
        status_code=200,
        json=[_CRON_PAYLOAD],
    )

    jobs = await async_clockwork.jobs.list()
    assert jobs[0].id == "cron_123"


async def test_async_jobs_create(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/clockwork/jobs",
        status_code=201,
        json=_CRON_PAYLOAD,
    )

    job = await async_clockwork.jobs.create(
        name="nightly-report",
        schedule="0 2 * * *",
        url="https://example.com/hook",
    )
    assert job.name == "nightly-report"


async def test_async_jobs_update(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123",
        status_code=200,
        json={**_CRON_PAYLOAD, "name": "renamed"},
    )

    job = await async_clockwork.jobs.update("cron_123", name="renamed")
    assert job.name == "renamed"
    assert json.loads(httpx_mock.get_request().content) == {"name": "renamed"}


async def test_async_jobs_delete(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123",
        status_code=204,
    )

    result = await async_clockwork.jobs.delete("cron_123")
    assert result is None


async def test_async_jobs_executions(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/jobs/cron_123/executions",
        status_code=200,
        json=[_EXECUTION_PAYLOAD],
    )

    executions = await async_clockwork.jobs.executions("cron_123")
    assert executions[0].status == "success"


async def test_async_delayed_list(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/delayed",
        status_code=200,
        json=[_DELAYED_PAYLOAD],
    )

    jobs = await async_clockwork.delayed.list()
    assert jobs[0].id == "dly_123"


async def test_async_delayed_create(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE_URL}/v1/clockwork/delayed",
        status_code=201,
        json=_DELAYED_PAYLOAD,
    )

    job = await async_clockwork.delayed.create(
        name="welcome-email",
        run_at="2026-07-26T09:00:00Z",
        url="https://example.com/send",
    )
    assert job.name == "welcome-email"


async def test_async_delayed_cancel(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/delayed/dly_123",
        status_code=204,
    )

    result = await async_clockwork.delayed.cancel("dly_123")
    assert result is None


async def test_async_delayed_executions(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/v1/clockwork/delayed/dly_123/executions",
        status_code=200,
        json=[{**_EXECUTION_PAYLOAD, "job_id": "dly_123"}],
    )

    executions = await async_clockwork.delayed.executions("dly_123")
    assert executions[0].job_id == "dly_123"


async def test_async_jobs_not_found(
    httpx_mock: HTTPXMock, async_clockwork: AsyncClockwork
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{_BASE_URL}/v1/clockwork/jobs/missing_id",
        status_code=404,
        json={
            "error": {
                "code": "not_found",
                "message": "Cron job not found.",
                "request_id": "req_404",
            }
        },
    )

    with pytest.raises(VerneAPIError) as exc_info:
        await async_clockwork.jobs.delete("missing_id")

    assert exc_info.value.status == 404
    assert exc_info.value.code == "not_found"
