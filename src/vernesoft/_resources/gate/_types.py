from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Identity:
    """A Gate identity object."""

    id: str
    schema_id: str
    state: str
    traits: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Identity":
        return cls(
            id=data["id"],
            schema_id=data["schema_id"],
            state=data["state"],
            traits=data.get("traits", {}),
        )


@dataclass(frozen=True)
class AccessToken:
    """An access token issued by the Gate service."""

    access_token: str
    expires_at: str
    subject: str
    tenant_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessToken":
        return cls(
            access_token=data["access_token"],
            expires_at=data["expires_at"],
            subject=data["subject"],
            tenant_id=data["tenant_id"],
        )


@dataclass(frozen=True)
class IntrospectResult:
    """Result of a token introspection."""

    active: bool
    subject: str
    tenant_id: str
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntrospectResult":
        return cls(
            active=data["active"],
            subject=data["subject"],
            tenant_id=data["tenant_id"],
            scopes=data.get("scopes", []),
            expires_at=data.get("expires_at"),
        )


@dataclass(frozen=True)
class SecuritySettings:
    """Security-related Gate Identity settings for a tenant."""

    passwordless_enabled: bool
    mfa_enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecuritySettings":
        return cls(
            passwordless_enabled=bool(data.get("passwordless_enabled", False)),
            mfa_enabled=bool(data.get("mfa_enabled", False)),
        )


@dataclass(frozen=True)
class OidcProvider:
    """A social login (OAuth 2.0 / OIDC) provider and whether it is enabled."""

    provider: str
    enabled: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OidcProvider":
        return cls(
            provider=str(data.get("provider", "")),
            enabled=bool(data.get("enabled", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"provider": self.provider, "enabled": self.enabled}


@dataclass(frozen=True)
class AuthorizeResult:
    """Result of an authorization check."""

    allowed: bool
    decision_id: str
    reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorizeResult":
        return cls(
            allowed=data["allowed"],
            decision_id=data["decision_id"],
            reason=data.get("reason"),
        )
