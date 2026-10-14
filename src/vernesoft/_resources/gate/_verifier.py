"""Offline verification of Gate signed tokens (ES256 JWTs) against a tenant's JWKS.

Needs the optional ``cryptography`` package: ``pip install "vernesoft[jwt]"``.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import re
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from ..._core.errors import VerneError, VerneTokenError
from ..._core.http import DEFAULT_BASE_URL
from ._types import SignedTokenClaims

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey

#: Cache lifetime when the key set answers without ``Cache-Control: max-age``.
_DEFAULT_JWKS_MAX_AGE = 300.0
#: An unknown ``kid`` refetches the key set at most this often (seconds).
_MIN_REFETCH_INTERVAL = 30.0
_DEFAULT_LEEWAY = 10
_DEFAULT_TIMEOUT = 10.0
_B64URL = re.compile(r"^[A-Za-z0-9_-]*$")
_MAX_AGE = re.compile(r"max-age=(\d+)", re.IGNORECASE)

_INSTALL_HINT = (
    'Verifying Gate signed tokens needs the `cryptography` package: pip install "vernesoft[jwt]"'
)


def _require_crypto() -> None:
    try:
        import cryptography.hazmat.primitives.asymmetric.ec  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise VerneError(_INSTALL_HINT) from exc


def _b64url_decode(segment: str) -> Optional[bytes]:
    if not _B64URL.match(segment):
        return None
    try:
        return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
    except (binascii.Error, ValueError):
        return None


def _decode_json(segment: str, what: str) -> Dict[str, Any]:
    raw = _b64url_decode(segment)
    if raw is not None:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            value = None
        if isinstance(value, dict):
            return value
    raise VerneTokenError("malformed", f"Token {what} is not base64url JSON.")


def _public_key(jwk: Dict[str, Any]) -> Optional["EllipticCurvePublicKey"]:
    from cryptography.hazmat.primitives.asymmetric import ec

    x = _b64url_decode(str(jwk.get("x", "")))
    y = _b64url_decode(str(jwk.get("y", "")))
    if not x or not y or len(x) != 32 or len(y) != 32:
        return None
    try:
        numbers = ec.EllipticCurvePublicNumbers(
            int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()
        )
        return numbers.public_key()
    except ValueError:
        return None


def _signature_valid(key: "EllipticCurvePublicKey", signing_input: bytes, sig: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

    # A JWS ES256 signature is raw r‖s (32 + 32 bytes); cryptography wants DER.
    der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
    try:
        key.verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return False
    return True


class _Parsed:
    __slots__ = ("kid", "payload", "signing_input", "signature")

    def __init__(self, kid: str, payload: Dict[str, Any], signing_input: bytes, sig: bytes):
        self.kid = kid
        self.payload = payload
        self.signing_input = signing_input
        self.signature = sig


class _VerifierBase:
    def __init__(
        self,
        *,
        tenant_id: str,
        base_url: str = DEFAULT_BASE_URL,
        leeway: int = _DEFAULT_LEEWAY,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not tenant_id:
            raise VerneError("GateTokenVerifier needs your tenant_id.")
        _require_crypto()
        base = base_url.rstrip("/")
        #: ``<base_url>/auth/<tenant_id>``: the only ``iss`` accepted.
        self.issuer = f"{base}/auth/{tenant_id}"
        #: Where the tenant's public keys are published.
        self.jwks_url = f"{self.issuer}/.well-known/jwks.json"
        self.leeway = leeway
        self._timeout = timeout
        self._keys: Dict[str, "EllipticCurvePublicKey"] = {}
        self._fetched_at: Optional[float] = None  # time.monotonic() of the last fetch
        self._max_age = _DEFAULT_JWKS_MAX_AGE

    # -- pieces shared by the sync and async verifiers ---------------------------------

    @staticmethod
    def _parse(token: str) -> _Parsed:
        parts = token.split(".") if isinstance(token, str) else []
        if len(parts) != 3:
            raise VerneTokenError("malformed", "Not a compact JWT.")
        raw_header, raw_payload, raw_signature = parts
        header = _decode_json(raw_header, "header")
        payload = _decode_json(raw_payload, "payload")
        alg = header.get("alg")
        if alg != "ES256":
            raise VerneTokenError(
                "unsupported_alg",
                f"Token algorithm {json.dumps(alg)} is not accepted; Gate signs with ES256.",
            )
        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise VerneTokenError("malformed", "Token header has no `kid`.")
        signature = _b64url_decode(raw_signature)
        if signature is None or len(signature) != 64:
            raise VerneTokenError("bad_signature", "Token signature is not a P-256 signature.")
        signing_input = f"{raw_header}.{raw_payload}".encode("ascii")
        return _Parsed(kid, payload, signing_input, signature)

    def _finish(self, parsed: _Parsed, key: "EllipticCurvePublicKey") -> SignedTokenClaims:
        if not _signature_valid(key, parsed.signing_input, parsed.signature):
            raise VerneTokenError("bad_signature", "Token signature does not verify.")
        payload = parsed.payload
        if payload.get("iss") != self.issuer:
            raise VerneTokenError(
                "wrong_issuer",
                f"Token issuer {json.dumps(payload.get('iss'))} is not {self.issuer}.",
            )
        now = time.time()
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)) or isinstance(exp, bool):
            raise VerneTokenError("missing_claim", "Token has no `exp`.")
        if now > exp + self.leeway:
            raise VerneTokenError("expired", "Token has expired.")
        for claim in ("nbf", "iat"):
            value = payload.get(claim)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if value > now + self.leeway:
                    raise VerneTokenError("not_yet_valid", "Token is not valid yet.")
        sub = payload.get("sub")
        if not isinstance(sub, str) or not sub:
            raise VerneTokenError("missing_claim", "Token has no `sub`.")
        return SignedTokenClaims.from_dict(payload)

    def _stale(self) -> bool:
        if self._fetched_at is None:
            return True
        return time.monotonic() - self._fetched_at > self._max_age

    def _may_refetch(self) -> bool:
        if self._fetched_at is None:
            return True
        return time.monotonic() - self._fetched_at >= _MIN_REFETCH_INTERVAL

    def _unknown_kid(self, kid: str) -> VerneTokenError:
        return VerneTokenError("unknown_kid", f"No key {kid} in {self.jwks_url}.")

    def _install(self, response: httpx.Response) -> None:
        if not response.is_success:
            raise VerneTokenError(
                "jwks_unavailable", f"{self.jwks_url} answered HTTP {response.status_code}."
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise VerneTokenError(
                "jwks_unavailable", f"{self.jwks_url} did not answer JSON."
            ) from exc
        jwks = body.get("keys") if isinstance(body, dict) else None
        if not isinstance(jwks, list):
            raise VerneTokenError("jwks_unavailable", f"{self.jwks_url} has no `keys`.")
        keys: Dict[str, "EllipticCurvePublicKey"] = {}
        for jwk in jwks:
            if not isinstance(jwk, dict):
                continue
            if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
                continue
            if not isinstance(jwk.get("kid"), str):
                continue
            if jwk.get("use") not in (None, "sig"):
                continue
            key = _public_key(jwk)
            if key is not None:  # a key we cannot load is one we cannot verify with
                keys[jwk["kid"]] = key
        self._keys = keys
        self._fetched_at = time.monotonic()
        match = _MAX_AGE.search(response.headers.get("Cache-Control", ""))
        self._max_age = float(match.group(1)) if match else _DEFAULT_JWKS_MAX_AGE

    def _fetch_failed(self, exc: Exception) -> VerneTokenError:
        return VerneTokenError("jwks_unavailable", f"Could not fetch {self.jwks_url}: {exc}")


class GateTokenVerifier(_VerifierBase):
    """Verifies Gate signed tokens (ES256 JWTs) offline, against your tenant's published
    public keys. No API key is involved: anything that receives a token can verify it.

    What it checks: the algorithm is ES256 (anything else, ``none`` included, is
    refused), the key is the one the token's ``kid`` names in your tenant's key set, the
    signature, ``iss`` is **your** issuer (a token of another Gate tenant is refused even
    though its signature is valid), ``exp``, ``nbf``/``iat`` (with ``leeway`` seconds of
    clock skew, default 10), and that ``sub`` is present.

    What it cannot check: whether the session behind the token is still alive. A signed
    token lives 15 minutes and **cannot be revoked**; for anything that must follow a
    revocation or a role change at once, ask ``gate.sessions.check()``, introspection or
    ``gate.organizations.can()``.

    The key set is cached for its ``Cache-Control: max-age`` (five minutes) and refetched
    once when a token names a key it has not seen (at most every 30 s) — which is how a
    key rotation is followed. Keep one verifier per tenant and reuse it. Failures raise
    :class:`~vernesoft.VerneTokenError` with a ``reason``.

    Example::

        verifier = GateTokenVerifier(tenant_id=os.environ["VERNE_TENANT_ID"])
        claims = verifier.verify(token)
        claims.sub   # the end user's id
        claims.orgs  # [OrgClaim(id=…, role=…, permissions=[…])]
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        base_url: str = DEFAULT_BASE_URL,
        leeway: int = _DEFAULT_LEEWAY,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(tenant_id=tenant_id, base_url=base_url, leeway=leeway, timeout=timeout)
        self._lock = threading.Lock()

    def verify(self, token: str) -> SignedTokenClaims:
        """Verify ``token`` and return its claims; raise :class:`VerneTokenError` when it
        must not be trusted."""
        parsed = self._parse(token)
        return self._finish(parsed, self._key_for(parsed.kid))

    def _key_for(self, kid: str) -> "EllipticCurvePublicKey":
        if self._stale():
            self._refresh(required=not self._keys)
        key = self._keys.get(kid)
        if key is None and self._may_refetch():
            # A kid we have not seen: a new key may have started signing. Ask once.
            self._refresh(required=True)
            key = self._keys.get(kid)
        if key is None:
            raise self._unknown_kid(kid)
        return key

    def _refresh(self, *, required: bool) -> None:
        with self._lock:
            try:
                try:
                    response = httpx.get(
                        self.jwks_url,
                        headers={"Accept": "application/json"},
                        timeout=self._timeout,
                    )
                except httpx.HTTPError as exc:
                    raise self._fetch_failed(exc) from exc
                self._install(response)
            except VerneTokenError:
                # A stale key set is still the right one unless a token says otherwise.
                if required:
                    raise


class AsyncGateTokenVerifier(_VerifierBase):
    """The asynchronous :class:`GateTokenVerifier`: ``await verifier.verify(token)``.
    Same checks, same key-set cache."""

    def __init__(
        self,
        *,
        tenant_id: str,
        base_url: str = DEFAULT_BASE_URL,
        leeway: int = _DEFAULT_LEEWAY,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__(tenant_id=tenant_id, base_url=base_url, leeway=leeway, timeout=timeout)
        self._lock: Optional[asyncio.Lock] = None

    async def verify(self, token: str) -> SignedTokenClaims:
        """Verify ``token`` and return its claims; raise :class:`VerneTokenError` when it
        must not be trusted."""
        parsed = self._parse(token)
        return self._finish(parsed, await self._key_for(parsed.kid))

    async def _key_for(self, kid: str) -> "EllipticCurvePublicKey":
        if self._stale():
            await self._refresh(required=not self._keys)
        key = self._keys.get(kid)
        if key is None and self._may_refetch():
            await self._refresh(required=True)
            key = self._keys.get(kid)
        if key is None:
            raise self._unknown_kid(kid)
        return key

    async def _refresh(self, *, required: bool) -> None:
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            try:
                try:
                    async with httpx.AsyncClient(timeout=self._timeout) as client:
                        response = await client.get(
                            self.jwks_url, headers={"Accept": "application/json"}
                        )
                except httpx.HTTPError as exc:
                    raise self._fetch_failed(exc) from exc
                self._install(response)
            except VerneTokenError:
                if required:
                    raise
