from __future__ import annotations

from typing import Any, List

from ..._core.http import AsyncHttpClient, SyncHttpClient
from ._types import OidcProvider, SecuritySettings

_PATH_SECURITY = "/v1/gate/settings/security"
_PATH_OIDC_PROVIDERS = "/v1/gate/settings/oidc-providers"
_PATH_RETURN_URLS = "/v1/gate/settings/return-urls"


def _return_urls(data: Any) -> List[str]:
    urls = data.get("return_urls") if isinstance(data, dict) else None
    return [str(u) for u in urls] if isinstance(urls, list) else []


class SettingsResource:
    """Synchronous Gate tenant settings operations."""

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def get_security(self) -> SecuritySettings:
        """Return the tenant's security settings (passwordless / MFA). With
        ``mfa_enabled``, ``sessions.check()`` refuses a session without a second factor
        (``403 mfa_required``)."""
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

    def update_oidc_providers(self, providers: List[OidcProvider]) -> List[OidcProvider]:
        """Set the enabled flag for one or more social login providers.

        Any provider omitted from ``providers`` is left unchanged. Returns the
        full, updated provider list.
        """
        data = self._http.put(
            _PATH_OIDC_PROVIDERS,
            body={"providers": [p.to_dict() for p in providers]},
        )
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]

    def get_return_urls(self) -> List[str]:
        """The project's social-login return URLs — the addresses on your backend that
        receive the user (with a one-time ``code``) after a social login. The first is
        the default."""
        return _return_urls(self._http.get(_PATH_RETURN_URLS))

    def update_return_urls(self, urls: List[str]) -> List[str]:
        """Replace the project's return URLs and return them as they will be matched —
        exactly, never by prefix.

        At most 10; an empty list switches the feature off. ``https`` only, except
        ``http://localhost`` and ``http://127.0.0.1``; no query, fragment, ``@`` or
        wildcard (``400 invalid_payload`` names the entry).
        """
        return _return_urls(self._http.put(_PATH_RETURN_URLS, body={"return_urls": list(urls)}))


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
        """Return the tenant's social login (OIDC) providers and their state."""
        data = await self._http.get(_PATH_OIDC_PROVIDERS)
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]

    async def update_oidc_providers(self, providers: List[OidcProvider]) -> List[OidcProvider]:
        """Set the enabled flag for one or more social login providers."""
        data = await self._http.put(
            _PATH_OIDC_PROVIDERS,
            body={"providers": [p.to_dict() for p in providers]},
        )
        return [OidcProvider.from_dict(p) for p in data.get("providers", [])]

    async def get_return_urls(self) -> List[str]:
        """The project's social-login return URLs. See
        :meth:`SettingsResource.get_return_urls`."""
        return _return_urls(await self._http.get(_PATH_RETURN_URLS))

    async def update_return_urls(self, urls: List[str]) -> List[str]:
        """Replace the project's return URLs. See
        :meth:`SettingsResource.update_return_urls`."""
        return _return_urls(
            await self._http.put(_PATH_RETURN_URLS, body={"return_urls": list(urls)})
        )
