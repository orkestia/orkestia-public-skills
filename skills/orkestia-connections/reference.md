# Connections — workflow map

Grouped by job. Discover live names with `list_workflow_types(prefix="connection.")` and `list_workflow_types(prefix="data.connection.")`. Verify fields with `get_workflow_schema` before every start.

## Create / connect

| Workflow | Kind | When |
|---|---|---|
| `connection.setup` | state machine, featured | **Entry point** for every provider. `has_prerequisites: true`. `field_groups` keyed by `provider_type`. Token injects `organization_uuid`. |
| `connection.oauth-start` | state machine, featured | Begin authorization-code flow. Returns `authorization_url` + `state`. |
| `connection.oauth-exchange` | state machine, featured | Trade `code` + `state` for tokens and run `connection.setup`. Returns `connection_uuid`. |

Do **not** start: `connection.validate_credentials`, `connection.test_connection`, `connection.persist_connection`, `connection.sync_resources` (pipeline internals that exist as their own types).

`get_workflow_dag("connection.setup")` reports `is_dag: false`. The catalog description still names the pipeline: validate → test → persist → sync resources.

### `connection.setup` field groups (orientation)

Read `field_groups` from the live schema. Known groups include: `aws`, `gcp`, `azure`, `github`, `gitlab`, `kubernetes`, `sql`, `stripe`, `docker_hub`, `neon`, `openai`, `slack`, `meta`, `meta_ads`, `linkedin`, `linkedin_ads`, `linkedin_community`, `youtube`, `deere`, plus others (`argocd`, `docusign`, `xero`, `hostinger`, …). The `common` group is `provider_type`, `connection_name`, `organization_uuid`, `actor`.

Prerequisite **variants** (pass as `get_workflow_prerequisites(..., variant=...)`) are a subset of those groups. If a provider has no variant, still read the schema group and start `connection.setup`.

### GitHub credential paths

All via `connection.setup` with `provider_type="github"`:

- PAT → `api_token`
- OAuth → `access_token` (optional `refresh_token`, `expires_at`, `scope`) or the oauth-start / oauth-exchange pair
- GitHub App → `installation_ref`

Detail: `orkestia-github`.

## Pick a UUID

| Workflow | Kind | When |
|---|---|---|
| `connection.query` | read-only | List. Input `filters` object: `connection_type`, `name`, `config`. Output `connections`, `count`. |
| `connection.get` | read-only, prerequisites | One row by `connection_uuid`. Output `connection` (no decrypted secrets). |
| `data.connection.query` | unfeatured read | Compatibility list. Prefer `connection.query`. |

## Lifecycle

| Workflow | Kind | When |
|---|---|---|
| `connection.validate` | featured | Re-test connectivity; update status. Input: `connection_uuid`. |
| `connection.rotate.credentials` | featured | Same UUID; validate + test replacement secrets; mark active. Flattened provider fields or `new_credentials`. `dry_run` skips mutation. |
| `connection.disconnect` | featured | Scrub secrets + soft-delete. Input: `connection_uuid`. |

Do **not** use unfeatured `data.connection.persist` / `data.connection.update` / `data.connection.soft_delete` / `data.connection.update_status` as the public path.

## Asset refresh

| Workflow | Provider inventory |
|---|---|
| `connection.meta.sync-assets` | Pages + IG Business (`Graph /me/accounts`) |
| `connection.meta-ads.sync-assets` | Ad accounts (`/me/adaccounts`) |
| `connection.linkedin.sync-assets` | Org ACLs (member token) |
| `connection.linkedin-community.sync-assets` | Community Management org ACLs |
| `connection.youtube.sync-assets` | Channels (`channels.list?mine=true`) |
| `connection.deere.sync-assets` | Operations Center orgs |

Each: `connection_uuid` plus optional pin (`default_page_ref`, `ad_account_ref`, `organization_ref`, `channel_ref`).

## DNS inventory

| Workflow | Kind | When |
|---|---|---|
| `data.connection.sync_dns` | data, featured | Mirror zones/records from a DNS-capable connection into the platform. |
| `data.connection.prune_dns` | data, featured | Soft-delete zones/records gone upstream. Optional `prune_records` (default true). |

Skipped when the provider has no DNS plugin (`sync_skipped` / `sync_reason`).

## Security

- Never log or echo secret-typed fields from `get_workflow_schema` or from `initial_data`.
- Read surfaces are UUID-only and do not return decrypted credentials.
- Disconnect scrubs secrets; it does not delete cloud resources or unsync registry/network catalogs.
