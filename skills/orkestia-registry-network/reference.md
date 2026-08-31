# Registry & network — workflow map

Discover with `list_workflow_types(prefix="registry.")`, `prefix="network."`, `prefix="data.registry."`, `prefix="data.network."`. Verify with `get_workflow_schema`.

## Registry — bind and sync

| Workflow | Kind | Job |
|---|---|---|
| `data.registry.account.persist` | data, featured | Create RegistryAccount (DB). Required: `cloud_connection_uuid`, `name`, `backend_type`. Output: `registry_account_uuid`. |
| `registry.account-sync-all` | DAG, featured | Discover all repositories and fan out hydration. Start this for a full catalog. |
| `registry.account-sync` | state machine | Repositories for **one** account (discover + reconcile). Used as DAG step `discover_account`. |
| `registry.enqueue-repository-syncs` | internal fan-out | DAG layer `fanout`. Do not start. |
| `registry.repository-sync` | per-repo | Images/versions for one repository. Started by the fan-out. |
| `registry.account-reset-status` | compensation | DAG compensate. Do not start. |
| `registry.github-account-sync` | featured, prerequisites `github_ghcr` | GHCR sync **with** image/version hydration (PAT, OAuth, or App). |

`registry.account-sync-all` DAG:

1. `discover` → `registry.account-sync` (compensate `registry.account-reset-status`)
2. `fanout` → `registry.enqueue-repository-syncs`

## Registry — resolve and read (UUID-only)

| Workflow | Kind | Job |
|---|---|---|
| `data.registry.account.list` | read | Accounts. Filters: `backend_type`, `cached_sync_status`. Output `items`. |
| `data.registry.repository.list` | read | Repos. Filter `registry_account_uuid`. |
| `data.registry.image.list` | read | Images. |
| `data.registry.image-version.list` | read | Tags/versions. |
| `registry.image.resolve` | read | Tag, digest, or `reference` → catalog metadata. No `registry_account_uuid` field. |
| `registry.inventory.read` | read | Aggregated snapshot. Optional `include_images` / `include_versions`. |

## Registry — unsync (DB only)

| Workflow | Job |
|---|---|
| `data.registry.account.unsync` | Soft-delete account catalog. |
| `data.registry.repository.unsync` | Soft-delete one repository + images/versions. |

## Registry — adjacent (not inventory sync)

| Workflow | Job |
|---|---|
| `registry.kubernetes-pull-binding.reconcile` | Mint dockerconfigjson Secret on a Kubernetes `connection_uuid`; attach to ServiceAccounts. `namespaces` required (MASTER refused). Optional `registry_account_uuid` or `github_connection_uuid`. |
| `registry.module.apply` / `registry.module.query` | App module descriptors (`identity_app_uuid`). See `orkestia-app-platform`. |
| `registry.image.build-publish` | Unfeatured DAG: build and publish an application image into the deployment catalog. |

## Network — bind and sync

| Workflow | Kind | Job |
|---|---|---|
| `data.network.account.persist` | featured | Create/restore NetworkAccount. Required: `cloud_connection_uuid`, `backend_type`, `name`. No secrets in `config`. |
| `data.network.account.query` / `update` / `soft_delete` | featured | List (uuid-only; risk fields stripped) / patch / archive. |
| `network.account-sync-all` | DAG | All scopes + detailed inventory. |
| `network.account-sync` | state machine | Scopes for one account. DAG step `discover_account`. |
| `network.enqueue-scope-syncs` | internal | DAG fan-out. Do not start. |
| `network.scope-sync` | per-scope | Detailed inventory. Started by fan-out. |
| `network.account-reset-status` | compensation | Do not start. |

`network.account-sync-all` DAG: `network.account-sync` then `network.enqueue-scope-syncs` (compensate `network.account-reset-status`).

## Network — profiles (launch targets)

| Workflow | Job |
|---|---|
| `data.network.profile.persist` | Create/restore by org+name. Required: `network_account_uuid`, `name`. `profile_type`: `generic` \| `runner_execution` \| `spad_deployment`. `config`: UUIDs only. |
| `data.network.profile.query` / `update` / `soft_delete` | List / patch / archive. |
| `network.profile.resolve` | Read-only. Profile → provider-native `target`. Optional `required_intent`: `any` \| `private` \| `public`. This is what `runner.group-creation.network_profile_uuid` points at. |

## Network — planners (read-only)

| Workflow | Job |
|---|---|
| `network.topology.discover` | Snapshot from **synced** inventory. Filters: `provider`, `backend_type`, `network_account_uuid`. |
| `network.connectivity.plan` | Cross-cloud plan AWS / GCP / Cloudflare. Required `source` + `target` JSON. Does not apply. |

## Network — unsync and retention (DB only)

| Workflow | Job |
|---|---|
| `network.account-unsync` | Soft-delete account inventory. |
| `network.scope-unsync` | Soft-delete one scope inventory. |
| `data.network.scope.prune_stale` | Hard-delete soft-deleted scopes past retention. |
| `data.network.topology.prune_stale` | Hard-delete stale topology rows. |

Scope / segment / security_boundary `data.network.*.persist|query|update|soft_delete` are UUID-only. **`data.network.security_boundary.query` does not expose rule contents**; persist upserts from sync also store no rules. Prefer sync over hand-built inventory.

## Network — Azure runner segment

`network.azure.runner-segment.ensure` — mutating DAG: VNet + subnet + NSG on a customer Azure connection for runner VMs. Default egress per-VM public IP; `egress_mode=nat_gateway` for shared NAT. Bindings belong with `orkestia-runners`.

## Runner group consumption

`runner.group-creation` (see `orkestia-runners`) optional fields sourced here:

- `registry_account_uuid` ← `data.registry.account.list`
- `image_pull_cloud_connection_uuid` ← `connection.query` (fallback: group's `cloud_connection_uuid`)
- `network_profile_uuid` ← `data.network.profile.query`

## Security

- UUID-only read surfaces. No decrypted registry passwords, kube tokens, or security-group rule bodies.
- Never log secrets from `registry.kubernetes-pull-binding.reconcile` or backing connections.
- Unsync does not delete provider resources.
