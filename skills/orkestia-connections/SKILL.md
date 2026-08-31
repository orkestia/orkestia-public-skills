---
name: orkestia-connections
description: Create, validate, rotate, disconnect, and pick Orkestia provider connections (connection.*) — the org-owned credential objects every provider-touching domain references by UUID. Use when wiring any external provider (AWS, GCP, Azure, GitHub, Stripe, SQL, social platforms, and others) or when a workflow needs a cloud_connection_uuid.
---

# Orkestia connections

A **CloudConnection** is an org-owned, named credential to an external provider. It is the root object of the platform: runner groups take `cloud_connection_uuid`, registry accounts, network accounts, storage, image-pull auth, GitLab CI bindings, and AI model bindings all resolve to one. Discover the live set with `list_workflow_types(prefix="connection.")` — do not treat any count in this file as frozen.

One featured entry point serves every provider: `connection.setup`. Its schema exposes `field_groups` — fill **only** the group that matches `provider_type`. Common fields live in the `common` group: `provider_type` (required), `connection_name` (recommended). `organization_uuid` is declared on the schema with `source.kind=context`; the MCP token injects it — do not ask the user for it and do not put it in `initial_data`.

## When to load

Load this skill when the user wants to connect a provider, pick a `connection_uuid` / `cloud_connection_uuid` for another domain, re-test a stale connection, rotate credentials, disconnect, refresh social/ads/equipment assets, or when a schema field sources `connection.query`. Load `orkestia-mcp-operating-loop` first if you have not already.

## Use cases

1. Create a provider connection (AWS AssumeRole, GitHub PAT, SQL, Stripe).
2. Connect an OAuth provider (authorize URL → user consent → token exchange).
3. List or get connections and pick a UUID for another domain.
4. Re-validate a stale connection.
5. Rotate credentials without disconnecting.
6. Disconnect and scrub secrets.
7. Refresh provider assets (Meta pages, LinkedIn orgs, YouTube channels, Deere orgs, ads accounts).

## How to

Call `whoami()` once per session. For every mutation below: `get_workflow_schema` → if `has_prerequisites`, `get_workflow_prerequisites` → `start_workflow` → `watch_workflow`. Reads (`read_only: true`) may start immediately. Never log or echo secret fields from schemas (`api_token`, `api_key`, `access_token`, `client_secret`, `webhook_secret`, `service_account_json`, …).

### 1. Create a provider connection

`connection.setup` has `has_prerequisites: true`. Variants include `aws`, `github`, `sql`, `stripe` (full list is `prerequisite_variants` on the schema). The guide fills platform identity server-side (for AWS, the AssumeRole principal).

1. `get_workflow_schema("connection.setup")` — read `field_groups` for the provider; ignore other groups.
2. `get_workflow_prerequisites("connection.setup", variant="<provider>")`.
3. Hand the markdown to the user if they still need to create an IAM role, token, or key.
4. `start_workflow("connection.setup", { …provider group fields only… })`.
5. Watch until terminal. Success output includes `connection_uuid`, `test_passed`, `persisted`.

AWS AssumeRole (no static access keys):

```json
{
  "provider_type": "aws",
  "connection_name": "prod-aws",
  "role_arn": "arn:aws:iam::123456789012:role/orkestia-access",
  "external_ref": "<same-string-as-trust-policy>",
  "regions": ["us-east-1", "us-west-2"]
}
```

If you omit `external_ref`, Orkestia auto-generates one — then the trust policy must be edited to match. Providing your own is cleaner.

GitHub PAT (three credential paths — see `orkestia-github`):

```json
{
  "provider_type": "github",
  "connection_name": "company-github",
  "api_token": "<github-pat>"
}
```

SQL (Postgres v1; `api_token` **is** the database password):

```json
{
  "provider_type": "sql",
  "connection_name": "analytics-pg",
  "host": "db.example.com",
  "database": "app",
  "username": "orkestia_ro",
  "api_token": "<db-password>",
  "dialect": "postgres",
  "port": "5432",
  "ssl_mode": "require"
}
```

Stripe (restricted `rk_…` recommended; `pk_…` rejected; unrelated to paying for Orkestia):

```json
{
  "provider_type": "stripe",
  "connection_name": "store-stripe",
  "api_key": "<restricted-or-secret-key>",
  "webhook_secret": "<whsec-optional>"
}
```

`connection.setup` is **not** a DAG (`get_workflow_dag` returns `is_dag: false`). It still runs the pipeline described in its catalog description: validate credentials, test connectivity, persist, sync resources. Sibling types `connection.validate_credentials`, `connection.test_connection`, `connection.persist_connection`, and `connection.sync_resources` are internals — **start `connection.setup`, not them.**

### 2. OAuth provider connect

Use this when the provider issues tokens via authorization-code (GitHub OAuth, Meta, YouTube, LinkedIn, Deere, GCP, and others). Schema description on `connection.oauth-start`: provider key examples include `gcp`, `bling`, `github`, `aws`. Confirm `provider_type` against `connection.setup` `field_groups`.

1. `start_workflow("connection.oauth-start", { "provider_type": "github", "connection_name": "github-oauth" })`.
2. Read terminal output: `authorization_url`, `state`, `expires_at`. Give the user the URL. Do not log `state` more than needed to call exchange.
3. After redirect, the callback yields `code` (and the same `state`).
4. `start_workflow("connection.oauth-exchange", { "provider_type": "github", "code": "<callback-code>", "state": "<state-from-start>", "connection_name": "github-oauth" })`.
5. Exchange runs `connection.setup` for you. Output: `connection_uuid`, `status`.

Optional pins on start/exchange (provider-specific): `default_page_ref`, `instagram_business_account_ref`, `channel_ref`, `organization_ref`, `ad_account_ref`, `redirect_uri`. `connection_uuid` on **start** is only for providers that resolve their authorization server from an existing connection. Keep `redirect_uri` identical on start and exchange.

### 3. List / get connections and pick a UUID

`connection.query` and `connection.get` are `read_only: true`.

```json
{ "filters": { "connection_type": "gitlab" } }
```

Filters is a **JSON object**; do not pass `connection_type` at the top level. Supported keys: `connection_type`, `name`, `config` (allowlisted config keys only). Example from the schema: `{"filters": {"connection_type": "neon"}}`. Output: `connections` (uuid-keyed dicts), `count`.

Then `start_workflow("connection.get", { "connection_uuid": "<uuid>" })` — `has_prerequisites: true` (needs an existing connection). Output `connection` is the public record, not decrypted secrets.

Pass that UUID into other domains as `cloud_connection_uuid` / `connection_uuid` / `gitlab_connection_uuid` as those schemas name it.

### 4. Re-validate a stale connection

```json
{ "connection_uuid": "<uuid>" }
```

`connection.validate` re-tests connectivity and updates stored status. Watch for `validation_success`, `test_passed`, `new_status`, `last_validated_at`. Use this when a downstream workflow failed on credentials or the user says the connection is stale — not to create a new row.

### 5. Rotate credentials without disconnecting

`connection.rotate.credentials` keeps the same UUID. Required: `connection_uuid`, `provider_type`, plus the replacement credential fields for that provider (flattened, same names as setup) or `new_credentials` / `candidate_credentials`. Optional: `dry_run` (validate and test without mutating), `rotation_strategy`, `reconcile_dependents`, `idempotency_key`.

```json
{
  "connection_uuid": "<uuid>",
  "provider_type": "stripe",
  "api_key": "<new-restricted-key>",
  "dry_run": false
}
```

Watch for `test_passed`, `updated_fields`, `new_status`. Do not disconnect-and-recreate unless the user wants a new UUID (that would break every downstream reference).

### 6. Disconnect / scrub secrets

```json
{ "connection_uuid": "<uuid>" }
```

`connection.disconnect` scrubs secrets and soft-deletes the row. Output: `disconnected`, `already_deleted`, `deleted_at`. Confirm the UUID with `connection.query` first. Downstream runner groups, registry accounts, and network accounts that still point at it will fail until retargeted.

### 7. Provider asset sync

After OAuth (or when pages/accounts/channels drifted), refresh cached assets. Each takes `connection_uuid` plus an optional pin:

| Workflow | Refreshes | Optional pin |
|---|---|---|
| `connection.meta.sync-assets` | Facebook Pages + linked IG Business accounts | `default_page_ref` |
| `connection.meta-ads.sync-assets` | Meta Ads ad accounts (`/me/adaccounts`) | `ad_account_ref` |
| `connection.linkedin.sync-assets` | LinkedIn org ACLs (member token) | `organization_ref` |
| `connection.linkedin-community.sync-assets` | LinkedIn Community Management org ACLs | `organization_ref` |
| `connection.youtube.sync-assets` | YouTube channels (`channels.list?mine=true`) | `channel_ref` |
| `connection.deere.sync-assets` | John Deere Operations Center orgs | `organization_ref` |

```json
{ "connection_uuid": "<meta-connection-uuid>", "default_page_ref": "<page-id>" }
```

## Object model

**CloudConnection** — public identity is `uuid` (`connection_uuid` in workflows). Secrets live encrypted on the row and never appear on `connection.query` / `connection.get`. Status is updated by `connection.validate` and `connection.rotate.credentials`. Soft-delete is `connection.disconnect`.

Provider-specific cached assets (pages, channels, orgs, ad accounts) are stored on the connection after the matching `*.sync-assets` run — not as separate catalog objects.

DNS zones/records (Route53 / similar DNS providers) are a side inventory: `data.connection.sync_dns` and `data.connection.prune_dns`. They are not a substitute for `connection.setup`.

Unfeatured `data.connection.persist` / `update` / `soft_delete` / `update_status` are internals. Do not use them as the public create/rotate/disconnect path.

## Day-to-day reads

- `connection.query` — list; filter with `filters.connection_type` (and `name` / `config`).
- `connection.get` — one row by `connection_uuid`.
- `data.connection.query` — compatibility list in the data namespace; prefer `connection.query`.

Both featured reads are UUID-only public surfaces. If a schema field's `source.ref` is `connection.query`, start that picker rather than inventing a UUID.

## Gotchas

- Fill **only** the `field_groups` entry for the chosen `provider_type`. Extra groups are noise and can send the wrong secret shape.
- Never log or echo secrets from schemas or from `initial_data` you were given. Placeholders in this skill are labels, not values to print back.
- GitHub has three credential paths — PAT `api_token`, OAuth `access_token` (+ optional `refresh_token`, `expires_at`, `scope`), App `installation_ref`. See `orkestia-github`.
- SQL password field is `api_token`, not `password`. Engine host must reach `host:port` today.
- `connection.query` filters belong **inside** `filters`. Other schemas (for example GitLab on runner groups) use it as a picker source with `connection_type`.
- Sub-steps `connection.validate_credentials` / `test_connection` / `persist_connection` / `sync_resources` are internals; start `connection.setup`.
- `organization_uuid` is injected from the Bearer token. Do not ask the user for it.
- Disconnecting does not tear down runner infra or unsync registry/network inventory — retarget those domains separately.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, prerequisites, watch, remediation.
- `orkestia-github` — PAT / OAuth / App wiring and `github.*` operations.
- `orkestia-runners` — fleets that take `cloud_connection_uuid`.
- `orkestia-registry-network` — bind a connection as a registry or network account.
- `orkestia-subscription` — paying for Orkestia (not your own Stripe `connection.setup`).

## Additional resources

- Workflow map by job: [reference.md](reference.md)
- Worked `initial_data` scenarios: [examples.md](examples.md)
