from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict

# ---------------------------------------------------------------------------
# Identities
# ---------------------------------------------------------------------------


class _IdentityTraitsRequired(TypedDict):
    email: str


class IdentityTraitsInput(_IdentityTraitsRequired, total=False):
    """Traits of a new end user. The ``user`` schema has exactly two: ``email``
    (required) and ``locale``; anything else is refused with ``400 invalid_payload``.
    Keep your own fields in custom metadata (``identities.update_metadata()``)."""

    locale: str


class PasswordConfigInput(TypedDict, total=False):
    """Give ``password`` or ``hashed_password``, not both."""

    #: The initial password, in clear.
    password: str
    #: A bcrypt hash (``$2a$…`` or ``$2b$…``) of the user's existing password; the user
    #: then signs in with their original password.
    hashed_password: str


class PasswordCredentialInput(TypedDict):
    config: PasswordConfigInput


class OidcProviderLink(TypedDict):
    """A social account linked to a new identity. ``provider`` is a Gate provider id
    (``"google"``, ``"github"``, …) and ``subject`` that provider's id for the account;
    together at most 254 characters."""

    provider: str
    subject: str


class OidcConfigInput(TypedDict):
    providers: List[OidcProviderLink]


class OidcCredentialInput(TypedDict):
    config: OidcConfigInput


class IdentityCredentialsInput(TypedDict, total=False):
    """Credentials of a new identity: a password (or its bcrypt hash) and the social
    accounts to link, e.g.
    ``{"password": {"config": {"hashed_password": "$2b$10$…"}},
    "oidc": {"config": {"providers": [{"provider": "google", "subject": "…"}]}}}``."""

    password: PasswordCredentialInput
    oidc: OidcCredentialInput


def _dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> List[Dict[str, Any]]:
    return [dict(x) for x in value if isinstance(x, dict)] if isinstance(value, list) else []


@dataclass(frozen=True)
class Identity:
    """An end user (a Kratos identity) managed by Gate.

    The object is the identity service's own: the stable fields are typed, the whole
    answer stays in ``raw``. ``traits`` holds ``email`` and, when set, ``locale``.
    """

    id: str
    schema_id: str
    state: str
    traits: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    state_changed_at: Optional[str] = None
    #: Your custom metadata — read and change it with ``identities.get_metadata()`` /
    #: ``update_metadata()``.
    metadata_public: Optional[Dict[str, Any]] = None
    verifiable_addresses: List[Dict[str, Any]] = field(default_factory=list)
    recovery_addresses: List[Dict[str, Any]] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Identity":
        metadata = data.get("metadata_public")
        return cls(
            id=data["id"],
            schema_id=data.get("schema_id", ""),
            state=data.get("state", ""),
            traits=_dict(data.get("traits")),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            state_changed_at=data.get("state_changed_at"),
            metadata_public=dict(metadata) if isinstance(metadata, dict) else None,
            verifiable_addresses=_list_of_dicts(data.get("verifiable_addresses")),
            recovery_addresses=_list_of_dicts(data.get("recovery_addresses")),
            raw=dict(data),
        )


# ---------------------------------------------------------------------------
# Tokens, introspection, authorization
# ---------------------------------------------------------------------------


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
class OrgClaim:
    """One organization a user belongs to — the unit Gate uses everywhere it says who a
    user is: introspection, the session check, the signed token's ``orgs`` claim and
    ``identities.list_organizations()``."""

    id: str
    #: The name of the role the user holds there.
    role: str
    #: That role's permissions, e.g. ``"invoices:write"``.
    permissions: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrgClaim":
        return cls(
            id=data["id"],
            role=data.get("role", ""),
            permissions=list(data.get("permissions") or []),
        )


def _orgs(value: Any) -> Optional[List[OrgClaim]]:
    if not isinstance(value, list):
        return None
    return [OrgClaim.from_dict(x) for x in value if isinstance(x, dict)]


@dataclass(frozen=True)
class IntrospectResult:
    """Result of a token introspection.

    An inactive token (unknown, expired, another tenant's, or its user deactivated or
    deleted) is ``active=False`` and nothing else: every other field is then ``None``.
    """

    active: bool
    subject: Optional[str] = None
    tenant_id: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    #: When ``subject`` is an end user's id: their organizations in the key's project,
    #: read live, the first 100 in the order they joined. ``None`` for any other subject.
    orgs: Optional[List[OrgClaim]] = None
    #: ``True``, and only then, when there are more than ``orgs`` shows — list them with
    #: ``identities.list_organizations()``.
    orgs_truncated: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntrospectResult":
        return cls(
            active=bool(data.get("active", False)),
            subject=data.get("subject"),
            tenant_id=data.get("tenant_id"),
            scopes=list(data.get("scopes") or []),
            expires_at=data.get("expires_at"),
            orgs=_orgs(data.get("orgs")),
            orgs_truncated=data.get("orgs_truncated") is True,
        )


#: ``reason`` values of an organization permission check (``AuthorizeResult.reason``).
REASON_MEMBER_WITH_PERMISSION = "member_with_permission"
REASON_MEMBER_WITHOUT_PERMISSION = "member_without_permission"
REASON_NOT_A_MEMBER = "not_a_member"
REASON_SUBJECT_INACTIVE = "subject_inactive"
REASON_NO_SUCH_ORGANIZATION = "no_such_organization"

#: ``reason`` values of a check on any other resource — *is the subject one of your
#: active end users?* — with ``REASON_SUBJECT_INACTIVE``. ``owned_by_tenant`` is the one
#: ``allowed=True`` answer.
REASON_OWNED_BY_TENANT = "owned_by_tenant"
REASON_NOT_OWNED_BY_TENANT = "not_owned_by_tenant"
REASON_NOT_A_KNOWN_IDENTITY = "not_a_known_identity"


@dataclass(frozen=True)
class AuthorizeResult:
    """An authorization decision.

    ``reason`` is a code to branch on, one of the ``REASON_*`` constants. For an
    organization resource it is ``member_with_permission``, ``member_without_permission``,
    ``not_a_member``, ``subject_inactive`` or ``no_such_organization``, and ``role`` is
    the role the user holds there (present for the first two and ``subject_inactive``).
    For any other resource it is ``owned_by_tenant`` (allowed), ``subject_inactive``,
    ``not_owned_by_tenant`` or ``not_a_known_identity``, and ``message`` says the same in
    a sentence for your logs — its wording can change; only ``reason`` is a contract.
    The set is open: treat a value you do not know as a denial.
    """

    allowed: bool
    #: Identifies the decision in Gate's logs, for support.
    decision_id: str
    reason: str = ""
    role: Optional[str] = None
    #: The decision as a sentence, for a resource that is not an organization; else None.
    message: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorizeResult":
        message = data.get("message")
        return cls(
            allowed=data.get("allowed") is True,
            decision_id=data.get("decision_id", ""),
            reason=data.get("reason") or "",
            role=data.get("role"),
            message=message if isinstance(message, str) else None,
        )


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecuritySettings:
    """Security-related Gate Identity settings for a tenant."""

    passwordless_enabled: bool
    #: With MFA on, ``sessions.check()`` refuses a session without a second factor
    #: (``403 mfa_required``).
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


# ---------------------------------------------------------------------------
# Sessions and signed tokens
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    """An end user's session, as the identity service returns it. The whole answer stays
    in ``raw``."""

    id: str
    active: Optional[bool] = None
    authenticated_at: Optional[str] = None
    expires_at: Optional[str] = None
    issued_at: Optional[str] = None
    authenticator_assurance_level: Optional[str] = None
    authentication_methods: List[Dict[str, Any]] = field(default_factory=list)
    devices: List[Dict[str, Any]] = field(default_factory=list)
    identity: Optional[Dict[str, Any]] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        identity = data.get("identity")
        active = data.get("active")
        return cls(
            id=data.get("id", ""),
            active=active if isinstance(active, bool) else None,
            authenticated_at=data.get("authenticated_at"),
            expires_at=data.get("expires_at"),
            issued_at=data.get("issued_at"),
            authenticator_assurance_level=data.get("authenticator_assurance_level"),
            authentication_methods=_list_of_dicts(data.get("authentication_methods")),
            devices=_list_of_dicts(data.get("devices")),
            identity=dict(identity) if isinstance(identity, dict) else None,
            raw=dict(data),
        )


@dataclass(frozen=True)
class SessionCheck:
    """The answer of ``sessions.check()`` — whether a session is good enough to act on.
    Gate on ``mfa_satisfied``."""

    active: bool
    #: ``"aal1"`` or ``"aal2"``.
    aal: str
    #: Whether your tenant requires a second factor.
    mfa_required: bool
    #: Whether this session meets what your tenant requires — the one field to gate on.
    mfa_satisfied: bool
    identity_id: Optional[str] = None
    #: The user's organizations in the key's project, read now (first 100).
    orgs: Optional[List[OrgClaim]] = None
    orgs_truncated: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionCheck":
        return cls(
            active=data.get("active") is True,
            aal=data.get("aal", ""),
            mfa_required=data.get("mfa_required") is True,
            mfa_satisfied=data.get("mfa_satisfied") is True,
            identity_id=data.get("identity_id"),
            orgs=_orgs(data.get("orgs")),
            orgs_truncated=data.get("orgs_truncated") is True,
        )


@dataclass(frozen=True)
class SignedToken:
    """What ``tokens.create_signed()`` returns."""

    #: The compact ES256 JWT. Valid for 15 minutes; it cannot be revoked.
    token: str
    #: The session the token was made from, as ``whoami`` returns it.
    session: Session


@dataclass(frozen=True)
class SignedTokenClaims:
    """The verified payload of a Gate signed token. Every claim is also in ``raw``.

    ``orgs`` is as old as the token: for anything that must follow a revocation or a
    role change at once, use ``sessions.check()``, introspection or
    ``organizations.can()``.
    """

    #: ``<base URL>/auth/<tenant id>`` — checked by the verifier.
    iss: str
    #: The end user's identity id.
    sub: str
    exp: int
    #: The session the token was made from (revocable with ``sessions.revoke()``).
    sid: Optional[str] = None
    tenant_id: Optional[str] = None
    schema_id: Optional[str] = None
    email: Optional[str] = None
    #: Always ``"authenticated"`` (the database role PostgREST-style consumers use).
    role: Optional[str] = None
    orgs: List[OrgClaim] = field(default_factory=list)
    #: ``True`` when ``orgs`` is incomplete; list them with
    #: ``identities.list_organizations(sub)``.
    orgs_truncated: bool = False
    iat: Optional[int] = None
    nbf: Optional[int] = None
    jti: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedTokenClaims":
        def _int(value: Any) -> Optional[int]:
            return int(value) if isinstance(value, (int, float)) else None

        return cls(
            iss=data["iss"],
            sub=data["sub"],
            exp=int(data["exp"]),
            sid=data.get("sid"),
            tenant_id=data.get("tenant_id"),
            schema_id=data.get("schema_id"),
            email=data.get("email"),
            role=data.get("role"),
            orgs=_orgs(data.get("orgs")) or [],
            orgs_truncated=data.get("orgs_truncated") is True,
            iat=_int(data.get("iat")),
            nbf=_int(data.get("nbf")),
            jti=data.get("jti"),
            raw=dict(data),
        )


@dataclass(frozen=True)
class OidcExchangeResult:
    """What ``exchange_oidc_code()`` returns: the same shape a password login returns."""

    #: The end user's session token. Keep it on your server.
    session_token: str
    session: Session
    raw: Dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OidcExchangeResult":
        return cls(
            session_token=data["session_token"],
            session=Session.from_dict(_dict(data.get("session"))),
            raw=dict(data),
        )


# ---------------------------------------------------------------------------
# Organizations, roles, members
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Organization:
    """A group of your end users (a customer's team, workspace, company)."""

    id: str
    #: Free text, 1–120 characters, not unique.
    name: str
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Organization":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass(frozen=True)
class Role:
    """A named set of permissions inside one organization."""

    id: str
    organization_id: str
    #: Lowercase letters, digits, ``_`` and ``-``; unique in the organization.
    name: str
    #: Sorted and de-duplicated by the API.
    permissions: List[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        return cls(
            id=data["id"],
            organization_id=data.get("organization_id", ""),
            name=data["name"],
            permissions=list(data.get("permissions") or []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass(frozen=True)
class Member:
    """An end user's membership of an organization."""

    organization_id: str
    identity_id: str
    role_id: str
    #: When the membership ends, or ``None`` for never.
    expires_at: Optional[str]
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Member":
        return cls(
            organization_id=data.get("organization_id", ""),
            identity_id=data["identity_id"],
            role_id=data["role_id"],
            expires_at=data.get("expires_at"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

#: Who acted. An open set: ``unknown`` exists and more may be added.
AuditActorType = Literal["team_member", "api_key", "end_user", "system", "staff"]


@dataclass(frozen=True)
class AuditActor:
    type: str
    id: Optional[str] = None


@dataclass(frozen=True)
class AuditTarget:
    type: str
    id: str


@dataclass(frozen=True)
class AuditLogEntry:
    """One entry of the audit log."""

    id: str
    occurred_at: str
    #: Open set: new actions are added over time.
    action: str
    actor: AuditActor
    target: Optional[AuditTarget]
    project_id: Optional[str]
    #: Free-form facts about the event, never personal data.
    details: Dict[str, Any]
    ip: Optional[str]
    user_agent: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditLogEntry":
        actor = _dict(data.get("actor"))
        target = data.get("target")
        return cls(
            id=data["id"],
            occurred_at=data.get("occurred_at", ""),
            action=data.get("action", ""),
            actor=AuditActor(type=actor.get("type", "unknown"), id=actor.get("id")),
            target=(
                AuditTarget(type=target.get("type", ""), id=target.get("id", ""))
                if isinstance(target, dict)
                else None
            ),
            project_id=data.get("project_id"),
            details=_dict(data.get("details")),
            ip=data.get("ip"),
            user_agent=data.get("user_agent"),
        )


# ---------------------------------------------------------------------------
# Automatic deletion (lifecycle rules)
# ---------------------------------------------------------------------------

LifecycleRuleKind = Literal[
    "delete_unverified", "remind_unverified", "expire_roles", "delete_inactive"
]
LifecycleActionStatus = Literal["pending", "done", "cancelled", "failed"]


@dataclass(frozen=True)
class LifecycleRule:
    """One automatic-deletion rule of the key's project, set up or not."""

    kind: str
    configured: bool
    enabled: bool
    #: The rule's settings, or ``None`` when it was never set up.
    params: Optional[Dict[str, Any]]
    #: Whether your plan includes the rule.
    available: bool
    #: ``"plan"`` when a plan change switched the rule off.
    disabled_reason: Optional[str]
    enabled_at: Optional[str]
    updated_at: Optional[str]
    #: How many people have something scheduled by this rule.
    pending: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifecycleRule":
        params = data.get("params")
        return cls(
            kind=data["kind"],
            configured=data.get("configured") is True,
            enabled=data.get("enabled") is True,
            params=dict(params) if isinstance(params, dict) else None,
            available=data.get("available") is True,
            disabled_reason=data.get("disabled_reason"),
            enabled_at=data.get("enabled_at"),
            updated_at=data.get("updated_at"),
            pending=int(data.get("pending") or 0),
        )


@dataclass(frozen=True)
class LifecycleRules:
    """All four rules of the key's project, and the plan."""

    #: Your plan: ``free``, ``pro``, ``advanced`` or ``contract``.
    tier: str
    rules: List[LifecycleRule]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifecycleRules":
        return cls(
            tier=data.get("tier", ""),
            rules=[LifecycleRule.from_dict(r) for r in data.get("rules") or []],
        )


@dataclass(frozen=True)
class LifecycleRulePreview:
    """How many people a rule with given settings would affect right now."""

    kind: str
    available: bool
    matching_now: int
    #: ``True`` when the count stopped at 1,000.
    capped: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifecycleRulePreview":
        return cls(
            kind=data["kind"],
            available=data.get("available") is True,
            matching_now=int(data.get("matching_now") or 0),
            capped=data.get("capped") is True,
        )


@dataclass(frozen=True)
class LifecycleAction:
    """Something a rule scheduled or did to one person."""

    id: str
    kind: str
    #: ``remind``, ``warn``, ``delete`` or ``revoke``.
    step: str
    identity_id: str
    #: ``pending``, ``done``, ``cancelled`` or ``failed``.
    status: str
    basis_at: str
    due_at: str
    #: Why it was cancelled or failed (``rule_disabled``, ``verified``, ``signed_in``, …).
    reason: Optional[str]
    created_at: str
    finished_at: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifecycleAction":
        return cls(
            id=data["id"],
            kind=data.get("kind", ""),
            step=data.get("step", ""),
            identity_id=data.get("identity_id", ""),
            status=data.get("status", ""),
            basis_at=data.get("basis_at", ""),
            due_at=data.get("due_at", ""),
            reason=data.get("reason"),
            created_at=data.get("created_at", ""),
            finished_at=data.get("finished_at"),
        )
