from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import CronJob, Execution

_PATH_JOBS = "/v1/clockwork/jobs"


class JobsResource:
    """Synchronous Clockwork cron job operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def list(self) -> List[CronJob]:
        """Return all cron jobs for the tenant."""
        data = self._http.get(_PATH_JOBS)
        return [CronJob.from_dict(x) for x in data]

    def create(
        self,
        *,
        name: str,
        schedule: str,
        url: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
    ) -> CronJob:
        """Create a new cron job."""
        payload: Dict[str, Any] = {
            "name": name,
            "schedule": schedule,
            "url": url,
        }
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        data = self._http.post(_PATH_JOBS, body=payload)
        return CronJob.from_dict(data)

    def update(
        self,
        job_id: str,
        *,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> CronJob:
        """Partially update a cron job — only provided fields are changed."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if schedule is not None:
            payload["schedule"] = schedule
        if url is not None:
            payload["url"] = url
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        if is_active is not None:
            payload["is_active"] = is_active
        data = self._http.patch(f"{_PATH_JOBS}/{job_id}", body=payload)
        return CronJob.from_dict(data)

    def delete(self, job_id: str) -> None:
        """Delete a cron job."""
        self._http.delete(f"{_PATH_JOBS}/{job_id}")

    def executions(self, job_id: str) -> List[Execution]:
        """Return the execution history for a cron job."""
        data = self._http.get(f"{_PATH_JOBS}/{job_id}/executions")
        return [Execution.from_dict(x) for x in data]


class AsyncJobsResource:
    """Asynchronous Clockwork cron job operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self) -> List[CronJob]:
        """Return all cron jobs for the tenant."""
        data = await self._http.get(_PATH_JOBS)
        return [CronJob.from_dict(x) for x in data]

    async def create(
        self,
        *,
        name: str,
        schedule: str,
        url: str,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
    ) -> CronJob:
        """Create a new cron job."""
        payload: Dict[str, Any] = {
            "name": name,
            "schedule": schedule,
            "url": url,
        }
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        data = await self._http.post(_PATH_JOBS, body=payload)
        return CronJob.from_dict(data)

    async def update(
        self,
        job_id: str,
        *,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> CronJob:
        """Partially update a cron job — only provided fields are changed."""
        payload: Dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if schedule is not None:
            payload["schedule"] = schedule
        if url is not None:
            payload["url"] = url
        if method is not None:
            payload["method"] = method
        if headers is not None:
            payload["headers"] = headers
        if body is not None:
            payload["body"] = body
        if is_active is not None:
            payload["is_active"] = is_active
        data = await self._http.patch(f"{_PATH_JOBS}/{job_id}", body=payload)
        return CronJob.from_dict(data)

    async def delete(self, job_id: str) -> None:
        """Delete a cron job."""
        await self._http.delete(f"{_PATH_JOBS}/{job_id}")

    async def executions(self, job_id: str) -> List[Execution]:
        """Return the execution history for a cron job."""
        data = await self._http.get(f"{_PATH_JOBS}/{job_id}/executions")
        return [Execution.from_dict(x) for x in data]
