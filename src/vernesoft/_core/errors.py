from __future__ import annotations

from typing import Any, Dict, Literal, Optional

#: The ``reason`` of a ``404 not_found`` or a ``409 conflict`` on the organization routes,
#: in :attr:`VerneAPIError.reason`:
#:
#: - ``404``: ``organization`` (no such organization in the key's project), ``role`` (no
#:   such role in it), ``member`` (the person is not a member), ``end_user``
#:   (``identity_id`` is not one of your end users), ``project`` (no such project);
#: - ``409``: ``role_name_taken`` (the organization already has a role with that name),
#:   ``role_held`` (someone holds the role, so it cannot be deleted), ``already_member``.
#:
#: The set is open: keep a branch for a reason you do not know. A role limit hit is
#: ``409 limit_reached``, with no reason.
ErrorReason = Literal[
    "organization",
    "role",
    "member",
    "end_user",
    "project",
    "role_name_taken",
    "role_held",
    "already_member",
]

#: Why a signed token was refused (see :class:`VerneTokenError`).
TokenErrorReason = Literal[
    "malformed",
    "unsupported_alg",
    "unknown_kid",
    "bad_signature",
    "wrong_issuer",
    "expired",
    "not_yet_valid",
    "missing_claim",
    "jwks_unavailable",
]


class VerneError(Exception):
    """Base exception for all Verne SDK errors (network, timeout, configuration, …)."""


class VerneAPIError(VerneError):
    """Raised when the API answers with an error status.

    Branch on ``status`` and ``code``. Codes are an open set of strings — compare against
    the ones you handle and treat the rest generically. Every API route answers with the
    envelope ``{"error": {"code", "message", "request_id"}}``; ``code`` is ``"unknown"``
    only for a body in another shape, read as a fallback — the string form Clockwork
    used before October 2026, an identity-service body with a numeric code (still what
    Kratos' own ``/auth/*`` self-service routes answer), a body that is not JSON.

    :ivar code: machine-readable code, e.g. ``"invalid_payload"``, ``"forbidden"``,
        ``"conflict"``, ``"mfa_required"``, ``"ACTIVE_USER_LIMIT_REACHED"``.
    :ivar status: HTTP status code.
    :ivar request_id: the request id to quote to support, or ``None`` when the response
        did not carry one.
    :ivar details: the members of ``error`` other than ``code``, ``message`` and
        ``request_id`` — e.g. ``plan``/``limit``/``current`` on a ``402``, ``kind`` on a
        Clockwork limit, ``required_aal``/``current_aal`` on ``403 mfa_required``. Empty
        when there are none.
    :ivar reason: which one of its kind the error is, when the API says: on the
        organization routes a ``404 not_found`` names what was not found and a
        ``409 conflict`` why it is one (see :data:`ErrorReason`). ``code`` is unchanged, so
        code that ignores ``reason`` behaves as before. ``None`` when the error has none,
        and for a body that is not the API's envelope. The same value stays in
        ``details["reason"]``.
    :ivar retry_after: seconds from the ``Retry-After`` header when the response had one.
        On ``429 RELAY_MESSAGE_LIMIT_REACHED`` it runs to the 1st of next month.
    :ivar body: the raw parsed response body (``None`` when it was not JSON), kept so an
        unrecognised shape stays diagnosable.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        request_id: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None,
        body: Any = None,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.request_id = request_id
        self.details: Dict[str, Any] = dict(details) if details else {}
        self.retry_after = retry_after
        self.body = body
        self.reason: Optional[str] = reason

    @classmethod
    def from_response(
        cls, status: int, body: Any, retry_after: Optional[float] = None
    ) -> "VerneAPIError":
        """Build an error from a parsed response body of *unknown* shape.

        The documented envelope is ``{"error": {"code", "message", "request_id", …}}``,
        but an engine or a pass-through can answer differently: Clockwork's
        ``{"error": "<sentence>"}``, an identity-service body whose ``code`` is a number.
        Anything unrecognised degrades to code ``"unknown"`` and message
        ``HTTP <status>`` — the error path never raises on its own. ``reason`` is read only
        from the envelope proper (a string ``code``): in an identity-service body it is a
        sentence for people, not a code.
        """
        envelope = body.get("error") if isinstance(body, dict) else None
        details: Dict[str, Any] = {}
        code = "unknown"
        request_id: Optional[str] = None
        reason: Optional[str] = None
        if isinstance(envelope, dict):
            for key, value in envelope.items():
                if key not in ("code", "message", "request_id"):
                    details[key] = value
            if isinstance(envelope.get("code"), str):
                code = envelope["code"]
                if isinstance(envelope.get("reason"), str):
                    reason = envelope["reason"]
            if isinstance(envelope.get("request_id"), str):
                request_id = envelope["request_id"]
        return cls(
            code=code,
            message=_extract_message(body, status),
            status=status,
            request_id=request_id,
            details=details,
            retry_after=retry_after,
            body=body,
            reason=reason,
        )

    def __repr__(self) -> str:
        return (
            f"VerneAPIError(code={self.code!r}, status={self.status}, "
            f"reason={self.reason!r}, request_id={self.request_id!r}, message={str(self)!r})"
        )


class VerneTokenError(VerneError):
    """Raised by signed-token verification when a token must not be trusted.

    :ivar reason: one of ``malformed``, ``unsupported_alg``, ``unknown_kid``,
        ``bad_signature``, ``wrong_issuer``, ``expired``, ``not_yet_valid``,
        ``missing_claim``, ``jwks_unavailable``.
    """

    def __init__(self, reason: TokenErrorReason, message: str) -> None:
        super().__init__(message)
        self.reason: TokenErrorReason = reason

    def __repr__(self) -> str:
        return f"VerneTokenError(reason={self.reason!r}, message={str(self)!r})"


def _extract_message(body: Any, status: int) -> str:
    """Best-effort human-readable message from an arbitrary error body."""
    if isinstance(body, dict):
        envelope = body.get("error")
        if isinstance(envelope, dict) and isinstance(envelope.get("message"), str):
            return str(envelope["message"])
        if isinstance(envelope, str) and envelope.strip():
            return envelope
        detail = body.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            messages = [
                str(item["msg"])
                for item in detail
                if isinstance(item, dict) and isinstance(item.get("msg"), str)
            ]
            if messages:
                return "; ".join(messages)
        if isinstance(body.get("message"), str):
            return str(body["message"])
    return f"HTTP {status}"
