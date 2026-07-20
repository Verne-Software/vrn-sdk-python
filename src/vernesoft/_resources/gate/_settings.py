from __future__ import annotations

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import SecuritySettings

_PATH_SECURITY = "/v1/gate/settings/security"


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