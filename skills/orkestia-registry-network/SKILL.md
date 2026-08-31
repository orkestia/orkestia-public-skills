---
name: orkestia-registry-network
description: Operate Orkestia's synced inventories — container registries (registry.*) and cloud networking (network.*) — bind CloudConnections as accounts, sync catalogs, resolve images and NetworkProfiles, unsync local rows, and plan cross-cloud connectivity. Use when runner groups, deploys, or launch networking need registry_account_uuid, image_pull_cloud_connection_uuid, or network_profile_uuid.
---

# Orkestia registry & network

Both domains follow the same shape: an **account** bound to a CloudConnection, sync workflows that mirror provider inventory into the platform, and a **UUID-only** read surface other domains reference. Discover live types with `list_workflow_types(prefix="registry.")`, `prefix="network."`, `prefix="data.registry."`, and `prefix="data.network."`. Do not treat counts in this file as frozen.

Registry hierarchy: **RegistryAccount → repositories → images → versions (tags)**. Network hierarchy: **NetworkAccount → NetworkScopes** (per provider scope) → **segments** and **security boundaries** (rule contents are not persisted or exposed).

## When to load

Load this skill when the user needs a container-image catalog, GHCR/ECR/GCR (or similar) sync, image tag/digest resolution, a Kubernetes pull Secret, a NetworkProfile for launch targeting, network inventory sync, topology, or a read-only cross-cloud connectivity plan — or when a runner group schema asks for `registry_account_uuid` / `image_pull_cloud_connection_uuid` / `network_profile_uuid`. Load `orkestia-connections` if the backing CloudConnection does not exist yet. Load `orkestia-runners` to **create** the group; this skill only prepares the UUIDs.

## Use cases

1. Bind a CloudConnection as a registry account and sync inventory (all repos vs one account vs GHCR).
2. Resolve an image (tag / digest / reference) to catalog metadata for a runner group.
3. Unsync / clean up local registry or network inventory (DB only).
4. Create or update a NetworkProfile and resolve it to launch-target data.
5. Sync network inventory, then topology.discover / connectivity.plan (read-only).
6. Hand `registry_account_uuid` + `image_pull_cloud_connection_uuid` + `network_profile_uuid` to a runner group (see `orkestia-runners`).

## How to

`whoami()` once. Reads (`read_only: true`) start freely. Mutations: schema → prerequisites if any → `start_workflow` → `watch_workflow`. Token injects `organization_uuid` — omit it from `initial_data`. Never log secrets; registry/network public surfaces are UUID-only.

### 1. Bind a CloudConnection as a registry account and sync

Need an existing CloudConnection (`connection.query` — `orkestia-connections`). Then persist a **RegistryAccount** (DB row only) and sync.

```json
{
  "cloud_connection_uuid": "<connection-uuid>",
  "name": "prod-ecr",
  "backend_type": "ecr",
  "region": "us-east-1",
  "project_or_account_ref": "123456789012"
}
```

`data.registry.account.persist` required: `cloud_connection_uuid`, `name`, `backend_type`. Schema examples for `backend_type`: `ecr`, `gcr`, `github_ghcr`. Optional: `description`, `namespace`, `config`, `provider_metadata`. Output: `registry_account_uuid`.

**Full catalog (discover + per-repo hydration)** — start the DAG, not its children:

```json
{ "registry_account_uuid": "<uuid>" }
```

`registry.account-sync-all` layers: `registry.account-sync` (discover) then `registry.enqueue-repository-syncs` (fan-out). Compensation: `registry.account-reset-status`. Do **not** start `enqueue-repository-syncs`, `repository-sync`, or `account-reset-status` yourself.

**One account, repository list only** (no fan-out): `registry.account-sync` with the same `registry_account_uuid`. Optional `manage_account_state` (defaults true; set false when a parent DAG owns status).

**GHCR with image/version hydration** (GitHub PAT, OAuth, or App connection):

```json
{ "registry_account_uuid": "<ghcr-account-uuid>" }
```

`registry.github-account-sync` has `has_prerequisites: true` (`variant="github_ghcr"`). PAT/OAuth needs `read:packages` (+ `repo` when packages or backing repos are private). App installation must see those packages. Persist the account with `backend_type="github_ghcr"` first.

### 2. Resolve an image for a runner group

Sync first (recipe 1). Then either browse or resolve.

Browse: `data.registry.account.list` (optional `backend_type`, `cached_sync_status`) → `data.registry.repository.list` (`registry_account_uuid`) → `data.registry.image.list` / `data.registry.image-version.list`. Aggregated snapshot: `registry.inventory.read` (`registry_account_uuid`, optional `include_images` / `include_versions`).

Resolve tag, digest, or full reference to catalog UUIDs (`read_only`):

```json
{
  "repository_full_name": "ghcr.io/acme/api",
  "tag": "sha-abc123"
}
```

Or `{ "reference": "ghcr.io/acme/api@sha256:…" }` or `{ "digest": "sha256:…" }`. Optional `registry_repository_uuid` restricts to one repo. Output: `resolved`, `registry_image_uuid`, `registry_image_version_uuid`, `media_type`, `architecture`, `size_bytes`.

There is no `registry_account_uuid` on `registry.image.resolve` — scope via repository UUID or `repository_full_name`. The runner group still stores `registry_account_uuid` separately (recipe 6).

### 3. Unsync / cleanup local inventory (DB only)

These **do not** delete images or VPCs on the provider.

Registry:

```json
{ "registry_account_uuid": "<uuid>" }
```

`data.registry.account.unsync` — soft-delete the account catalog. One repo: `data.registry.repository.unsync` with `registry_repository_uuid` (picker: `data.registry.repository.list`).

Network:

```json
{ "network_account_uuid": "<uuid>" }
```

`network.account-unsync` — whole account inventory. One scope: `network.scope-unsync` with `network_scope_uuid` (picker: `data.network.scope.query`).

Retention hard-deletes: `data.network.scope.prune_stale`, `data.network.topology.prune_stale`.

### 4. Create / update a NetworkProfile and resolve it

Need a **NetworkAccount** on a CloudConnection:

```json
{
  "cloud_connection_uuid": "<aws-connection-uuid>",
  "backend_type": "aws_vpc",
  "name": "prod-aws-net",
  "region": "us-east-1"
}
```

`data.network.account.persist` — `backend_type` examples: `aws_vpc`, `gcp_vpc`, `azure_vnet`. `config` / `provider_metadata` must **not** contain secrets. Output: `network_account_uuid`. Sync inventory (recipe 5) so scopes/segments exist, then persist a profile:

```json
{
  "network_account_uuid": "<uuid>",
  "name": "runner-private",
  "profile_type": "runner_execution",
  "is_default": false,
  "config": {}
}
```

`profile_type`: `generic` | `runner_execution` | `spad_deployment`. **`config` is UUIDs only** — sequential numeric id keys are rejected. Output: `network_profile_uuid`.

Update: `data.network.profile.update` with `network_profile_uuid` plus any of `name`, `description`, `profile_type`, `is_default`, `config`. List: `data.network.profile.query` (filter `network_account_uuid`, `profile_type`, `is_default`, `name_contains`). Archive: `data.network.profile.soft_delete`.

Resolve to provider-native launch data (`read_only`) — this is what a runner group's `network_profile_uuid` points at:

```json
{
  "network_profile_uuid": "<uuid>",
  "required_intent": "private"
}
```

`required_intent`: `any` | `private` | `public`. Output includes `target`, `segment_uuids`, `security_boundary_uuids`, `cloud_connection_uuid`, `readiness`, `readiness_reasons`. Boundary **rule contents are not in the output**.

### 5. Sync network inventory, then topology / connectivity plan

**Full sync** DAG:

```json
{ "network_account_uuid": "<uuid>" }
```

`network.account-sync-all` layers: `network.account-sync` then `network.enqueue-scope-syncs`. Compensation: `network.account-reset-status`. Do not start those children (or `network.scope-sync`) yourself unless you are recovering a single scope.

One account, scopes only: `network.account-sync`.

Then **read-only** planners (they need synced inventory):

```json
{ "network_account_uuid": "<uuid>", "include_profiles": true }
```

`network.topology.discover` — local snapshot: `domains`, `graph`, `cidr_overlaps`, `invalid_cidrs`. Filters: `provider`, `backend_type`.

```json
{
  "connectivity_type": "auto",
  "intent_name": "aws-to-gcp-private",
  "source": { "provider": "aws", "region": "us-east-1", "cidr_blocks": ["10.0.0.0/16"] },
  "target": { "provider": "gcp", "region": "us-central1", "cidr_blocks": ["10.8.0.0/16"] }
}
```

`network.connectivity.plan` — AWS / GCP / Cloudflare, **read-only**. `connectivity_type`: `auto` | `public_edge` | `private_vpn` | `dedicated_interconnect` | `private_service` | `cloudflare_wan`. Output: `supported`, `blockers`, `route_plan`, `apply_available` (planning does not apply).

### 6. How a runner group consumes the three UUIDs

Do **not** duplicate `orkestia-runners`. `runner.group-creation` optional bindings:

| Field | Picker | Role |
|---|---|---|
| `registry_account_uuid` | `data.registry.account.list` | Image catalog the group resolves against |
| `image_pull_cloud_connection_uuid` | `connection.query` | Auth for pulls; falls back to `cloud_connection_uuid` |
| `network_profile_uuid` | `data.network.profile.query` | Launch networking; resolved via `network.profile.resolve` |

Prepare those UUIDs with recipes 1–4, then follow `orkestia-runners` to start `runner.group-creation`. On Kubernetes clusters, `registry.kubernetes-pull-binding.reconcile` mints a dockerconfigjson Secret from a registry account (or GitHub connection) onto ServiceAccounts — that is cluster pull auth, not the runner-group field set.

## Object model

**RegistryAccount** (`registry_account_uuid`) binds `cloud_connection_uuid` + `backend_type`. Children: repositories → images → versions. Public list workflows return UUID-only dicts.

**NetworkAccount** (`network_account_uuid`) binds `cloud_connection_uuid` + `backend_type`. Children: **NetworkScope** → **NetworkSegment** and **NetworkSecurityBoundary**. Rule contents are not persisted and not exposed on `data.network.security_boundary.query`.

**NetworkProfile** (`network_profile_uuid`) is the launch-networking abstraction: CRUD via `data.network.profile.*`; `network.profile.resolve` turns it into provider-native `target` data.

App modules (`registry.module.apply` / `registry.module.query`) share the `registry.*` prefix but belong to app descriptors (`identity_app_uuid`) — see `orkestia-app-platform`, not this inventory.

## Day-to-day reads

Registry (UUID-only): `data.registry.account.list`, `data.registry.repository.list`, `data.registry.image.list`, `data.registry.image-version.list`, `registry.image.resolve`, `registry.inventory.read`.

Network (UUID-only): `data.network.account.query`, `data.network.scope.query`, `data.network.segment.query`, `data.network.security_boundary.query`, `data.network.profile.query`, `network.profile.resolve`, `network.topology.discover`. `network.connectivity.plan` is read-only planning (not a list).

## Gotchas

- Sync-all DAGs own fan-out. Starting `enqueue-*` or `*-reset-status` by hand is compensation/internal.
- Unsync is **DB only**. Provider registries and VPCs stay put.
- GHCR: `registry.github-account-sync`, not `account-sync-all`, when you need image/version hydration on a GitHub-backed account. Token scopes: `orkestia-github`.
- `registry.image.resolve` has no `registry_account_uuid`; pass repo UUID or `repository_full_name`.
- NetworkProfile `config` rejects sequential ids — UUIDs only. Security-boundary **rules never appear** on reads.
- `data.network.*.persist` / `update` on scope/segment/boundary are sync upserts; prefer account-sync rather than hand-crafting inventory.
- `network.azure.runner-segment.ensure` provisions Azure VNet/subnet/NSG for runner VMs — a mutating DAG, not a planner. Use with `orkestia-runners`.
- Never log pull tokens or connection secrets when reconciling Kubernetes pull bindings.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, watch, recovery.
- `orkestia-connections` — CloudConnection create/validate/rotate.
- `orkestia-runners` — `runner.group-creation` and fleets.
- `orkestia-github` — GitHub credential paths and GHCR scopes.
- `orkestia-app-platform` — `registry.module.*` app descriptors.

## Additional resources

- Workflow map by job: [reference.md](reference.md)
- Worked `initial_data` scenarios: [examples.md](examples.md)
