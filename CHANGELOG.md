# Changelog

All notable changes to `vernesoft`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [1.4.0] — unreleased

### Added

- **One key for every service**: `Verne(api_key=…)` / `AsyncVerne(api_key=…)`. Keys are
  `vrn_…` with scopes; the per-service keys (`relay=`, `gate=`, …) still work and
  override `api_key`.
- **Organizations, roles and members**: `gate.organizations` (`create`, `list`, `get`,
  `update`, `delete`), `.roles` (`create`, `list`, `get`, `update`, `delete`),
  `.members` (`add`, `list`, `update`, `remove`), and
  `gate.identities.list_organizations()`. `members.update(expires_at=…)` tells "keep"
  (left out, or `NOT_GIVEN`) from "remove" (`None`).
- **Permission checks in an organization**: `gate.organizations.authorize(org_id,
  identity_id, permission)` and `.can(…)` → `bool`. `AuthorizeResult` gains `role`; the
  organization `reason` values are exported as `REASON_*` constants.
- **Audit log**: `gate.audit_log.list()` with filters (`from_` for the `from` filter) and
  cursor paging.
- **Automatic deletion rules**: `gate.lifecycle` (`list_rules`, `set_rule`,
  `delete_rule`, `preview_rule`, `list_actions`).
- **Signed tokens (JWT)**: `gate.tokens.create_signed(session_token)`,
  `gate.tokens.verify_signed(token, tenant_id=…)` and the standalone
  `GateTokenVerifier` / `AsyncGateTokenVerifier` — ES256 against the tenant's JWKS,
  issuer checked. Needs the new extra `vernesoft[jwt]` (`cryptography`). Failures
  raise `VerneTokenError` with a `reason`.
- **Sessions**: `gate.sessions` (`list`, `revoke`, `revoke_all`, `check`). `check()` is
  `GET /v1/gate/auth/session`: `mfa_satisfied`, `orgs`, and `403 mfa_required`.
- **Custom metadata**: `gate.identities.get_metadata()` / `update_metadata()`.
- **Social-login return**: `gate.settings.get_return_urls()` / `update_return_urls()`,
  `gate.exchange_oidc_code()`, `gate.create_registration_flow()`, and `return_to`,
  `state`, `aal`, `session_token` on `gate.create_login_flow()`.
- `orgs` / `orgs_truncated` on Gate and Passepartout introspection results.
- `clockwork.usage()`; `Execution.attempt`.
- `Identity` keeps the whole answer in `raw` and types `created_at`, `updated_at`,
  `metadata_public`, `verifiable_addresses`, …
- `VerneAPIError.details` (the extra members of the error: `plan`, `limit`,
  `required_aal`, …), `.retry_after` and `.body`.
- `pytest -m integration`: an opt-in suite against a running stack, and
  `scripts/local_stack_key.py` to make a throwaway local tenant for it.

### Changed

- Aligned with the API changes of October 2026: `AuthorizeResult` gains `message`, and
  `REASON_OWNED_BY_TENANT`, `REASON_NOT_OWNED_BY_TENANT` and
  `REASON_NOT_A_KNOWN_IDENTITY` join the constants (with `REASON_SUBJECT_INACTIVE`, the
  codes of a check on a resource that is not an organization); the sentence that check
  used to put in `reason` is now `message`. `sessions.revoke_all()` is documented as
  succeeding for a user with no session (`204`, it was a `404`). Docs and comments name
  `invalid_payload` (not `invalid_request`) for a malformed token request and treat
  Clockwork errors as the standard envelope; the string-form and numeric-code parsing
  stays as a fallback. Identities no longer carry `metadata_public.verne_tenant_id`;
  the SDK never read it.

### Fixed

- `gate.tokens.create()` sent the key in the request body without an `Authorization`
  header, which the API answers with `401`. It now sends the header like every other
  call, and no longer puts the key in the body.
- A `429` was retried after waiting out any `Retry-After` — for Relay's monthly limit,
  up to a month. Only a `Retry-After` of 60 seconds or less is waited out now; the
  monthly limit (`RELAY_MESSAGE_LIMIT_REACHED`) is raised at once with `retry_after`.
- An error body whose `error` is a string (Clockwork) lost its message, and one with a
  numeric `code` (identity service) leaked the number as the code; both now give
  `code == "unknown"` and the real sentence. A body that is not JSON gives `HTTP
  <status>`. `VerneAPIError.request_id` is `None`, not `""`, when there is none.
- Types: identity traits are `email` and `locale` — the `custom_data` and `tenant_id`
  traits never existed in the API (creating with `custom_data` is a `400`); use custom
  metadata. Introspection fields other than `active` are optional (an inactive token is
  just `active=False`).
- `gate.get_enabled_providers()` (a public endpoint) no longer sends the API key.
- Docs: keys are `vrn_…` with no test/live environment; the Relay idempotency window is
  12 hours, not 24; `409` means "already exists in your account".
- Ids in paths are URL-encoded.

## [1.3.0] — 2026-07-25

### Added

- Clockwork (Cron-as-a-Service): `clockwork.jobs` and `clockwork.delayed`.

## [1.2.0] — 2026-07-24

### Added

- Passepartout (Telegram sign-in): `login_start`, `login_status`, `introspect`.
