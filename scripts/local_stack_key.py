#!/usr/bin/env python3
"""A throwaway tenant and API key on a LOCAL Nautilus stack, for the integration suite.

    python scripts/local_stack_key.py create <state.json>   register an e2e- tenant, mint keys
    python scripts/local_stack_key.py env    <state.json>   print `export VERNE_…=…` lines
    python scripts/local_stack_key.py revoke <state.json>   revoke the keys

A port of vrn-sdk-node's ``scripts/local-stack-key.mjs``. It registers the way the
dashboard's sign-up form does (Kratos browser flow, then ``/auth/registration/tenant``)
and mints keys through the dashboard API with that session. The email is
``<prefix>@e2e.soft.com`` with ``<prefix> = e2e-sdkpy-<run>`` (``PREFIX_BASE`` changes the
first part), which nautilus' ``make purge-e2e E2E_PREFIXES=<prefix>`` sweeps afterwards.
The state file holds secrets (mode 0600); nothing here prints a key unless you ask for
``env``.

Refuses any API host but api.soft.com / localhost: this is not for production.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx

API = os.environ.get("VERNE_BASE_URL", "http://api.soft.com").rstrip("/")
if urlparse(API).hostname not in ("api.soft.com", "localhost", "127.0.0.1"):
    raise SystemExit(f"refusing non-local API {API}")


def _absorb(jar: Dict[str, str], response: httpx.Response) -> None:
    for line in response.headers.get_list("set-cookie"):
        pair = line.split(";", 1)[0]
        name, _, value = pair.partition("=")
        jar[name.strip()] = value


def _cookie_header(jar: Dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in jar.items())


def _mint_key(session: str, name: str, scopes: List[str]) -> Dict[str, Any]:
    res = httpx.post(
        f"{API}/dashboard/tenant/keys",
        headers={"Cookie": f"ory_kratos_session={session}"},
        json={"name": name, "scopes": scopes},
        timeout=30,
    )
    if res.status_code != 201:
        raise SystemExit(f"key creation: HTTP {res.status_code}")
    key: Dict[str, Any] = res.json()
    return key


def create(path: str) -> None:
    run_id = f"{int(time.time() * 1000):x}{secrets.token_hex(3)}"
    prefix = f"{os.environ.get('PREFIX_BASE', 'e2e-sdkpy')}-{run_id}"
    password = f"Pw-{secrets.token_hex(6)}-{secrets.token_hex(6)}-9!"
    jar: Dict[str, str] = {}

    flow_res = httpx.get(
        f"{API}/auth/self-service/registration/browser?identity_schema=tenant",
        headers={"Accept": "application/json"},
        timeout=30,
    )
    _absorb(jar, flow_res)
    if not flow_res.is_success:
        raise SystemExit(f"registration flow: HTTP {flow_res.status_code}")
    flow = flow_res.json()
    csrf = next(
        (
            n["attributes"]["value"]
            for n in flow["ui"]["nodes"]
            if n.get("attributes", {}).get("name") == "csrf_token"
        ),
        None,
    )

    reg = httpx.post(
        f"{API}/auth/registration/tenant",
        headers={"Accept": "application/json", "Cookie": _cookie_header(jar)},
        json={
            "flow": flow["id"],
            "csrf_token": csrf,
            "password": password,
            "traits": {
                "email": f"{prefix}@e2e.soft.com",
                "locale": "en",
                "display_name": f"SDK Python {run_id}",
            },
        },
        timeout=30,
    )
    _absorb(jar, reg)
    try:
        body = reg.json()
    except ValueError:
        body = {}
    session = jar.get("ory_kratos_session")
    identity_id = (((body or {}).get("session") or {}).get("identity") or {}).get("id")
    if not identity_id or not session:
        raise SystemExit(f"registration: HTTP {reg.status_code}")

    scopes = os.environ.get("SCOPES", "gate,clockwork,passepartout").split(",")
    key = _mint_key(session, f"sdkpy-{run_id}", scopes)
    narrow = _mint_key(session, f"sdkpy-{run_id}-narrow", ["clockwork"])

    state = {
        "runId": run_id,
        "prefix": prefix,
        "baseUrl": API,
        "tenantId": identity_id,
        "session": session,
        "keyId": key["id"],
        "key": key["raw_key"],
        "narrowKeyId": narrow["id"],
        "narrowKey": narrow["raw_key"],
        "scopes": scopes,
    }
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(state, fh)
    os.chmod(path, 0o600)
    print(
        f"tenant registered: prefix {prefix}, keys {key['id']} ({','.join(scopes)}) "
        f"and {narrow['id']} (clockwork)"
    )


def env(path: str) -> None:
    with open(path) as fh:
        s = json.load(fh)
    print(f"export VERNE_BASE_URL='{s['baseUrl']}'")
    print(f"export VERNE_API_KEY='{s['key']}'")
    print(f"export VERNE_NARROW_KEY='{s['narrowKey']}'")
    print(f"export VERNE_EMAIL_PREFIX='{s['prefix']}'")


def revoke(path: str) -> None:
    with open(path) as fh:
        s = json.load(fh)
    for key_id in (s.get("keyId"), s.get("narrowKeyId")):
        if not key_id:
            continue
        res = httpx.patch(
            f"{API}/dashboard/tenant/keys/{key_id}",
            headers={"Cookie": f"ory_kratos_session={s['session']}"},
            timeout=30,
        )
        print(f"revoke {key_id}: HTTP {res.status_code}")
    print(f"now sweep: (cd nautilus && E2E_PREFIXES={s['prefix']} make purge-e2e)")


def main(argv: List[str]) -> None:
    if len(argv) != 3 or argv[1] not in ("create", "env", "revoke"):
        raise SystemExit("usage: local_stack_key.py create|env|revoke <state.json>")
    {"create": create, "env": env, "revoke": revoke}[argv[1]](argv[2])


if __name__ == "__main__":
    main(sys.argv)
