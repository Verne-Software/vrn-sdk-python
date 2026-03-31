from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Paginated(Generic[T]):
    """Generic paginated response container."""

    data: List[T]
    has_more: bool
    next_cursor: Optional[str] = None
