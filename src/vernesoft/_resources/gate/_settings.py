from __future__ import annotations

from typing import List

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import OidcProvider, SecuritySettings

_PATH_SECURITY = "/v1/gate/settings/security"
_PATH_OIDC_PROVIDERS = "/v1/gate/settings/oidc-providers"


class SettingsResource:
    """Synchronous Gate tenant settings operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def get_security(self) -> SecuritySettings:
        """Return the tenant's security settings (passwordless / MFA)."""
        data = self._http.get(_PATH_SECURITY)
        return SecuritySettings.from_dict(data)

    def update_security(self, *, passwordless_enabled: bool, mfa_enabled: bool) -> None:
        """Replace the tenant's security settings.

        Both fields are required — the update is a full replacement, not a merge.
        """
        self._http.put(
            _PATH_SECURITY,
            body={
                "passwordless_enabled": passwordless_enabled,
                "mfa_enabled": mfa_enabled,
            },
        )

    def get_oidc_providers(self) -> List[OidcProvider]:
        """Return the tenant's social login (OIDC) providers and their state.

        Covers every provider Gate supports, regardless of whether it is
        enabled.
        """
        data = self._http.get(_PATH_OIDC_PROVIDERS)
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]

    def update_oidc_providers(
        self, providers: List[OidcProvider]
    ) -> List[OidcProvider]:
        """Set the enabled flag for one or more social login providers.

        Any provider omitted from ``providers`` is left unchanged. Returns the
        full, updated provider list.
        """
        data = self._http.put(
            _PATH_OIDC_PROVIDERS,
            body={"providers": [p.to_dict() for p in providers]},
        )
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]


class AsyncSettingsResource:
    """Asynchronous Gate tenant settings operations."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def get_security(self) -> SecuritySettings:
        """Return the tenant's security settings (passwordless / MFA)."""
        data = await self._http.get(_PATH_SECURITY)
        return SecuritySettings.from_dict(data)

    async def update_security(self, *, passwordless_enabled: bool, mfa_enabled: bool) -> None:
        """Replace the tenant's security settings.

        Both fields are required — the update is a full replacement, not a merge.
        """
        await self._http.put(
            _PATH_SECURITY,
            body={
                "passwordless_enabled": passwordless_enabled,
                "mfa_enabled": mfa_enabled,
            },
        )

    async def get_oidc_providers(self) -> List[OidcProvider]:
        """Return the tenant's social login (OIDC) providers and their state.

        Covers every provider Gate supports, regardless of whether it is
        enabled.
        """
        data = await self._http.get(_PATH_OIDC_PROVIDERS)
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]

    async def update_oidc_providers(
        self, providers: List[OidcProvider]
    ) -> List[OidcProvider]:
        """Set the enabled flag for one or more social login providers.

        Any provider omitted from ``providers`` is left unchanged. Returns the
        full, updated provider list.
        """
        data = await self._http.put(
            _PATH_OIDC_PROVIDERS,
            body={"providers": [p.to_dict() for p in providers]},
        )
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]