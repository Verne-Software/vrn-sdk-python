"""Integration suite for 1.5.0: Clockwork time zones, and importing a user with a password
hash, a confirmed address and metadata. Opt-in (``pytest -m integration``), same
environment as ``test_live.py``; it deletes everything it creates.
"""

from __future__ import annotations

import os
import re
import time
from urllib.parse import urlparse

import httpx
import pytest

from vernesoft import AsyncVerne, Verne, VerneAPIError

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

# bcrypt (cost 10) of IMPORTED_PASSWORD — a test value, nothing else.
IMPORTED_PASSWORD = "Imported-Pw-104!"
IMPORTED_HASH = "$2b$10$Ky/GcB0gC9sEpv84tO7.Wuxp7RsfSWrDYtz7M5iU4akOb3O5Y1Kq2"


def at_utc_hour(timestamp: object, hour: int) -> bool:
    return isinstance(timestamp, str) and bool(
        re.search(rf"T{hour:02d}:00:00(\.0+)?(Z|\+00:00)$", timestamp)
    )


def test_a_cron_job_keeps_its_time_zone() -> None:
    verne = Verne(api_key=KEY, base_url=BASE_URL)
    jobs = verne.clockwork.jobs
    job = jobs.create(
        name=f"{PREFIX}-tz",
        schedule="0 9 * * *",
        url="https://example.com/hooks/tz",
        method="GET",
        timezone="Europe/Paris",
    )
    try:
        assert job.timezone == "Europe/Paris"
        # 09:00 in Paris in October (CEST, UTC+2) is 07:00 UTC.
        assert at_utc_hour(job.next_run_at, 7), job.next_run_at

        listed = [j for j in jobs.list() if j.id == job.id]
        assert listed[0].timezone == "Europe/Paris"

        moved = jobs.update(job.id, timezone="America/New_York")
        assert moved.timezone == "America/New_York"
        # 09:00 in New York in October (EDT, UTC-4) is 13:00 UTC.
        assert at_utc_hour(moved.next_run_at, 13), moved.next_run_at
    finally:
        jobs.delete(job.id)


async def test_async_a_job_without_a_zone_is_utc_and_an_unknown_zone_is_400() -> None:
    jobs = AsyncVerne(api_key=KEY, base_url=BASE_URL).clockwork.jobs
    job = await jobs.create(
        name=f"{PREFIX}-utc", schedule="0 9 * * *", url="https://example.com/hooks/utc"
    )
    try:
        assert job.timezone == "UTC"
        with pytest.raises(VerneAPIError) as exc_info:
            await jobs.update(job.id, timezone="Mars/Olympus")
        assert exc_info.value.status == 400
        assert exc_info.value.code == "invalid_payload"
    finally:
        await jobs.delete(job.id)


def test_an_imported_user_is_confirmed_keeps_metadata_and_signs_in() -> None:
    gate = Verne(api_key=KEY, base_url=BASE_URL).gate
    email = f"{PREFIX}-import@e2e.soft.com"
    identity = gate.identities.create(
        traits={"email": email},
        credentials={"password": {"config": {"hashed_password": IMPORTED_HASH}}},
        email_verified=True,
        metadata_public={"previous_user_id": "auth0|sdk-104"},
    )
    try:
        assert identity.verifiable_addresses[0]["verified"] is True
        assert identity.verifiable_addresses[0]["status"] == "completed"
        assert identity.metadata_public == {"previous_user_id": "auth0|sdk-104"}
        assert gate.identities.get(identity.id).verifiable_addresses[0]["verified"] is True

        flow = gate.create_login_flow()
        res = httpx.post(
            flow["ui"]["action"],
            headers={"Accept": "application/json"},
            json={"method": "password", "identifier": email, "password": IMPORTED_PASSWORD},
            timeout=30,
        )
        assert res.status_code == 200, "login with the original password"
        assert res.json().get("session_token")
    finally:
        gate.identities.delete(identity.id)
