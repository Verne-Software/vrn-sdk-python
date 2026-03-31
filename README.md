# Verne Software Python SDK

[![PyPI version](https://img.shields.io/pypi/v/vernesoft.svg)](https://pypi.org/project/vernesoft/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

The official Python library for the [Verne Nautilus](https://vernesoft.com) platform.

> **Server-side only.** API keys carry full service access and must never be used in client-side or browser contexts.

## Requirements

Python 3.9 or later.

## Installation

```bash
pip install vernesoft
```

## Quick Start

```python
from vernesoft import Verne

verne = Verne(
    relay=os.environ["VERNE_RELAY_KEY"],
    gate=os.environ["VERNE_GATE_KEY"],
)
```

You can also instantiate services independently if you only need one:

```python
from vernesoft import Relay, Gate

relay = Relay(api_key=os.environ["VERNE_RELAY_KEY"])
gate  = Gate(api_key=os.environ["VERNE_GATE_KEY"])
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
    idempotency_key="evt_abc",  # prevent duplicate delivery within 24h
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

## Gate — Auth-as-a-Service

### Identity Management

Manage your end-users. The `tenant_id` is automatically scoped to your API key.

```python
# Create a user
identity = verne.gate.identities.create(
    schema_id="user",
    traits={
        "email": "user@example.com",
        "custom_data": {"role": "editor"},
    },
    credentials={"password": {"config": {"password": "StrongPassword123!"}}},
    state="active",
)

# Get a user
verne.gate.identities.get(identity.id)

# Update a user (JSON Patch — RFC 6902)
verne.gate.identities.patch(identity.id, [
    {"op": "replace", "path": "/traits/custom_data/role", "value": "admin"},
])

# Delete a user
verne.gate.identities.delete(identity.id)
```

### Access Tokens

Exchange your long-lived API key for a short-lived access token:

```python
token = verne.gate.tokens.create(
    subject="usr_123",
    scopes=["gate.tokens.read"],  # optional
    ttl_seconds=3600,             # optional, default 3600, max 86400
)

# token.access_token — attach to downstream requests
# token.expires_at   — ISO 8601 expiry
```

Validate a token:

```python
info = verne.gate.tokens.introspect(token.access_token)

if not info.active:
    # token is expired or invalid
    pass
```

### Authorization

Check whether a subject is allowed to perform an action:

```python
decision = verne.gate.authorize(
    subject="usr_123",
    action="relay.messages.read",
    resource="tenant:ten_001",
)

if not decision.allowed:
    raise PermissionError("Forbidden")
```

## Async Support

Every client has an async counterpart — `AsyncVerne`, `AsyncRelay`, `AsyncGate` — with the same interface, where all methods are coroutines:

```python
from vernesoft import AsyncVerne

verne = AsyncVerne(
    relay=os.environ["VERNE_RELAY_KEY"],
    gate=os.environ["VERNE_GATE_KEY"],
)

msg      = await verne.relay.messages.send(event_type="user.created", payload={"id": "usr_123"})
page     = await verne.relay.messages.list(limit=10)
identity = await verne.gate.identities.create(schema_id="user", traits={"email": "a@b.com"})
token    = await verne.gate.tokens.create(subject="usr_123")
decision = await verne.gate.authorize(subject="usr_123", action="relay.messages.read", resource="tenant:ten_001")
```

## Error Handling

All API errors raise `VerneAPIError` with structured fields:

```python
from vernesoft import VerneAPIError, VerneError

try:
    verne.relay.messages.send(event_type="ping", payload={})
except VerneAPIError as e:
    print(e.code)       # e.g. 'invalid_payload', 'unauthorized'
    print(e.status)     # HTTP status code
    print(e.request_id) # include in support requests
except VerneError as e:
    # network failure or timeout
    print(e)
```

## Configuration

Both `Verne` and the per-service clients accept an optional `timeout` in seconds (default `30`):

```python
verne = Verne(
    relay=os.environ["VERNE_RELAY_KEY"],
    timeout=10,
)
```

Individual requests can be cancelled by passing an `httpx` timeout or by closing the client. Per-request timeouts are supported natively through `httpx`:

```python
import httpx
from vernesoft import Relay

relay = Relay(api_key=os.environ["VERNE_RELAY_KEY"], timeout=5)
```

## License

[MIT](LICENSE)
