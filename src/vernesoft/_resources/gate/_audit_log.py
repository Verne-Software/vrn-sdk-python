from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from ..._core.http import AsyncHttpClient, QueryValue, SyncHttpClient
from ..._core.types import Paginated
from ._types import AuditLogEntry

_PATH_AUDIT_LOG = "/v1/gate/audit-log"

Instant = Union[str, datetime]


def _query(
    limit: Optional[int],
    cursor: Optional[str],
    action: Optional[str],
    actor_id: Optional[str],
    actor_type: Optional[str],
    target_id: Optional[str],
    from_: Optional[Instant],
    to: Optional[Instant],
) -> dict[str, QueryValue]:
    return {
        "limit": limit,
        "cursor": cursor,
        "action": action,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "target_id": target_id,
        "from": from_,
        "to": to,
    }


class AuditLogResource:
    """The account's audit log, read-only: who did what, to what, when and from where.

    **Any key with the ``gate`` scope reads the whole log, including the IP addresses
    and user agents of your team members.** Keep ``gate`` keys on your backend.
    """

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        target_id: Optional[str] = None,
        from_: Optional[Instant] = None,
        to: Optional[Instant] = None,
    ) -> Paginated[AuditLogEntry]:
        """One page of entries, newest first. Filters combine; keep the same filters while
        paging with ``cursor``.

        :param action: one action, e.g. ``"identity.login"``,
            ``"organization.member_added"``. An unknown action is ``400``.
        :param actor_type: ``team_member``, ``api_key``, ``end_user``, ``system`` or
            ``staff``.
        :param from_: entries at or after this instant (the query parameter ``from``;
            ``from`` is a Python keyword).
        :param to: entries before this instant; must be later than ``from_``.
        """
        data = self._http.get(
            _PATH_AUDIT_LOG,
            params=_query(limit, cursor, action, actor_id, actor_type, target_id, from_, to),
        )
        return Paginated.from_dict(data, AuditLogEntry.from_dict)


class AsyncAuditLogResource:
    """The account's audit log (async). See :class:`AuditLogResource` — the same warning
    about team members' IPs applies."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_type: Optional[str] = None,
        target_id: Optional[str] = None,
        from_: Optional[Instant] = None,
        to: Optional[Instant] = None,
    ) -> Paginated[AuditLogEntry]:
        """One page of entries, newest first. See :meth:`AuditLogResource.list`."""
        data = await self._http.get(
            _PATH_AUDIT_LOG,
            params=_query(limit, cursor, action, actor_id, actor_type, target_id, from_, to),
        )
        return Paginated.from_dict(data, AuditLogEntry.from_dict)
