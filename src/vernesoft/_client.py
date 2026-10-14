from __future__ import annotations

from typing import Optional

from ._core.errors import VerneError
from ._core.http import DEFAULT_BASE_URL
from ._resources.clockwork._clockwork import AsyncClockwork, Clockwork
from ._resources.gate._gate import AsyncGate, Gate
from ._resources.passepartout._passepartout import AsyncPassepartout, Passepartout
from ._resources.relay._relay import AsyncRelay, Relay

_DEFAULT_TIMEOUT = 30.0

_LABELS = {
    "relay": "Relay",
    "gate": "Gate",
    "passepartout": "Passepartout",
    "clockwork": "Clockwork",
}


class _Keys:
    """API keys of a unified client: one shared key, per-service keys override it."""

    def __init__(
        self,
        client: str,
        api_key: Optional[str],
        relay: Optional[str],
        gate: Optional[str],
        passepartout: Optional[str],
        clockwork: Optional[str],
    ) -> None:
        self._client = client
        self._shared = api_key
        self._per_service = {
            "relay": relay,
            "gate": gate,
            "passepartout": passepartout,
            "clockwork": clockwork,
        }

    def for_service(self, service: str) -> str:
        key = self._per_service[service] or self._shared
        if not key:
            raise VerneError(
                f"No API key for {_LABELS[service]}. Pass api_key='vrn_...' to "
                f"{self._client}() (or {service}='vrn_...' to use a separate key for "
                f"{_LABELS[service]})."
            )
        return key


class Verne:
    """Unified synchronous client for the Verne Nautilus platform.

    Pass one API key (``api_key``) and use every service its scopes allow — ``relay``,
    ``gate``, ``passepartout``, ``clockwork``. A key is ``vrn_…`` and carries a set of
    scopes; a call to a service the key has no scope for is refused by the API with
    ``403 forbidden``. The per-service keys are for using a *different* key for one
    service: they override ``api_key`` for that service. Keys made before scopes
    existed (``vrn_gate_…``, ``vrn_relay_…``, …) keep working for the one API they name.
    There is no test or live mode: every key acts on your real data.

    Services are created on first access; accessing one with no key raises
    :class:`VerneError`.

    Example::

        verne = Verne(api_key=os.environ["VERNE_API_KEY"])
        verne.gate.organizations.create(name="Acme")
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        relay: Optional[str] = None,
        gate: Optional[str] = None,
        passepartout: Optional[str] = None,
        clockwork: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._keys = _Keys("Verne", api_key, relay, gate, passepartout, clockwork)
        self._base_url = base_url
        self._timeout = timeout

        self._relay_client: Relay | None = None
        self._gate_client: Gate | None = None
        self._passepartout_client: Passepartout | None = None
        self._clockwork_client: Clockwork | None = None

    @property
    def relay(self) -> Relay:
        """The Relay (Webhooks-as-a-Service) client, created on first access."""
        if self._relay_client is None:
            self._relay_client = Relay(
                api_key=self._keys.for_service("relay"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._relay_client

    @property
    def gate(self) -> Gate:
        """The Gate (sign-in and end users) client, created on first access."""
        if self._gate_client is None:
            self._gate_client = Gate(
                api_key=self._keys.for_service("gate"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._gate_client

    @property
    def passepartout(self) -> Passepartout:
        """The Passepartout (Telegram sign-in) client, created on first access."""
        if self._passepartout_client is None:
            self._passepartout_client = Passepartout(
                api_key=self._keys.for_service("passepartout"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._passepartout_client

    @property
    def clockwork(self) -> Clockwork:
        """The Clockwork (Cron-as-a-Service) client, created on first access."""
        if self._clockwork_client is None:
            self._clockwork_client = Clockwork(
                api_key=self._keys.for_service("clockwork"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._clockwork_client


class AsyncVerne:
    """Unified asynchronous client for the Verne Nautilus platform.

    The same keys as :class:`Verne`: one ``api_key`` for every service, per-service keys
    override it. Every method of its services is a coroutine.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        relay: Optional[str] = None,
        gate: Optional[str] = None,
        passepartout: Optional[str] = None,
        clockwork: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._keys = _Keys("AsyncVerne", api_key, relay, gate, passepartout, clockwork)
        self._base_url = base_url
        self._timeout = timeout

        self._relay_client: AsyncRelay | None = None
        self._gate_client: AsyncGate | None = None
        self._passepartout_client: AsyncPassepartout | None = None
        self._clockwork_client: AsyncClockwork | None = None

    @property
    def relay(self) -> AsyncRelay:
        """The AsyncRelay client, created on first access."""
        if self._relay_client is None:
            self._relay_client = AsyncRelay(
                api_key=self._keys.for_service("relay"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._relay_client

    @property
    def gate(self) -> AsyncGate:
        """The AsyncGate client, created on first access."""
        if self._gate_client is None:
            self._gate_client = AsyncGate(
                api_key=self._keys.for_service("gate"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._gate_client

    @property
    def passepartout(self) -> AsyncPassepartout:
        """The AsyncPassepartout client, created on first access."""
        if self._passepartout_client is None:
            self._passepartout_client = AsyncPassepartout(
                api_key=self._keys.for_service("passepartout"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._passepartout_client

    @property
    def clockwork(self) -> AsyncClockwork:
        """The AsyncClockwork client, created on first access."""
        if self._clockwork_client is None:
            self._clockwork_client = AsyncClockwork(
                api_key=self._keys.for_service("clockwork"),
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._clockwork_client
