from __future__ import annotations

from typing import Any, List

from ..._core.http import AsyncHttpClient, SyncHttpClient, seg
from ._types import Session, SessionCheck

_PATH_SESSION_CHECK = "/v1/gate/auth/session"


def _identity_sessions_path(identity_id: str) -> str:
    return f"/v1/gate/identities/{seg(identity_id)}/sessions"


def _session_path(session_id: str) -> str:
    return f"/v1/gate/sessions/{seg(session_id)}"


def _sessions(data: Any) -> List[Session]:
    return [Session.from_dict(s) for s in data or [] if isinstance(s, dict)]


class SessionsResource:
    """End users' sessions: list, revoke, and check one is good enough to act on."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def list(self, identity_id: str) -> List[Session]:
        """The active sessions of one of your end users (not paged). Another tenant's user
        is ``403 forbidden``."""
        return _sessions(self._http.get(_identity_sessions_path(identity_id)))

    def revoke_all(self, identity_id: str) -> None:
        """Revoke every session of an end user — "log out everywhere". Signed tokens
        already issued keep verifying until their own ``exp`` (at most 15 minutes).

        Note: the API answers ``404`` (raised as :class:`VerneAPIError`, code
        ``unknown``) when the user has no session at all.
        """
        self._http.delete(_identity_sessions_path(identity_id))

    def revoke(self, session_id: str) -> None:
        """Revoke one session by its id. Revoking an already revoked session of your user
        succeeds again; an id that is not one of your users' sessions is ``404``."""
        self._http.delete(_session_path(session_id))

    def check(self, session_token: str) -> SessionCheck:
        """Whether an end user's session meets what your tenant requires — the one call
        to gate your own routes on. Gate on ``mfa_satisfied``. Also lists the user's
        organizations in the key's project, read now.

        Raises :class:`VerneAPIError` with ``status 401`` for a dead, foreign or unknown
        session, and ``code "mfa_required"`` (``403``, ``details["required_aal"]``) when
        a second factor is owed: start a step-up flow with
        ``gate.create_login_flow(aal="aal2", session_token=…)``.
        """
        data = self._http.get(_PATH_SESSION_CHECK, session_token=session_token)
        return SessionCheck.from_dict(data)


class AsyncSessionsResource:
    """End users' sessions (async). See :class:`SessionsResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list(self, identity_id: str) -> List[Session]:
        """The active sessions of one of your end users (not paged)."""
        return _sessions(await self._http.get(_identity_sessions_path(identity_id)))

    async def revoke_all(self, identity_id: str) -> None:
        """Revoke every session of an end user. ``404`` when the user has none."""
        await self._http.delete(_identity_sessions_path(identity_id))

    async def revoke(self, session_id: str) -> None:
        """Revoke one session by its id (idempotent for your users' sessions)."""
        await self._http.delete(_session_path(session_id))

    async def check(self, session_token: str) -> SessionCheck:
        """Whether a session meets what your tenant requires. See
        :meth:`SessionsResource.check`."""
        data = await self._http.get(_PATH_SESSION_CHECK, session_token=session_token)
        return SessionCheck.from_dict(data)
