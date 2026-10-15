# Verne Software Python SDK

[![PyPI version](https://img.shields.io/pypi/v/vernesoft.svg)](https://pypi.org/project/vernesoft/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

The official Python library for [Nautilus by Verne Software](https://vernesoft.com): sign-in and users, webhook delivery, cron jobs and Telegram sign-in, behind one API key. Nautilus runs on servers in France. Documentation: [docs.vernesoft.com](https://docs.vernesoft.com).

> **Server-side only.** API keys carry full access to the APIs they were created for and must never be used in browser or client-side code.

## Requirements

Python 3.9 or later.

## Installation

```bash
pip install vernesoft
# with offline verification of Gate signed tokens (adds `cryptography`):
pip install "vernesoft[jwt]"
```

## Quick Start

```python
import os
from vernesoft import Verne

verne = Verne(api_key=os.environ["VERNE_API_KEY"])

verne.relay.messages.send(event_type="user.created", payload={"id": "usr_123"})
verne.gate.organizations.create(name="Acme")
```

### API keys

Create a key on **Dashboard → Keys** and tick the APIs it may call — its **scopes**: `relay`, `gate`, `clockwork`, `passepartout`. A key looks like `vrn_9f8a7…` and does not name an API. Pass it once as `api_key`; the client sends it as `Authorization: Bearer …` to every service.

- A call to an API the key has no scope for is refused by the API with `403`, code `forbidden`, message `This API key is not authorized for <API>.` The SDK does not check scopes itself.
- To use a different key for one service, pass it as `relay=`, `gate=`, `clockwork=` or `passepartout=`; it overrides `api_key` for that service only.
- There is **no test or live mode and no sandbox**: every key acts on your real data. Use a separate key per environment.
- Keys made before scopes existed (`vrn_gate_…`, `vrn_relay_…`, …) keep working, for the one API they name.

You can also instantiate one service on its own:

```python
from vernesoft import Clockwork, Gate

gate = Gate(api_key=os.environ["VERNE_API_KEY"])
clockwork = Clockwork(api_key=os.environ["VERNE_API_KEY"])
```

## Relay — Webhooks-as-a-Service

Send events to all subscribed endpoints:

```python
msg = verne.relay.messages.send(
    event_type="user.created",
    payload={"id": "usr_123"},
)
```

Optional parameters:

```python
msg = verne.relay.messages.send(
    event_type="order.placed",
    payload={"order_id": "999"},
    idempotency_key="evt_abc",  # a repeat within 12 hours returns the original message
    channels=["team-a"],        # restrict to specific endpoint channels
)
```

List previously sent events:

```python
page = verne.relay.messages.list(limit=20, event_type="user.created")

print(page.data)        # list[Message]
print(page.has_more)    # bool
print(page.next_cursor) # pass to the next call to paginate
```

## Gate — sign-in and users

### Identities

Manage your end users. They are kept apart per tenant: the same address at another tenant is a different person.

```python
# Create a user (traits are `email` and, optionally, `locale`)
identity = verne.gate.identities.create(
    traits={"email": "user@example.com"},
    credentials={"password": {"config": {"password": "StrongPassword123!"}}},
)
# A second user with the same address in your account is a 409 `conflict`.

# Get, update (JSON Patch — RFC 6902), delete
verne.gate.identities.get(identity.id)
verne.gate.identities.patch(identity.id, [
    {"op": "replace", "path": "/traits/email", "value": "new@example.com"},
])
verne.gate.identities.delete(identity.id)

# Activate / deactivate (an inactive user cannot sign in; nothing is deleted)
verne.gate.identities.deactivate(identity.id)
verne.gate.identities.activate(identity.id)

# Resend the email verification link
verne.gate.identities.resend_verification(identity.id)
```

Your own fields about a user go in **custom metadata**, not in traits:

```python
verne.gate.identities.update_metadata(identity.id, {"plan": "pro", "seats": 5})  # merged
verne.gate.identities.update_metadata(identity.id, {"seats": None})              # removes `seats`
metadata = verne.gate.identities.get_metadata(identity.id)                      # {"plan": "pro"}
```

`identity.raw` keeps the whole object the identity service returned, for the fields the SDK does not type.

### Organizations, roles and members

Group your end users into organizations (their teams, workspaces, companies). A **role** is a named set of permissions inside one organization; a **member** holds one role. Everything acts on the project the key belongs to. Gate keeps this data and reports it; it does not enforce it — ask it.

```python
from vernesoft import NOT_GIVEN

org = verne.gate.organizations.create(name="Acme")

admin = verne.gate.organizations.roles.create(
    org.id,
    name="admin",                                    # lowercase, digits, _ and -
    permissions=["invoices:read", "invoices:write"], # lowercase segments joined by `:`
)

verne.gate.organizations.members.add(
    org.id,
    identity_id=identity.id,
    role_id=admin.id,
    expires_at="2027-01-31T23:59:59Z",  # optional (str or datetime): the membership ends then
)

# Change the role or the deadline: leave expires_at out (or NOT_GIVEN) to keep it,
# None to remove it, a time to set it
verne.gate.organizations.members.update(org.id, identity.id, expires_at=None)

# Lists are cursor-paged: loop while has_more, passing next_cursor as cursor
page = verne.gate.organizations.members.list(org.id, limit=50)
page.data, page.has_more, page.next_cursor

# A user's organizations, with role and permissions in each
held = verne.gate.identities.list_organizations(identity.id)
```

A role somebody holds cannot be deleted (`409 conflict`); a second role of the same name in one organization is `409 conflict`; past 100 roles, `409 limit_reached`.

#### Checking a permission

```python
if not verne.gate.organizations.can(org.id, identity.id, "invoices:write"):
    raise PermissionError("Forbidden")

# Or the full decision:
decision = verne.gate.organizations.authorize(org.id, identity.id, "invoices:write")
# AuthorizeResult(allowed=True, decision_id='dec_…', reason='member_with_permission', role='admin')
```

`reason` is one of `member_with_permission`, `member_without_permission`, `not_a_member`, `subject_inactive`, `no_such_organization` (constants `vernesoft.REASON_*`); `role` is set when the user is a member. The match is exact (no wildcards) and live. A permission no role could hold (`Invoices:*`, the `nautilus:` prefix) raises `400 invalid_payload`, never `False`.

`gate.authorize(subject=…, action=…, resource=…)` is the same endpoint; with any resource that is not `organization:<id>` it only says whether `subject` is one of your active end users. Its `reason` is a code too: `owned_by_tenant` (the one `allowed=True`), `subject_inactive`, `not_owned_by_tenant`, `not_a_known_identity` (constants `vernesoft.REASON_*`). The sentence a person would read is in `message`, for your logs — its wording can change, `reason` is the contract.

```python
decision = verne.gate.authorize(subject=identity.id, action="read", resource="doc:1")
# AuthorizeResult(allowed=True, decision_id='dec_…', reason='owned_by_tenant', role=None, message='subject `…` is an identity owned by tenant `…`')
```

### Sessions

```python
# Is this session good enough to act on? (the one call to gate your routes on)
check = verne.gate.sessions.check(session_token)
# SessionCheck(active, aal, mfa_required, mfa_satisfied, identity_id, orgs=[OrgClaim(id, role, permissions)])

sessions = verne.gate.sessions.list(identity.id)
verne.gate.sessions.revoke(sessions[0].id)  # one device
verne.gate.sessions.revoke_all(identity.id) # everywhere
```

`revoke_all()` succeeds also when the user has no session, so a "log out everywhere" button can be pressed twice. An id that is not one of your users (another account's, unknown, or one you deleted) is `403 forbidden`.

With MFA required, `check()` raises a `VerneAPIError` with code `mfa_required` and `details["required_aal"] == "aal2"`; start a step-up flow. A dead, foreign or unknown session is `401`.

```python
from vernesoft import VerneAPIError

try:
    check = verne.gate.sessions.check(session_token)
except VerneAPIError as e:
    if e.code == "mfa_required":
        flow = verne.gate.create_login_flow(aal="aal2", session_token=session_token)
    else:
        raise
```

### Signed tokens (JWT)

For a platform that verifies signatures instead of calling Gate (Supabase, an API gateway). Verification needs `pip install "vernesoft[jwt]"`.

```python
signed = verne.gate.tokens.create_signed(session_token)  # no API key involved

claims = verne.gate.tokens.verify_signed(signed.token, tenant_id=os.environ["VERNE_TENANT_ID"])
claims.sub   # the end user's id
claims.orgs  # [OrgClaim(id, role, permissions)], as of when the token was made
```

Verification is offline, against your tenant's public keys (fetched once, cached, refetched when a new key appears). It always checks the issuer is **your** tenant, and refuses anything but ES256, a bad signature, an expired token — with a `VerneTokenError` whose `reason` says which (`wrong_issuer`, `unsupported_alg`, `bad_signature`, `expired`, …). To verify where you have no Gate client:

```python
from vernesoft import GateTokenVerifier  # AsyncGateTokenVerifier for asyncio

verifier = GateTokenVerifier(tenant_id=os.environ["VERNE_TENANT_ID"])
claims = verifier.verify(token)
```

A signed token lives **15 minutes** and **cannot be revoked**; its `orgs` are as old as the token. For anything that must follow a revocation or a role change at once, use `sessions.check()`, introspection or `organizations.can()`.

### Audit log

```python
from datetime import datetime, timedelta, timezone

page = verne.gate.audit_log.list(
    action="organization.member_added",
    from_=datetime.now(timezone.utc) - timedelta(days=7),  # the `from` filter
    limit=50,
)
# newest first; each entry: id, occurred_at, action, actor, target, project_id, details, ip, user_agent
```

Any key with the `gate` scope reads the **whole** log, including your team members' IP addresses and user agents. Keep `gate` keys on your backend.

### Automatic deletion of inactive accounts

```python
rules = verne.gate.lifecycle.list_rules()  # rules.tier, rules.rules (all four kinds)

preview = verne.gate.lifecycle.preview_rule(
    "delete_unverified", {"delete_after_days": 14, "warn_before_days": 3}
)  # preview.matching_now, preview.capped — look before you switch it on

verne.gate.lifecycle.set_rule(
    "delete_unverified",
    enabled=True,
    params={"delete_after_days": 14, "warn_before_days": 3},
)

actions = verne.gate.lifecycle.list_actions(status="pending")
verne.gate.lifecycle.delete_rule("delete_unverified")
```

Only `delete_unverified` is in the Free plan; switching on another rule is `403 plan_required`.

### Settings

```python
security = verne.gate.settings.get_security()
# Both fields are required — the update is a full replacement, not a merge.
verne.gate.settings.update_security(passwordless_enabled=True, mfa_enabled=False)

# Social login: where your backend receives the user (matched exactly)
verne.gate.settings.update_return_urls(["https://app.example.com/auth/callback"])
flow = verne.gate.create_login_flow(state=csrf_bound_value)  # then, at your callback:
result = verne.gate.exchange_oidc_code(code)                 # result.session_token, result.session
```

### Access tokens

Short-lived opaque tokens for a user or a service account:

```python
token = verne.gate.tokens.create(
    subject="usr_123",
    ttl_seconds=3600,  # optional, default 3600, max 86400
)

info = verne.gate.tokens.introspect(token.access_token)
if not info.active:
    ...  # expired, unknown, or its user is deactivated or deleted — every other field is None
# For an end user, info.orgs lists their organizations, read now.
```

## Passepartout — Telegram sign-in

```python
start = verne.passepartout.login_start()
# send the user to start.deep_link, then poll:
status = verne.passepartout.login_status(start.nonce)
if status.status == "completed":
    info = verne.passepartout.introspect(status.access_token)
    info.orgs  # the user's organizations in your project
```

## Clockwork — Cron-as-a-Service

Schedule recurring HTTP callbacks with cron expressions, or one-shot jobs at a future time.

### Cron Jobs

```python
job = verne.clockwork.jobs.create(
    name="nightly-report",
    schedule="0 2 * * *",              # standard cron expression
    url="https://example.com/hooks/report",
    method="POST",                     # optional, defaults server-side
    headers={"X-Api-Key": "secret"},   # optional
    body='{"kind":"report"}',          # optional
)

jobs = verne.clockwork.jobs.list()                                       # list[CronJob]
verne.clockwork.jobs.update(job.id, schedule="0 3 * * *", is_active=False)  # partial
executions = verne.clockwork.jobs.executions(job.id)  # list[Execution], one row per attempt
verne.clockwork.jobs.delete(job.id)
```

### Delayed Jobs

One-shot jobs that fire once at `run_at`:

```python
delayed = verne.clockwork.delayed.create(
    name="welcome-email",
    run_at="2026-07-26T09:00:00Z",     # ISO 8601 timestamp
    url="https://example.com/send",
    body='{"template":"welcome"}',      # optional
)

verne.clockwork.delayed.list()                  # list[DelayedJob]
verne.clockwork.delayed.executions(delayed.id)  # list[Execution]
verne.clockwork.delayed.cancel(delayed.id)
```

### Usage

```python
usage = verne.clockwork.usage()
# ClockworkUsage(plan='free', cron=CronUsage(active=3, limit=10), delayed=DelayedUsage(pending=12, limit=100))
```

## Async Support

Every client has an async counterpart — `AsyncVerne`, `AsyncRelay`, `AsyncGate`, `AsyncPassepartout`, `AsyncClockwork` — with the same interface, where all methods are coroutines:

```python
from vernesoft import AsyncVerne

verne = AsyncVerne(api_key=os.environ["VERNE_API_KEY"])

msg      = await verne.relay.messages.send(event_type="user.created", payload={"id": "usr_123"})
org      = await verne.gate.organizations.create(name="Acme")
allowed  = await verne.gate.organizations.can(org.id, identity_id, "invoices:write")
usage    = await verne.clockwork.usage()
```

## Error Handling

API errors raise `VerneAPIError`:

```python
from vernesoft import VerneAPIError, VerneError

try:
    verne.gate.organizations.members.add(org_id, identity_id=identity_id, role_id=role_id)
except VerneAPIError as e:
    e.status       # HTTP status
    e.code         # e.g. 'conflict' — branch on status + code
    str(e)         # a sentence to show a person (also e.message)
    e.details      # extra members of the error, e.g. {"plan": ..., "limit": ..., "current": ...}
    e.retry_after  # seconds, when the response had Retry-After
    e.request_id   # include in support requests (None when the response had none)
except VerneError as e:
    ...            # network failure or timeout
```

| Status | `code` | Meaning |
|:--|:--|:--|
| 400 | `invalid_payload` | Something in the request is malformed; the message says what. |
| 401 | `unauthorized` | No key, or a revoked or invalid one; for a session, a dead session. |
| 402 | `ACTIVE_USER_LIMIT_REACHED`, `UPGRADE_REQUIRED`, `JOB_LIMIT_REACHED`, `PROJECT_LIMIT_REACHED`, `BILLING_HARD_BLOCKED`, `SUBSCRIPTION_PAST_DUE`, `payment_required` | A plan or billing limit. Does not lift by waiting — the SDK never retries it. |
| 403 | `forbidden` | The key lacks the scope for this API (the message names it), or the resource is not yours. |
| 403 | `plan_required`, `mfa_required`, `account_disabled` | A rule not in your plan; a second factor owed; a deactivated Telegram user. |
| 404 | `not_found` | No such thing in your project. |
| 409 | `conflict`, `limit_reached` | It already exists **in your account** (an end user with that address, a role name, a membership), a role still held, or a cap reached. |
| 429 | `rate_limited`, `RELAY_MESSAGE_LIMIT_REACHED` | Too fast, or Relay's monthly limit (read `retry_after`). |
| 5xx | `upstream_unavailable`, `internal_error` | Retry; quote `request_id` to support. |

Codes are an open set; treat unknown ones generically. Every API route, Clockwork's included, answers in this envelope with a string `code` and a `request_id`. A body in another shape (one that did not come from the API — a proxy in between, an identity-service answer passed through on `/auth/*`) still raises a `VerneAPIError`, with `code == "unknown"` and its sentence as the message; `e.body` keeps the raw parsed body.

**Retries.** A `POST` that gets a short `429` (a `Retry-After` of 60 seconds or less, or none) is retried once after waiting. Relay's monthly limit (`429 RELAY_MESSAGE_LIMIT_REACHED`, `Retry-After` until the 1st of next month) and every `402` are raised at once.

Network failures and timeouts raise a base `VerneError`; a refused signed token raises `VerneTokenError`.

## Configuration

`Verne` and the per-service clients accept `base_url` and a `timeout` in seconds (default `30`):

```python
verne = Verne(api_key=os.environ["VERNE_API_KEY"], timeout=10)
```

## Development

```bash
pip install -e ".[dev]"
pytest          # unit tests (no network); the integration suite is deselected
mypy src/
ruff check src/ tests/
```

### Integration tests

`pytest -m integration` runs every resource against a real Nautilus stack. It is opt-in, and skipped without a key; it creates end users, an organization and settings changes, and removes them again.

| Variable | |
|:--|:--|
| `VERNE_API_KEY` | A key with the scopes `gate`, `clockwork`, `passepartout`. Required. |
| `VERNE_BASE_URL` | Default `http://api.soft.com` (the local stack). Any other host needs `VERNE_ALLOW_REMOTE=1`. |
| `VERNE_EMAIL_PREFIX` | Every end user created is `<prefix>-<name>@e2e.soft.com`. |
| `VERNE_NARROW_KEY` | Optional: a key **without** the `gate` scope, to check the `403`. |

Against a local stack, `scripts/local_stack_key.py` registers a throwaway `e2e-sdkpy-…` tenant and mints the keys:

```bash
python scripts/local_stack_key.py create /tmp/sdk-it.json
eval "$(python scripts/local_stack_key.py env /tmp/sdk-it.json)"
pytest -m integration
python scripts/local_stack_key.py revoke /tmp/sdk-it.json   # then purge the tenant it names
```

## License

[MIT](LICENSE)
