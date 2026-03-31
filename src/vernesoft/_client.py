from __future__ import annotations

from typing import Optional

from ._core.errors import VerneError
from ._resources.gate._gate import AsyncGate, Gate
from ._resources.relay._relay import AsyncRelay, Relay

_DEFAULT_BASE_URL = "https://api.vernesoft.com"
_DEFAULT_TIMEOUT = 30.0


class Verne:
    """Unified synchronous client for the Verne Nautilus platform.

    Provides lazy access to the Relay and Gate services via the ``relay``
    and ``gate`` properties.  Raise ``VerneError`` if you try to access a
    service for which no API key was supplied.
    """

    def __init__(
        self,
        *,
        relay: Optional[str] = None,
        gate: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._relay_key = relay
        self._gate_key = gate
        self._base_url = base_url
        self._timeout = timeout

        self._relay_client: Relay | None = None
        self._gate_client: Gate | None = None

    @property
    def relay(self) -> Relay:
        """Return the Relay service client, initialising it on first access."""
        if self._relay_client is None:
            if self._relay_key is None:
                raise VerneError(
                    "No Relay API key provided. Pass relay='vrn_relay_...' to Verne()."
                )
            self._relay_client = Relay(
                api_key=self._relay_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._relay_client

    @property
    def gate(self) -> Gate:
        """Return the Gate service client, initialising it on first access."""
        if self._gate_client is None:
            if self._gate_key is None:
                raise VerneError("No Gate API key provided. Pass gate='vrn_gate_...' to Verne().")
            self._gate_client = Gate(
                api_key=self._gate_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._gate_client


class AsyncVerne:
    """Unified asynchronous client for the Verne Nautilus platform.

    Provides lazy access to the AsyncRelay and AsyncGate services via the
    ``relay`` and ``gate`` properties.  Raises ``VerneError`` if you try to
    access a service for which no API key was supplied.
    """

    def __init__(
        self,
        *,
        relay: Optional[str] = None,
        gate: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._relay_key = relay
        self._gate_key = gate
        self._base_url = base_url
        self._timeout = timeout

        self._relay_client: AsyncRelay | None = None
        self._gate_client: AsyncGate | None = None

    @property
    def relay(self) -> AsyncRelay:
        """Return the AsyncRelay service client, initialising it on first access."""
        if self._relay_client is None:
            if self._relay_key is None:
                raise VerneError(
                    "No Relay API key provided. Pass relay='vrn_relay_...' to AsyncVerne()."
                )
            self._relay_client = AsyncRelay(
                api_key=self._relay_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._relay_client

    @property
    def gate(self) -> AsyncGate:
        """Return the AsyncGate service client, initialising it on first access."""
        if self._gate_client is None:
            if self._gate_key is None:
                raise VerneError(
                    "No Gate API key provided. Pass gate='vrn_gate_...' to AsyncVerne()."
                )
            self._gate_client = AsyncGate(
                api_key=self._gate_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._gate_client
