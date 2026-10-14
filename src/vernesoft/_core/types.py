from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Paginated(Generic[T]):
    """One page of a cursor-paged list.

    Pass ``next_cursor`` back as ``cursor`` while ``has_more`` is ``True``;
    ``next_cursor`` is ``None`` on the last page — loop on ``has_more``, not on an
    empty ``data``.
    """

    data: List[T]
    has_more: bool
    next_cursor: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], item: Callable[[Dict[str, Any]], T]) -> "Paginated[T]":
        return cls(
            data=[item(x) for x in data.get("data") or []],
            has_more=bool(data.get("has_more", False)),
            next_cursor=data.get("next_cursor"),
        )


class NotGiven:
    """Type of :data:`NOT_GIVEN`: "this argument was not passed" as distinct from
    ``None``, which is sent as JSON ``null``."""

    _instance: Optional["NotGiven"] = None

    def __new__(cls) -> "NotGiven":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"


#: Default of an argument where leaving it out and passing ``None`` mean different
#: things — e.g. ``members.update(expires_at=…)``: left out keeps the deadline, ``None``
#: removes it.
NOT_GIVEN = NotGiven()
