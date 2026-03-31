from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Message:
    """A relay message (sent event)."""

    id: str
    event_type: str
    status: str
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            id=data["id"],
            event_type=data["event_type"],
            status=data["status"],
            timestamp=data["timestamp"],
        )


@dataclass(frozen=True)
class ListMessagesResponse:
    """Paginated list of relay messages."""

    data: List[Message]
    has_more: bool
    next_cursor: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ListMessagesResponse":
        return cls(
            data=[Message.from_dict(m) for m in data.get("data", [])],
            has_more=data["has_more"],
            next_cursor=data.get("next_cursor"),
        )
