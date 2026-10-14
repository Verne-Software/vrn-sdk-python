from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ..._core.http import AsyncHttpClient, SyncHttpClient, seg
from ..._core.types import Paginated
from ._types import (
    LifecycleAction,
    LifecycleRule,
    LifecycleRuleKind,
    LifecycleRulePreview,
    LifecycleRules,
)

_PATH_RULES = "/v1/gate/lifecycle/rules"
_PATH_ACTIONS = "/v1/gate/lifecycle/actions"


def _rule_path(kind: str) -> str:
    return f"{_PATH_RULES}/{seg(kind)}"


def _set_body(enabled: bool, params: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    # The server refuses unknown fields: exactly {enabled, params?}. `params` left out
    # (not null) keeps the saved settings.
    body: Dict[str, Any] = {"enabled": enabled}
    if params is not None:
        body["params"] = dict(params)
    return body


def _actions_query(
    status: Optional[str],
    kind: Optional[str],
    identity_id: Optional[str],
    limit: Optional[int],
    cursor: Optional[str],
) -> Dict[str, Any]:
    return {
        "status": status,
        "kind": kind,
        "identity_id": identity_id,
        "limit": limit,
        "cursor": cursor,
    }


class LifecycleResource:
    """Automatic deletion of unconfirmed and inactive accounts, and removal of expired
    roles — four rules per project, all off until you switch them on.

    Rule kinds and their ``params``:

    - ``delete_unverified``: ``delete_after_days`` (2–365), ``warn_before_days``
      (1 to ``delete_after_days - 1``)
    - ``remind_unverified``: ``remind_after_hours`` (1–720)
    - ``expire_roles``: no settings (``{}``)
    - ``delete_inactive``: ``inactive_after_months`` (1–120), ``warn_before_days``
      (7–90), optional ``include_without_address``

    Only ``delete_unverified`` is in the Free plan; switching on another is
    ``403 plan_required``. Bounds are checked by the server (``400 invalid_payload``).
    """

    def __init__(self, http: SyncHttpClient) -> None:
        self._http = http

    def list_rules(self) -> LifecycleRules:
        """All four rules of the key's project, set up or not, and the plan."""
        return LifecycleRules.from_dict(self._http.get(_PATH_RULES))

    def set_rule(
        self,
        kind: LifecycleRuleKind,
        *,
        enabled: bool,
        params: Optional[Mapping[str, Any]] = None,
    ) -> LifecycleRule:
        """Create, change, or switch a rule on or off.

        Leave ``params`` out to keep the saved settings; a first write needs them (except
        ``expire_roles``). Switching off or changing settings cancels what the rule had
        scheduled.
        """
        return LifecycleRule.from_dict(
            self._http.put(_rule_path(kind), body=_set_body(enabled, params))
        )

    def delete_rule(self, kind: LifecycleRuleKind) -> None:
        """Remove a rule and cancel what it scheduled. Succeeds also when there was none."""
        self._http.delete(_rule_path(kind))

    def preview_rule(
        self, kind: LifecycleRuleKind, params: Optional[Mapping[str, Any]] = None
    ) -> LifecycleRulePreview:
        """How many people a rule with these settings would affect right now. Writes
        nothing; works whether or not the rule is on or in your plan. ``expire_roles``
        takes no settings (``params`` left out sends ``{}``)."""
        data = self._http.post(f"{_rule_path(kind)}/preview", body={"params": dict(params or {})})
        return LifecycleRulePreview.from_dict(data)

    def list_actions(
        self,
        *,
        status: Optional[str] = None,
        kind: Optional[LifecycleRuleKind] = None,
        identity_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Paginated[LifecycleAction]:
        """What the rules have scheduled and done, oldest first, cursor-paged.

        :param status: ``pending``, ``done``, ``cancelled`` or ``failed``.
        """
        data = self._http.get(
            _PATH_ACTIONS, params=_actions_query(status, kind, identity_id, limit, cursor)
        )
        return Paginated.from_dict(data, LifecycleAction.from_dict)


class AsyncLifecycleResource:
    """Automatic-deletion rules (async). See :class:`LifecycleResource`."""

    def __init__(self, http: AsyncHttpClient) -> None:
        self._http = http

    async def list_rules(self) -> LifecycleRules:
        """All four rules of the key's project, set up or not, and the plan."""
        return LifecycleRules.from_dict(await self._http.get(_PATH_RULES))

    async def set_rule(
        self,
        kind: LifecycleRuleKind,
        *,
        enabled: bool,
        params: Optional[Mapping[str, Any]] = None,
    ) -> LifecycleRule:
        """Create, change, or switch a rule on or off. ``params`` left out keeps the
        saved settings."""
        return LifecycleRule.from_dict(
            await self._http.put(_rule_path(kind), body=_set_body(enabled, params))
        )

    async def delete_rule(self, kind: LifecycleRuleKind) -> None:
        """Remove a rule and cancel what it scheduled. Succeeds also when there was none."""
        await self._http.delete(_rule_path(kind))

    async def preview_rule(
        self, kind: LifecycleRuleKind, params: Optional[Mapping[str, Any]] = None
    ) -> LifecycleRulePreview:
        """How many people a rule with these settings would affect right now."""
        data = await self._http.post(
            f"{_rule_path(kind)}/preview", body={"params": dict(params or {})}
        )
        return LifecycleRulePreview.from_dict(data)

    async def list_actions(
        self,
        *,
        status: Optional[str] = None,
        kind: Optional[LifecycleRuleKind] = None,
        identity_id: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Paginated[LifecycleAction]:
        """What the rules have scheduled and done, oldest first, cursor-paged."""
        data = await self._http.get(
            _PATH_ACTIONS, params=_actions_query(status, kind, identity_id, limit, cursor)
        )
        return Paginated.from_dict(data, LifecycleAction.from_dict)
