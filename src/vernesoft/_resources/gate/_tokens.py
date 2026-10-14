from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..._core.errors import VerneError
from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import AccessToken, IntrospectResult, Session, SignedToken, SignedTokenClaims
from ._verifier import AsyncGateTokenVerifier, GateTokenVerifier

_PATH_TOKENS = "/v1/gate/tokens"
_PATH_INTROSPECT = "/v1/gate/tokens/introspect"
_PATH_WHOAMI = "/auth/sessions/whoami"
_TOKENIZE = {"tokenize_as": "gate_jwt"}


def _create_body(
    subject: str, scopes: Optional[List[str]], ttl_seconds: Optional[int]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"subject": subject}
    if scopes is not None:
        body["scopes"] = list(scopes)
    if ttl_seconds is not None:
        body["ttl_seconds"] = ttl_seconds
    return body


def _signed(data: Any) -> SignedToken:
    if not isinstance(data, dict) or not isinstance(data.get("tokenized"), str):
        raise VerneError("The session answer carried no signed token (`tokenized`).")
    session = {k: v for k, v in data.items() if k != "tokenized"}
    return SignedToken(token=data["tokenized"], session=Session.from_dict(session))


class TokensResource:
    """Synchronous Gate token operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http
        self._verifiers: Dict[Tuple[str, int], GateTokenVerifier] = {}

    def create(
        self,
        *,
        subject: str,
        scopes: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AccessToken:
        """Exchange the API key for a short-lived access token for ``subject`` — a user or
        a service account. ``ttl_seconds`` defaults to 3600, at most 86400.

        The key travels in the ``Authorization`` header like on every other call. (Until
        1.4.0 this SDK sent it in the body without the header, which the API refuses
        with ``401``.)
        """
        data = self._http.post(_PATH_TOKENS, body=_create_body(subject, scopes, ttl_seconds))
        return AccessToken.from_dict(data)

    def introspect(self, access_token: str) -> IntrospectResult:
        """Validate a Gate access token and return its attributes.

        An unknown, expired or foreign token, or one whose user you deactivated or
        deleted, is ``active=False`` with nothing else. When the subject is an end user,
        ``orgs`` lists their organizations in the key's project, read now.
        """
        data = self._http.post(_PATH_INTROSPECT, body={"access_token": access_token})
        return IntrospectResult.from_dict(data)

    def create_signed(self, session_token: str) -> SignedToken:
        """Get a **signed JWT** (ES256) for a signed-in end user's session, for a platform
        that verifies signatures instead of calling Gate (Supabase, an API gateway).

        The session token is the credential: no API key is sent. The token is valid for
        15 minutes and **cannot be revoked**; its ``orgs`` claim is as old as the token.
        Every call mints a new one. A revoked or expired session, or a deactivated user,
        is a ``401``.
        """
        data = self._http.get(
            _PATH_WHOAMI, params=_TOKENIZE, skip_auth=True, session_token=session_token
        )
        return _signed(data)

    def verify_signed(self, token: str, *, tenant_id: str, leeway: int = 10) -> SignedTokenClaims:
        """Verify a Gate signed token offline against your tenant's public keys (fetched
        once and cached) and return its claims.

        Raises :class:`~vernesoft.VerneTokenError` when the token must not be trusted —
        wrong issuer (another tenant), bad signature, expired, any algorithm but ES256.
        Needs ``pip install "vernesoft[jwt]"``. See :class:`GateTokenVerifier` to verify
        without a Gate client.
        """
        key = (tenant_id, leeway)
        verifier = self._verifiers.get(key)
        if verifier is None:
            verifier = GateTokenVerifier(
                tenant_id=tenant_id, base_url=self._http.base_url, leeway=leeway
            )
            self._verifiers[key] = verifier
        return verifier.verify(token)


class AsyncTokensResource:
    """Asynchronous Gate token operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http
        self._verifiers: Dict[Tuple[str, int], AsyncGateTokenVerifier] = {}

    async def create(
        self,
        *,
        subject: str,
        scopes: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> AccessToken:
        """Exchange the API key for a short-lived access token. See
        :meth:`TokensResource.create`."""
        data = await self._http.post(_PATH_TOKENS, body=_create_body(subject, scopes, ttl_seconds))
        return AccessToken.from_dict(data)

    async def introspect(self, access_token: str) -> IntrospectResult:
        """Validate a Gate access token. An inactive token is ``active=False`` only."""
        data = await self._http.post(_PATH_INTROSPECT, body={"access_token": access_token})
        return IntrospectResult.from_dict(data)

    async def create_signed(self, session_token: str) -> SignedToken:
        """Get a signed JWT for an end user's session (15 minutes, not revocable). See
        :meth:`TokensResource.create_signed`."""
        data = await self._http.get(
            _PATH_WHOAMI, params=_TOKENIZE, skip_auth=True, session_token=session_token
        )
        return _signed(data)

    async def verify_signed(
        self, token: str, *, tenant_id: str, leeway: int = 10
    ) -> SignedTokenClaims:
        """Verify a Gate signed token offline. See :meth:`TokensResource.verify_signed`."""
        key = (tenant_id, leeway)
        verifier = self._verifiers.get(key)
        if verifier is None:
            verifier = AsyncGateTokenVerifier(
                tenant_id=tenant_id, base_url=self._http.base_url, leeway=leeway
            )
            self._verifiers[key] = verifier
        return await verifier.verify(token)
