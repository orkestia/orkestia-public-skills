# Connections — examples

All `start_workflow` payloads omit `organization_uuid` (injected from the MCP token). Replace angle-bracket placeholders; never print real secrets back.

## AWS AssumeRole

```
get_workflow_prerequisites("connection.setup", variant="aws")
# hand the trust-policy markdown to the user; principal is filled in
start_workflow("connection.setup", {
  "provider_type": "aws",
  "connection_name": "prod-aws",
  "role_arn": "arn:aws:iam::123456789012:role/orkestia-access",
  "external_ref": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "regions": ["us-east-1"]
})
watch_workflow(<workflow_id>)
# terminal: connection_uuid, test_passed, persisted
```

## GitHub PAT, then pick the UUID

```
get_workflow_prerequisites("connection.setup", variant="github")
start_workflow("connection.setup", {
  "provider_type": "github",
  "connection_name": "company-github",
  "api_token": "<github-pat-with-repo-and-read-packages-if-ghcr>"
})
```

Later, for a GitLab (or any) picker used by another domain:

```
start_workflow("connection.query", {
  "filters": { "connection_type": "github" }
})
# connections[].uuid → cloud_connection_uuid / gitlab_connection_uuid as the consumer schema names it
```

GitHub App path uses `installation_ref` instead of `api_token`. OAuth path uses `access_token` or recipe 2 in SKILL.md. See `orkestia-github`.

## SQL Postgres

```
get_workflow_prerequisites("connection.setup", variant="sql")
start_workflow("connection.setup", {
  "provider_type": "sql",
  "connection_name": "analytics-pg",
  "host": "db.internal.example.com",
  "port": "5432",
  "database": "analytics",
  "username": "orkestia_ro",
  "api_token": "<db-password>",
  "dialect": "postgres",
  "ssl_mode": "require"
})
```

`api_token` is the database password (stored encrypted). Not Neon (Neon is `provider_type="neon"` with an API key).

## Stripe restricted key

```
get_workflow_prerequisites("connection.setup", variant="stripe")
start_workflow("connection.setup", {
  "provider_type": "stripe",
  "connection_name": "store-stripe",
  "api_key": "<rk-or-sk>",
  "webhook_secret": "<whsec-if-validating-webhooks>"
})
```

This is **your** Stripe account. Orkestia billing is `orkestia-subscription`, never this key.

## OAuth (GitHub) start → exchange

```
start_workflow("connection.oauth-start", {
  "provider_type": "github",
  "connection_name": "github-oauth"
})
# output: authorization_url, state, expires_at
# user opens authorization_url; callback returns code
start_workflow("connection.oauth-exchange", {
  "provider_type": "github",
  "code": "<callback-code>",
  "state": "<state-from-start>",
  "connection_name": "github-oauth"
})
# output: connection_uuid, status
```

Meta organic variant pins a page after grant:

```
start_workflow("connection.oauth-start", {
  "provider_type": "meta",
  "connection_name": "meta-organic",
  "default_page_ref": "<page-id>"
})
```

## Validate, rotate, disconnect

```
start_workflow("connection.query", { "filters": { "connection_type": "stripe" } })
start_workflow("connection.get", { "connection_uuid": "<uuid>" })
start_workflow("connection.validate", { "connection_uuid": "<uuid>" })
# validation_success, new_status, last_validated_at

start_workflow("connection.rotate.credentials", {
  "connection_uuid": "<uuid>",
  "provider_type": "stripe",
  "api_key": "<new-rk>",
  "dry_run": true
})
# if test_passed, repeat with dry_run false (or omit)

start_workflow("connection.disconnect", { "connection_uuid": "<uuid>" })
# disconnected, deleted_at
```

## Refresh Meta pages after OAuth

```
start_workflow("connection.meta.sync-assets", {
  "connection_uuid": "<meta-connection-uuid>",
  "default_page_ref": "<page-id>"
})
# pages, count, instagram_business_account_ref
```

YouTube:

```
start_workflow("connection.youtube.sync-assets", {
  "connection_uuid": "<youtube-connection-uuid>"
})
```

## DNS sync (Route53 / DNS-capable connection)

```
start_workflow("data.connection.sync_dns", { "connection_uuid": "<uuid>" })
# zones_synced, records_synced; or sync_skipped
start_workflow("data.connection.prune_dns", {
  "connection_uuid": "<uuid>",
  "prune_records": true
})
```
