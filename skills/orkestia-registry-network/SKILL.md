---
name: orkestia-registry-network
description: Operate Orkestia's synced inventories — container registries (registry.*) and cloud networking (network.*) — accounts, sync fan-outs, UUID-only read surfaces, image resolution, network profiles, topology and cross-cloud connectivity planning. Use when runner groups, deploys, or launch networking need registry or network references.
---

# Orkestia registry & network

Both domains follow the same shape: an **account** object bound to a CloudConnection, sync workflows that mirror provider inventory into the platform, and a UUID-only read surface other domains reference.

## Registry (container images) — 10 types + 7 reads

Hierarchy: **RegistryAccount → repositories → images → versions (tags)**.

- Sync: `registry.account-sync-all` (DAG: discover all repositories, fan out) → `registry.repository-sync` per repo via `enqueue-repository-syncs`; `registry.account-sync` for one account; `registry.github-account-sync` for GHCR (token or App connections, with image/version hydration); `account-reset-status` is the DAG compensation step.
- Reads: `data.registry.account.list`, `repository.list`, `image.list`, `image-version.list` (all UUID-only); `registry.image.resolve` (tag / digest / reference → catalog metadata); `registry.inventory.read` (aggregated catalog).
- Cleanup: `data.registry.account.unsync`, `repository.unsync` (soft delete, DB only).
- App modules (separate concern in the same namespace): `registry.module.apply` (validate, persist, compile a module descriptor), `registry.module.query`.

**Consumers:** runner groups resolve container images through `registry_account_uuid` (with `image_pull_cloud_connection_uuid` for pull auth).

## Network — 9 types + 22 reads

Hierarchy: **NetworkAccount → NetworkScopes** (per provider scope) → **segments** and **security boundaries** (rule contents deliberately not persisted/exposed).

- Sync: `network.account-sync-all` (DAG: all scopes + detailed inventory) → `network.scope-sync` per scope via `enqueue-scope-syncs`; `network.account-sync` for one account; `scope-unsync` removes local inventory (soft delete); `account-reset-status` compensation.
- Planners: `network.topology.discover` builds a local topology snapshot from synced inventory; `network.connectivity.plan` plans cross-cloud connectivity between AWS, GCP, and Cloudflare (read-only).
- **NetworkProfile** — the launch-networking abstraction: CRUD via `data.network.profile.persist/query/update/soft_delete`; `network.profile.resolve` turns a profile into provider-native launch target data. This is what a runner group's `network_profile_uuid` points at.
- Reads/CRUD (`data.network.*`, UUID-only): account, scope, segment, security_boundary — each with `query`/`persist`/`update`/`soft_delete`; retention pruning via `scope.prune_stale`, `topology.prune_stale`.
