from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LoginStart:
    """Result of starting a Passepartout Telegram login flow."""

    nonce: str
    deep_link: str
    expires_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoginStart":
        return cls(
            nonce=data["nonce"],
            deep_link=data["deep_link"],
            expires_at=data["expires_at"],
        )


@dataclass(frozen=True)
class TelegramUser:
    """A Telegram user linked to a Passepartout login."""

    id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    photo_url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelegramUser":
        return cls(
            id=data["id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            photo_url=data.get("photo_url"),
        )


@dataclass(frozen=True)
class LoginStatus:
    """Status of a Passepartout Telegram login flow."""

    status: str
    access_token: Optional[str] = None
    expires_at: Optional[str] = None
    identity_id: Optional[str] = None
    user: Optional[TelegramUser] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoginStatus":
        user = data.get("user")
        return cls(
            status=data["status"],
            access_token=data.get("access_token"),
            expires_at=data.get("expires_at"),
            identity_id=data.get("identity_id"),
            user=TelegramUser.from_dict(user) if user is not None else None,
        )


@dataclass(frozen=True)
class TokenIntrospection:
    """Result of a Passepartout access token introspection."""

    active: bool
    subject: Optional[str] = None
    tenant_id: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenIntrospection":
        return cls(
            active=data["active"],
            subject=data.get("subject"),
            tenant_id=data.get("tenant_id"),
            scopes=data.get("scopes", []),
            expires_at=data.get("expires_at"),
        )
