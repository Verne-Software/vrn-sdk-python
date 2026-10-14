"""Tests for Gate signed-token verification, signed with locally generated P-256 keys."""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Optional

import pytest
from pytest_httpx import HTTPXMock

pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import hashes, hmac  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature  # noqa: E402

from vernesoft import (  # noqa: E402
    AsyncGate,
    AsyncGateTokenVerifier,
    Gate,
    GateTokenVerifier,
    VerneTokenError,
)

_BASE_URL = "http://api.soft.com"
_TENANT = "6a1b2c3d-4e5f-4061-8293-a4b5c6d7e8f9"
_ISSUER = f"{_BASE_URL}/auth/{_TENANT}"
_JWKS_URL = f"{_ISSUER}/.well-known/jwks.json"
_SUB = "c0ffee00-1111-4222-8333-444455556666"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64json(value: Dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode())


class _Key:
    def __init__(self, kid: str) -> None:
        self.kid = kid
        self.private = ec.generate_private_key(ec.SECP256R1())

    def jwk(self) -> Dict[str, Any]:
        numbers = self.private.public_key().public_numbers()
        return {
            "kty": "EC",
            "crv": "P-256",
            "alg": "ES256",
            "use": "sig",
            "kid": self.kid,
            "x": _b64(numbers.x.to_bytes(32, "big")),
            "y": _b64(numbers.y.to_bytes(32, "big")),
        }

    def sign(self, claims: Dict[str, Any], header: Optional[Dict[str, Any]] = None) -> str:
        head = header if header is not None else {"alg": "ES256", "typ": "JWT", "kid": self.kid}
        signing_input = f"{_b64json(head)}.{_b64json(claims)}".encode()
        der = self.private.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return f"{signing_input.decode()}.{_b64(signature)}"


def _claims(**overrides: Any) -> Dict[str, Any]:
    now = int(time.time())
    claims: Dict[str, Any] = {
        "iss": _ISSUER,
        "sub": _SUB,
        "sid": "ses_1",
        "tenant_id": _TENANT,
        "schema_id": "user",
        "email": "member@example.com",
        "role": "authenticated",
        "orgs": [{"id": "org_1", "role": "admin", "permissions": ["invoices:write"]}],
        "iat": now,
        "nbf": now,
        "exp": now + 900,
        "jti": "jti_1",
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


@pytest.fixture()
def key() -> _Key:
    return _Key("k1")


def _serve(httpx_mock: HTTPXMock, *keys: _Key, max_age: int = 300) -> None:
    httpx_mock.add_response(
        method="GET",
        url=_JWKS_URL,
        json={"keys": [k.jwk() for k in keys]},
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )


def _verifier() -> GateTokenVerifier:
    return GateTokenVerifier(tenant_id=_TENANT, base_url=_BASE_URL)


def _reason(verifier: GateTokenVerifier, token: str) -> str:
    with pytest.raises(VerneTokenError) as exc_info:
        verifier.verify(token)
    return exc_info.value.reason


# ===========================================================================
# Accepts
# ===========================================================================


def test_valid_token(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    verifier = _verifier()
    claims = verifier.verify(key.sign(_claims()))
    assert claims.sub == _SUB
    assert claims.iss == _ISSUER
    assert claims.sid == "ses_1"
    assert claims.role == "authenticated"
    assert claims.orgs[0].permissions == ["invoices:write"]
    assert claims.orgs_truncated is False
    assert claims.raw["jti"] == "jti_1"
    # The key set is cached: a second token needs no second fetch.
    verifier.verify(key.sign(_claims(jti="jti_2")))
    assert len(httpx_mock.get_requests()) == 1


def test_leeway_accepts_a_token_just_expired(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    now = int(time.time())
    assert _verifier().verify(key.sign(_claims(exp=now - 5))).sub == _SUB


def test_gate_tokens_verify_signed_uses_the_client_base_url(
    httpx_mock: HTTPXMock, key: _Key
) -> None:
    _serve(httpx_mock, key)
    gate = Gate(api_key="vrn_3b1e5d7a9c0f2e4d", base_url=_BASE_URL + "/")
    claims = gate.tokens.verify_signed(key.sign(_claims()), tenant_id=_TENANT)
    assert claims.tenant_id == _TENANT
    gate.tokens.verify_signed(key.sign(_claims()), tenant_id=_TENANT)  # cached verifier
    assert len(httpx_mock.get_requests()) == 1


async def test_async_verifier(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    verifier = AsyncGateTokenVerifier(tenant_id=_TENANT, base_url=_BASE_URL)
    assert (await verifier.verify(key.sign(_claims()))).sub == _SUB
    gate = AsyncGate(api_key="vrn_3b1e5d7a9c0f2e4d", base_url=_BASE_URL)
    _serve(httpx_mock, key)
    assert (await gate.tokens.verify_signed(key.sign(_claims()), tenant_id=_TENANT)).sub == _SUB


async def test_async_verifier_rejects_wrong_issuer(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    verifier = AsyncGateTokenVerifier(tenant_id=_TENANT, base_url=_BASE_URL)
    with pytest.raises(VerneTokenError) as exc_info:
        await verifier.verify(key.sign(_claims(iss=f"{_BASE_URL}/auth/someone-else")))
    assert exc_info.value.reason == "wrong_issuer"


# ===========================================================================
# Refuses
# ===========================================================================


def test_wrong_issuer(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    other = "11111111-2222-4333-8444-555555555555"
    assert _reason(_verifier(), key.sign(_claims(iss=f"{_BASE_URL}/auth/{other}"))) == (
        "wrong_issuer"
    )


def test_another_tenants_verifier_refuses_a_valid_token(httpx_mock: HTTPXMock, key: _Key) -> None:
    other_tenant = "11111111-2222-4333-8444-555555555555"
    httpx_mock.add_response(
        method="GET",
        url=f"{_BASE_URL}/auth/{other_tenant}/.well-known/jwks.json",
        json={"keys": [key.jwk()]},
    )
    foreign = GateTokenVerifier(tenant_id=other_tenant, base_url=_BASE_URL)
    assert _reason(foreign, key.sign(_claims())) == "wrong_issuer"


def test_alg_none_is_refused_without_fetching(httpx_mock: HTTPXMock, key: _Key) -> None:
    header = _b64json({"alg": "none", "typ": "JWT", "kid": "k1"})
    token = f"{header}.{_b64json(_claims())}."
    assert _reason(_verifier(), token) == "unsupported_alg"
    assert httpx_mock.get_requests() == []


def test_hs256_is_refused(httpx_mock: HTTPXMock, key: _Key) -> None:
    head = _b64json({"alg": "HS256", "typ": "JWT", "kid": "k1"})
    body = _b64json(_claims())
    mac = hmac.HMAC(json.dumps(key.jwk()).encode(), hashes.SHA256())
    mac.update(f"{head}.{body}".encode())
    token = f"{head}.{body}.{_b64(mac.finalize())}"
    assert _reason(_verifier(), token) == "unsupported_alg"


def test_bad_signature(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    impostor = _Key("k1")  # same kid, different key
    assert _reason(_verifier(), impostor.sign(_claims())) == "bad_signature"


def test_tampered_payload(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    head, _, sig = key.sign(_claims()).split(".")
    forged = f"{head}.{_b64json(_claims(sub='someone-else'))}.{sig}"
    assert _reason(_verifier(), forged) == "bad_signature"


def test_signature_of_wrong_length(httpx_mock: HTTPXMock, key: _Key) -> None:
    head, body, _ = key.sign(_claims()).split(".")
    assert _reason(_verifier(), f"{head}.{body}.{_b64(b'x' * 70)}") == "bad_signature"


def test_expired(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    now = int(time.time())
    assert _reason(_verifier(), key.sign(_claims(exp=now - 60, iat=now - 960))) == "expired"


def test_not_yet_valid(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    now = int(time.time())
    assert _reason(_verifier(), key.sign(_claims(nbf=now + 120))) == "not_yet_valid"


def test_missing_sub_and_exp(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    verifier = _verifier()
    without_sub = _claims()
    del without_sub["sub"]
    assert _reason(verifier, key.sign(without_sub)) == "missing_claim"
    without_exp = _claims()
    del without_exp["exp"]
    assert _reason(verifier, key.sign(without_exp)) == "missing_claim"


def test_malformed(httpx_mock: HTTPXMock) -> None:
    verifier = _verifier()
    assert _reason(verifier, "not-a-jwt") == "malformed"
    assert _reason(verifier, "a.b.c") == "malformed"
    no_kid = f"{_b64json({'alg': 'ES256'})}.{_b64json(_claims())}.{_b64(b'x' * 64)}"
    assert _reason(verifier, no_kid) == "malformed"


def test_jwks_unavailable(httpx_mock: HTTPXMock, key: _Key) -> None:
    httpx_mock.add_response(method="GET", url=_JWKS_URL, status_code=503)
    assert _reason(_verifier(), key.sign(_claims())) == "jwks_unavailable"


# ===========================================================================
# Key rotation
# ===========================================================================


def test_unknown_kid_refetches_once(httpx_mock: HTTPXMock, key: _Key) -> None:
    rotated = _Key("k2")
    _serve(httpx_mock, key)
    verifier = _verifier()
    verifier.verify(key.sign(_claims()))

    # Within 30 s of the last fetch an unknown kid is refused without asking again.
    assert _reason(verifier, rotated.sign(_claims())) == "unknown_kid"
    assert len(httpx_mock.get_requests()) == 1

    # Later, the unknown kid triggers one refetch, which brings the new key.
    _serve(httpx_mock, key, rotated)
    assert verifier._fetched_at is not None
    verifier._fetched_at -= 31
    assert verifier.verify(rotated.sign(_claims())).sub == _SUB
    assert len(httpx_mock.get_requests()) == 2


def test_still_unknown_kid_after_refetch(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key)
    verifier = _verifier()
    verifier.verify(key.sign(_claims()))
    _serve(httpx_mock, key)
    assert verifier._fetched_at is not None
    verifier._fetched_at -= 31
    assert _reason(verifier, _Key("k9").sign(_claims())) == "unknown_kid"
    assert len(httpx_mock.get_requests()) == 2


def test_stale_cache_survives_a_failed_refresh(httpx_mock: HTTPXMock, key: _Key) -> None:
    _serve(httpx_mock, key, max_age=1)
    verifier = _verifier()
    verifier.verify(key.sign(_claims()))
    httpx_mock.add_response(method="GET", url=_JWKS_URL, status_code=500)
    assert verifier._fetched_at is not None
    verifier._fetched_at -= 2  # past max-age
    assert verifier.verify(key.sign(_claims())).sub == _SUB


def test_needs_a_tenant() -> None:
    from vernesoft import VerneError

    with pytest.raises(VerneError):
        GateTokenVerifier(tenant_id="")
