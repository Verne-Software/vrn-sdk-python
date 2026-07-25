from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CronJob:
    """A recurring Clockwork cron job."""

    id: str
    tenant_id: str
    name: str
    schedule: str
    url: str
    method: str
    headers: Optional[Dict[str, Any]]
    body: Optional[str]
    is_active: bool
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CronJob":
        return cls(
            id=data["id"],
            tenant_id=data["tenant_id"],
            name=data["name"],
            schedule=data["schedule"],
            url=data["url"],
            method=data["method"],
            headers=data.get("headers"),
            body=data.get("body"),
            is_active=data["is_active"],
            last_run_at=data.get("last_run_at"),
            next_run_at=data.get("next_run_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(frozen=True)
class DelayedJob:
    """A one-shot Clockwork job scheduled to run at a future time."""

    id: str
    tenant_id: str
    name: str
    run_at: str
    url: str
    method: str
    headers: Optional[Dict[str, Any]]
    body: Optional[str]
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelayedJob":
        return cls(
            id=data["id"],
            tenant_id=data["tenant_id"],
            name=data["name"],
            run_at=data["run_at"],
            url=data["url"],
            method=data["method"],
            headers=data.get("headers"),
            body=data.get("body"),
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass(frozen=True)
class Execution:
    """A single execution record of a cron or delayed job."""

    id: str
    job_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    response_status: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Execution":
        return cls(
            id=data["id"],
            job_id=data["job_id"],
            status=data["status"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms"),
            response_status=data.get("response_status"),
            response_body=data.get("response_body"),
            error_message=data.get("error_message"),
        )
