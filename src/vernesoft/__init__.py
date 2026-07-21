"""vernesoft — Official Python SDK for the Verne Nautilus platform."""

from ._client import AsyncVerne, Verne
from ._core.errors import VerneAPIError, VerneError
from ._core.types import Paginated
from ._resources.gate._gate import AsyncGate, Gate
from ._resources.gate._types import (
    AccessToken,
    AuthorizeResult,
    Identity,
    IntrospectResult,
    OidcProvider,
    SecuritySettings,
)
from ._resources.relay._relay import AsyncRelay, Relay
from ._resources.relay._types import ListMessagesResponse, Message

__all__ = [
    # Unified clients
    "Verne",
    "AsyncVerne",
    # Per-service clients
    "Relay",
    "AsyncRelay",
    "Gate",
    "AsyncGate",
    # Errors
    "VerneError",
    "VerneAPIError",
    # Relay types
    "Message",
    "ListMessagesResponse",
    # Gate types
    "Identity",
    "AccessToken",
    "IntrospectResult",
    "AuthorizeResult",
    "SecuritySettings",
    "OidcProvider",
    # Generic
    "Paginated",
]
