"""vernesoft — Official Python SDK for the Verne Nautilus platform."""

from ._client import AsyncVerne, Verne
from ._core.errors import TokenErrorReason, VerneAPIError, VerneError, VerneTokenError
from ._core.types import NOT_GIVEN, NotGiven, Paginated
from ._resources.clockwork._clockwork import AsyncClockwork, Clockwork
from ._resources.clockwork._types import (
    ClockworkUsage,
    CronJob,
    CronUsage,
    DelayedJob,
    DelayedUsage,
    Execution,
)
from ._resources.gate._gate import AsyncGate, Gate
from ._resources.gate._types import (
    REASON_MEMBER_WITH_PERMISSION,
    REASON_MEMBER_WITHOUT_PERMISSION,
    REASON_NO_SUCH_ORGANIZATION,
    REASON_NOT_A_MEMBER,
    REASON_SUBJECT_INACTIVE,
    AccessToken,
    AuditActor,
    AuditLogEntry,
    AuditTarget,
    AuthorizeResult,
    Identity,
    IdentityTraitsInput,
    IntrospectResult,
    LifecycleAction,
    LifecycleRule,
    LifecycleRuleKind,
    LifecycleRulePreview,
    LifecycleRules,
    Member,
    OidcExchangeResult,
    OidcProvider,
    Organization,
    OrgClaim,
    Role,
    SecuritySettings,
    Session,
    SessionCheck,
    SignedToken,
    SignedTokenClaims,
)
from ._resources.gate._verifier import AsyncGateTokenVerifier, GateTokenVerifier
from ._resources.passepartout._passepartout import AsyncPassepartout, Passepartout
from ._resources.passepartout._types import (
    LoginStart,
    LoginStatus,
    TelegramUser,
    TokenIntrospection,
)
from ._resources.relay._relay import AsyncRelay, Relay
from ._resources.relay._types import ListMessagesResponse, Message

__version__ = "1.4.0"

__all__ = [
    "__version__",
    # Unified clients
    "Verne",
    "AsyncVerne",
    # Per-service clients
    "Relay",
    "AsyncRelay",
    "Gate",
    "AsyncGate",
    "Passepartout",
    "AsyncPassepartout",
    "Clockwork",
    "AsyncClockwork",
    # Signed-token verification
    "GateTokenVerifier",
    "AsyncGateTokenVerifier",
    # Errors
    "VerneError",
    "VerneAPIError",
    "VerneTokenError",
    "TokenErrorReason",
    # Relay types
    "Message",
    "ListMessagesResponse",
    # Gate types
    "Identity",
    "IdentityTraitsInput",
    "AccessToken",
    "IntrospectResult",
    "AuthorizeResult",
    "SecuritySettings",
    "OidcProvider",
    "OidcExchangeResult",
    "OrgClaim",
    "Organization",
    "Role",
    "Member",
    "Session",
    "SessionCheck",
    "SignedToken",
    "SignedTokenClaims",
    "AuditLogEntry",
    "AuditActor",
    "AuditTarget",
    "LifecycleRuleKind",
    "LifecycleRule",
    "LifecycleRules",
    "LifecycleRulePreview",
    "LifecycleAction",
    "REASON_MEMBER_WITH_PERMISSION",
    "REASON_MEMBER_WITHOUT_PERMISSION",
    "REASON_NOT_A_MEMBER",
    "REASON_SUBJECT_INACTIVE",
    "REASON_NO_SUCH_ORGANIZATION",
    # Passepartout types
    "LoginStart",
    "LoginStatus",
    "TelegramUser",
    "TokenIntrospection",
    # Clockwork types
    "CronJob",
    "DelayedJob",
    "Execution",
    "ClockworkUsage",
    "CronUsage",
    "DelayedUsage",
    # Generic
    "Paginated",
    "NOT_GIVEN",
    "NotGiven",
]
