---
name: orkestia-runners
description: Operate Orkestia runner fleets (runner.*, 204 types) — create runner groups across 14 cloud backends, manage environments, executions, warm pools, DevKit local runners, and Orkestia-hosted pools. Use when provisioning CI or agent compute, debugging executions, or scaling/draining fleets.
---

# Orkestia runners

The runner domain manages fleets of ephemeral compute across every supported cloud. It is the largest domain (204 types + 21 reads in `data.runner`).

## Object model

**RunnerGroup** (fleet definition) → provisioned **environment** (real cloud infrastructure) → **RunnerExecution** (one launched job) and, for warm pools, long-lived **RunnerInstance** rows. DevKit coding work adds **workspace leases** on top.

## Creating a group — `runner.group-creation` (DAG)

Four defining choices:

- **backend_type** (14): `devkit`, `fargate`, `ec2_auto_scaling`, `ec2_vm`, `gce`, `cloud_run`, `kubernetes`, `eks`, `azure_container_apps_job`, `azure_vm`, `azure_vmss`, `do_app_job`, `do_droplet`, `mgc_vm`. Backend-specific `config` keys: call `data.runner.list-provider-config-specs` first.
- **purpose**: `github_actions`, `gitlab_runner`, `generic` (plain container jobs), `agent` (hosts Orkestia agent sessions).
- **integration_type**: `github` (requires `github_installation_uuid` — supplied by caller, no list workflow exists), `gitlab` (requires `gitlab_connection_uuid` + project/group target), `none`.
- **runner_scope**: `organization` or `repository` (GitHub only, requires `github_repository_uuid`).

Bindings into other domains: `cloud_connection_uuid` (required for cloud backends; omit for devkit), `network_profile_uuid` (launch networking), `registry_account_uuid` (image resolution), `image_pull_cloud_connection_uuid`. Coding runtime: `coding_runtime_enabled` + `coding_artifact_storage_connection_uuid` provisions a private artifact bucket (capacity 512 MiB–1 TiB, retention 7–90 days).

Recovery for stuck creations: `runner.group-creation-abort`, `runner.group-reset-status`. Re-provision an existing row by passing `runner_group_uuid` back into `group-creation`. Update: `runner.group-update`; delete all infra: `runner.group-deletion`.

## Lifecycle families

| Family | Pattern | Notes |
|---|---|---|
| Environment | `environment-provision/-update/-deletion/-scale-*` per backend | Real infra create / re-apply / teardown / native scaling |
| Drift | `environment-drift-detect` / `environment-drift-repair` | Cross-backend drift plan + repair |
| Execution | `execution-launch/-stop/-restart/-sync/-logs-sync-*` per backend | `*-generic` variants run arbitrary commands; `-agent` variants host agent sessions |
| Warm pool | `pool-reconcile-{ec2-vm,gce,fargate,azure-vm,kubernetes}` | Controller loops converging to `min_warm_idle`/`max_count`; `pool-drain`, `pool-rotate` (AMI/hygiene rollout), `instance-terminate-*` per backend. `pool-sweep-ec2-vm` is DEPRECATED (superseded by pool-reconcile) |
| Scaling | `scale-check-group`, `dispatch-from-job-queued` | Demand-driven: pick an active group whose labels cover the queued job, launch up to max_count; min_count is the warm floor |
| DevKit | `instance-register/-heartbeat/-drain/-resume`, `execution-claim-next/-heartbeat/-complete`, `execution-safe-retry/-retry-ready/-retry-reject`, `workspace-lease.request/claim/heartbeat/complete` | Provider-blind local runners; leases bind Staff coding sessions to workspaces |
| Hosted | `hosted-tenant-provision/-disable`, `hosted-usage-reconcile` | Orkestia-hosted pools per org; usage metering writes one BillableEvent per terminal execution and enforces max session wall clock |
| Profiles & builds | `repository-profile.create/activate/retire`, `environment-build.request/retry` | Immutable per-repo execution profiles; immutable environment builds |

## Day-to-day reads (`data.runner.*`)

`list-groups`, `get-group`, `list-executions`, `get-execution`, `execution-logs-tail`, `pool-status` (warm/busy/draining composition + per-instance stats), `list-instances`, `list-events`, `list-resources`, `list-stuck`, `list-provider-config-specs`, `list-scheduling-diagnostics`, `list-stale-claims`, `workspace-lease.get`, `environment-build.get/list`, `repository-profile.get/list`.

## Gotchas

- Secret hygiene: `runner.execution-secrets-purge` scrubs environment/log keys from execution metadata (org-scoped, idempotent, audited).
- GitHub webhook `workflow_job` events drive dispatch and slot-freeing — see `orkestia-github`.
- `agents.runner-group.enable/disable` toggles agent support on a group (disable is guarded by an active-session check).
