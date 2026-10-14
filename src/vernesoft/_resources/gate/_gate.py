from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from ..._core.http import DEFAULT_BASE_URL, AsyncHttpClient, SyncHttpClient, seg
from ._audit_log import AsyncAuditLogResource, AuditLogResource
from ._identities import AsyncIdentitiesResource, IdentitiesResource
from ._lifecycle import AsyncLifecycleResource, LifecycleResource
from ._organizations import AsyncOrganizationsResource, OrganizationsResource
from ._sessions import AsyncSessionsResource, SessionsResource
from ._settings import AsyncSettingsResource, SettingsResource
from ._tokens import AsyncTokensResource, TokensResource
from ._types import AuthorizeResult, OidcExchangeResult

_DEFAULT_TIMEOUT = 30.0
_PATH_AUTHORIZE = "/v1/gate/authorize"
_PATH_LOGIN_FLOW = "/v1/gate/auth/login"
_PATH_REGISTRATION_FLOW = "/v1/gate/auth/registration"
_PATH_OIDC_EXCHANGE = "/v1/gate/auth/oidc/exchange"

Aal = Literal["aal1", "aal2"]


def _providers_path(tenant_id: str) -> str:
    return f"/public/gate/providers/{seg(tenant_id)}"


def _authorize_body(
    subject: str, action: str, resource: str, context: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"subject": subject, "action": action, "resource": resource}
    if context is not None:
        body["context"] = context
    return body


class Gate:
    """Synchronous client for the Verne Gate service (sign-in and end users)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = SyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._identities: IdentitiesResource | None = None
        self._tokens: TokensResource | None = None
        self._settings: SettingsResource | None = None
        self._organizations: OrganizationsResource | None = None
        self._sessions: SessionsResource | None = None
        self._audit_log: AuditLogResource | None = None
        self._lifecycle: LifecycleResource | None = None

    @property
    def identities(self) -> IdentitiesResource:
        if self._identities is None:
            self._identities = IdentitiesResource(self._http)
        return self._identities

    @property
    def tokens(self) -> TokensResource:
        if self._tokens is None:
            self._tokens = TokensResource(self._http)
        return self._tokens

    @property
    def settings(self) -> SettingsResource:
        if self._settings is None:
            self._settings = SettingsResource(self._http)
        return self._settings

    @property
    def organizations(self) -> OrganizationsResource:
        if self._organizations is None:
            self._organizations = OrganizationsResource(self._http)
        return self._organizations

    @property
    def sessions(self) -> SessionsResource:
        if self._sessions is None:
            self._sessions = SessionsResource(self._http)
        return self._sessions

    @property
    def audit_log(self) -> AuditLogResource:
        if self._audit_log is None:
            self._audit_log = AuditLogResource(self._http)
        return self._audit_log

    @property
    def lifecycle(self) -> LifecycleResource:
        if self._lifecycle is None:
            self._lifecycle = LifecycleResource(self._http)
        return self._lifecycle

    def authorize(
        self,
        *,
        subject: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizeResult:
        """Ask whether a subject may perform an action on a resource. The answer is
        a decision; your service enforces it.

        - ``resource="organization:<id>"`` — may this end user do ``action`` (a
          permission) in that organization? ``reason`` is one of a fixed set and ``role``
          is the role they hold. Prefer ``gate.organizations.authorize()`` / ``can()``,
          which build the resource.
        - any other resource — only *is* ``subject`` *one of your active end users?*;
          ``reason`` is a sentence for people.

        ``context`` is accepted and ignored by the API today.
        """
        data = self._http.post(
            _PATH_AUTHORIZE, body=_authorize_body(subject, action, resource, context)
        )
        return AuthorizeResult.from_dict(data)

    def get_enabled_providers(self, tenant_id: str) -> List[str]:
        """Return the social login providers currently enabled for a tenant.

        This is a public, unauthenticated endpoint — call it from your login /
        registration page to decide which social buttons to render.
        """
        data = self._http.get(_providers_path(tenant_id), skip_auth=True)
        return list(data.get("providers", []))

    def create_login_flow(
        self,
        *,
        return_to: Optional[str] = None,
        state: Optional[str] = None,
        aal: Optional[Aal] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a Kratos login flow and return it; render its ``ui.nodes`` or post
        credentials to its ``ui.action``.

        :param return_to: one of the project's registered return URLs, exactly as
            registered (``settings.update_return_urls()``); the first is used when absent.
        :param state: an opaque value of yours (1–256 characters of letters, digits,
            ``-``, ``.``, ``_``, ``~``) returned unchanged on the redirect to your return
            URL. Always send one for social login, and check it.
        :param aal: ``"aal2"`` starts a step-up (second factor) flow; needs
            ``session_token``.
        :param session_token: the end user's session token for a step-up, sent as the
            ``X-Session-Token`` header (never in the URL).
        """
        return dict(
            self._http.get(
                _PATH_LOGIN_FLOW,
                params={"return_to": return_to, "state": state, "aal": aal},
                session_token=session_token,
            )
        )

    def create_registration_flow(
        self, *, return_to: Optional[str] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a Kratos registration flow (``return_to`` and ``state`` as for
        :meth:`create_login_flow`). Refused with ``402 ACTIVE_USER_LIMIT_REACHED`` when
        the account is past its active-user limit."""
        return dict(
            self._http.get(_PATH_REGISTRATION_FLOW, params={"return_to": return_to, "state": state})
        )

    def exchange_oidc_code(self, code: str) -> OidcExchangeResult:
        """Exchange the one-time ``code`` your return URL received after a social login
        for the user's session. The code works once, for about 60 seconds, and only with
        a key of the project that started the login (otherwise ``404``). Keep the session
        token server-side."""
        return OidcExchangeResult.from_dict(
            self._http.post(_PATH_OIDC_EXCHANGE, body={"code": code})
        )


class AsyncGate:
    """Asynchronous client for the Verne Gate service (sign-in and end users)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._http = AsyncHttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self._identities: AsyncIdentitiesResource | None = None
        self._tokens: AsyncTokensResource | None = None
        self._settings: AsyncSettingsResource | None = None
        self._organizations: AsyncOrganizationsResource | None = None
        self._sessions: AsyncSessionsResource | None = None
        self._audit_log: AsyncAuditLogResource | None = None
        self._lifecycle: AsyncLifecycleResource | None = None

    @property
    def identities(self) -> AsyncIdentitiesResource:
        if self._identities is None:
            self._identities = AsyncIdentitiesResource(self._http)
        return self._identities

    @property
    def tokens(self) -> AsyncTokensResource:
        if self._tokens is None:
            self._tokens = AsyncTokensResource(self._http)
        return self._tokens

    @property
    def settings(self) -> AsyncSettingsResource:
        if self._settings is None:
            self._settings = AsyncSettingsResource(self._http)
        return self._settings

    @property
    def organizations(self) -> AsyncOrganizationsResource:
        if self._organizations is None:
            self._organizations = AsyncOrganizationsResource(self._http)
        return self._organizations

    @property
    def sessions(self) -> AsyncSessionsResource:
        if self._sessions is None:
            self._sessions = AsyncSessionsResource(self._http)
        return self._sessions

    @property
    def audit_log(self) -> AsyncAuditLogResource:
        if self._audit_log is None:
            self._audit_log = AsyncAuditLogResource(self._http)
        return self._audit_log

    @property
    def lifecycle(self) -> AsyncLifecycleResource:
        if self._lifecycle is None:
            self._lifecycle = AsyncLifecycleResource(self._http)
        return self._lifecycle

    async def authorize(
        self,
        *,
        subject: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AuthorizeResult:
        """Ask whether a subject may perform an action on a resource. See
        :meth:`Gate.authorize`."""
        data = await self._http.post(
            _PATH_AUTHORIZE, body=_authorize_body(subject, action, resource, context)
        )
        return AuthorizeResult.from_dict(data)

    async def get_enabled_providers(self, tenant_id: str) -> List[str]:
        """Return the social login providers currently enabled for a tenant (public,
        unauthenticated endpoint)."""
        data = await self._http.get(_providers_path(tenant_id), skip_auth=True)
        return list(data.get("providers", []))

    async def create_login_flow(
        self,
        *,
        return_to: Optional[str] = None,
        state: Optional[str] = None,
        aal: Optional[Aal] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a Kratos login flow. See :meth:`Gate.create_login_flow`."""
        return dict(
            await self._http.get(
                _PATH_LOGIN_FLOW,
                params={"return_to": return_to, "state": state, "aal": aal},
                session_token=session_token,
            )
        )

    async def create_registration_flow(
        self, *, return_to: Optional[str] = None, state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start a Kratos registration flow. See :meth:`Gate.create_registration_flow`."""
        return dict(
            await self._http.get(
                _PATH_REGISTRATION_FLOW, params={"return_to": return_to, "state": state}
            )
        )

    async def exchange_oidc_code(self, code: str) -> OidcExchangeResult:
        """Exchange a social login's one-time ``code`` for the user's session. See
        :meth:`Gate.exchange_oidc_code`."""
        return OidcExchangeResult.from_dict(
            await self._http.post(_PATH_OIDC_EXCHANGE, body={"code": code})
        )
