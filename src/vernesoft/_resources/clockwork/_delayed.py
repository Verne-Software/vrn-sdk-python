from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import DelayedJob, Execution

_PATH_DELAYED = "/v1/clockwork/delayed"


class DelayedResource:
    """Synchronous Clockwork delayed (one-shot) job operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def list(self) -> List[DelayedJob]:
        """Return all delayed jobs for the tenant."""
        data = self._http.get(_PATH_DELAYED)
        return [DelayedJob.from_dict(x) for x in data]

    def create(
        self,
        *,
        name: str,
        run_at: str,
        url: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
    ) -> DelayedJob:
        """Schedule a new delayed job to run once at ``run_at``."""
        payload: Dict[str, Any] = {
            "name": name,
            "run_at": run_at,
            "url": url,
        }
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        data = self._http.post(_PATH_DELAYED, body=payload)
        return DelayedJob.from_dict(data)

    def cancel(self, job_id: str) -> None:
        """Cancel a pending delayed job."""
        self._http.delete(f"{_PATH_DELAYED}/{job_id}")

    def executions(self, job_id: str) -> List[Execution]:
        """Return the execution history for a delayed job."""
        data = self._http.get(f"{_PATH_DELAYED}/{job_id}/executions")
        return [Execution.from_dict(x) for x in data]


class AsyncDelayedResource:
    """Asynchronous Clockwork delayed (one-shot) job operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self) -> List[DelayedJob]:
        """Return all delayed jobs for the tenant."""
        data = await self._http.get(_PATH_DELAYED)
        return [DelayedJob.from_dict(x) for x in data]

    async def create(
        self,
        *,
        name: str,
        run_at: str,
        url: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
    ) -> DelayedJob:
        """Schedule a new delayed job to run once at ``run_at``."""
        payload: Dict[str, Any] = {
            "name": name,
            "run_at": run_at,
            "url": url,
        }
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        data = await self._http.post(_PATH_DELAYED, body=payload)
        return DelayedJob.from_dict(data)

    async def cancel(self, job_id: str) -> None:
        """Cancel a pending delayed job."""
        await self._http.delete(f"{_PATH_DELAYED}/{job_id}")

    async def executions(self, job_id: str) -> List[Execution]:
        """Return the execution history for a delayed job."""
        data = await self._http.get(f"{_PATH_DELAYED}/{job_id}/executions")
        return [Execution.from_dict(x) for x in data]
