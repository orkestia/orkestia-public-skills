# Runner workflow map

Job-grouped. Confirm names with `list_workflow_types(prefix="runner.")` (and `prefix="data.runner."`). Do not start `__pre` / `__post`, `*.prepare` / `*.finalize`, or adapter rows unless a parent schema names them.

## Backends

`runner.group-creation.backend_type` values, verified against the schema and `data.runner.list-provider-config-specs` (2026-08-31). **`devkit` is not in the spec catalogue** — omit `config` and `cloud_connection_uuid`.

| `backend_type` | `config` required_keys | Standing environment provision (DAG child) |
|---|---|---|
| `devkit` | — | Hosts register via `runner.instance-register` |
| `fargate` | `ecs_cluster_name` | `runner.environment-provision` |
| `ec2_auto_scaling` | `instance_type` | `runner.environment-provision-ec2` |
| `ec2_vm` | `instance_type` | `runner.environment-provision-ec2-vm` |
| `gce` | `project_id`, `zone`, `machine_type`, `vm_image` | `runner.environment-provision-gcp` |
| `cloud_run` | `project_id`, `region` | `runner.environment-provision-cloud-run` |
| `kubernetes` | `namespace` | `runner.environment-provision-kubernetes` |
| `eks` | `cluster_name`, `namespace` | same Kubernetes provisioner |
| `azure_container_apps_job` | `subscription_id`, `resource_group`, `environment_name` | `runner.environment-provision-azure-container-apps` |
| `azure_vm` | `subscription_id`, `resource_group`, `location`, `vm_size` | per-execution VM (no standing provision step on the create DAG) |
| `azure_vmss` | `subscription_id`, `resource_group`, `vmss_name` | native scale: `runner.environment-scale-azure-vmss` |
| `do_app_job` | `app_id`, `job_name` | `runner.environment-provision-do-app-job` |
| `do_droplet` | `region`, `size` | per-execution droplet |
| `mgc_vm` | `region`, `machine_type` | per-execution Magalu VM |

Single-backend spec: `data.runner.get-provider-config-spec`. Azure managed environments: `data.runner.list-azure-environments`, `runner.azure-managed-environment-create` / `azure-managed-environment-sync`.

Optional `config` keys (cpu/memory, subnets, Spot, images, …) live on the spec row — copy from the live catalogue, do not guess.

## Group lifecycle

| Job | Start | Notes |
|---|---|---|
| Create / re-provision | `runner.group-creation` | DAG. Pass `runner_group_uuid` to re-provision. |
| Abort stuck create | `runner.group-creation-abort` | Force-fail in-flight + reset |
| Reset status only | `runner.group-reset-status` | `ERROR` + clear `active_workflow_uuid` |
| Patch + coding storage | `runner.group-update` | DAG; `config_strategy` `merge` (default) or `replace` |
| Patch row only | `data.runner.group-update` | Does **not** re-provision |
| Change image | `runner.group-set-container-image` | |
| Delete infra | `runner.group-deletion` | DAG: deregister CI runners, then per-backend `environment-deletion-*` |
| Reads | `data.runner.list-groups`, `data.runner.get-group` | `hosted` is tenancy, not a backend |

Skip: `runner.group-creation.prepare` / `.finalize`, `group-creation-abort.force-fail`, `group-update.prepare` / `.apply` / `.finalize`, `group-deletion.deregister` / `.finalize`, `data.runner.group-persist`, `data.runner.group-get`.

## Environments

Cross-backend entry points (the create DAG already calls the right one):

- Provision / update / delete / health: `runner.environment-provision[-<backend>]`, `environment-update[-<backend>]`, `environment-deletion[-<backend>]`, `environment-health-check[-<backend>]`
- Drift: `runner.environment-drift-detect`, `runner.environment-drift-repair` (plus `drift_detect_*` / `drift_repair_*` internals)
- Native scale: `environment-scale-ec2-asg`, `environment-scale-gce`, `environment-scale-gcp-mig`, `environment-scale-azure-vmss`
- Reconcile (Fargate): `runner.environment-reconcile`

Builder / immutable builds: `runner.environment-build.request` / `.retry` / `.claim` / `.heartbeat` / `.publish` / `.verify` / `.fail` / `.reconcile`. Reads: `data.runner.environment-build.get` / `.list`. Kubernetes builder: `environment-builder-config-reconcile-kubernetes`, `environment-builder-runtime-delete-kubernetes`.

Repository profiles: `runner.repository-profile.create` / `.activate` / `.retire` / `.adopt-source`. Reads: `data.runner.repository-profile.get` / `.list`.

## Executions

Pattern: `execution-launch[-<backend>][-generic|-agent|-gitlab]`, then `execution-sync-*`, `execution-stop-*`, `execution-restart-*`, `execution-logs-sync-*`.

**CI (default launch, no suffix)** — GitHub/GitLab runner process on that backend, e.g. `execution-launch`, `execution-launch-ec2`, `execution-launch-ec2-vm`, `execution-launch-gcp`, `execution-launch-cloud-run`, `execution-launch-kubernetes`, `execution-launch-azure-container-apps`, `execution-launch-azure-vm`, `execution-launch-azure-vmss`, `execution-launch-do-droplet`, `execution-launch-mgc-vm`. GitLab-on-Cloud-Run: `execution-launch-cloud-run-gitlab`.

**`*-generic`** — arbitrary command, no CI registration: `execution-launch-generic`, `execution-launch-ec2-vm-generic`, `execution-launch-gcp-generic`, `execution-launch-cloud-run-generic`, `execution-launch-kubernetes-generic`, `execution-launch-azure-container-apps-generic`, `execution-launch-azure-vm-generic`, `execution-launch-azure-vmss-generic`, `execution-launch-do-app-job-generic`, `execution-launch-do-droplet-generic`, `execution-launch-mgc-vm-generic`. Restarts: `execution-restart-azure-container-apps-generic`, `execution-restart-cloud-run-generic`.

**`*-agent`** — Orkestia agent session hosts: `execution-launch-agent` (Fargate), `execution-launch-kubernetes-agent`. Prefer `agents.session-launch` (`orkestia-agents`) over starting these directly.

Stale sync: `execution-sync-stale-cloud-run` / `-gcp` / `-kubernetes`. Claim-watch: `execution-claim-watch`. Stale coding claims: `execution-reconcile-stale-claims`, `execution-reconciliation-plan`. Secret hygiene: `runner.execution-secrets-purge`. GCP secret stage: `execution-secret-stage-gcp`.

Reads: `data.runner.list-executions`, `get-execution`, `execution-logs-tail`, `execution-assignment.get`.

## Warm pools

| Job | Workflow |
|---|---|
| Snapshot | `data.runner.pool-status` |
| Drain | `runner.pool-drain` |
| Rotate (drain + reconcile nudge) | `runner.pool-rotate` |
| Controller tick | `pool-reconcile-ec2-vm`, `pool-reconcile-gce`, `pool-reconcile-fargate`, `pool-reconcile-azure-vm`, `pool-reconcile-kubernetes` |
| Launch into pool | `pool-launch-fargate`, `pool-launch-kubernetes` |
| Terminate instance | `instance-terminate-ec2-vm`, `-gce`, `-fargate`, `-azure-vm`, `-kubernetes` |
| Cron inventory (internal) | `data.runner.list-active-warm-pool-groups` |

**DEPRECATED:** `runner.pool-sweep-ec2-vm` — use `pool-reconcile-ec2-vm`. Adapter (do not start from MCP): `runner.pool-reconcile`.

## Scaling

- Webhook-driven: `github.workflow-job` → `github.workflow-job-handle` → `runner.dispatch-from-job-queued` (queued) / `execution-stop-*` (completed)
- Operator / floor: `runner.scale-check-group` — `max(min_count, demand)` up to `max_count`

## DevKit

`instance-register`, `instance-heartbeat`, `instance-drain`, `instance-resume`, `instance-evict`. Executions: `execution-claim-next`, `execution-heartbeat`, `execution-complete`, `execution-safe-retry`, `execution-retry-ready`, `execution-retry-reject`. Leases: `workspace-lease.request` / `.claim` / `.heartbeat` / `.complete`. Reads: `list-claimable`, `list-stale-claims`, `workspace-lease.get`.

## Hosted (subscription-gated)

`runner.hosted-tenant-provision` — `backend_type` `kubernetes` (default) or `azure_vm`; one pool per backend; idempotent. `runner.hosted-tenant-disable` — optional `force`. Metering: `runner.hosted-usage-reconcile` (`runner_group_uuid`) → **BillableEvent** + `max_session_duration_s`. See `orkestia-subscription`.

## GitHub runner groups (existing GH groups)

Does not create GitHub runners. `runner.github-runner-group.bind-existing` (`runner_group_uuid`, `github_runner_group_ref`, optional exact `github_runner_group_name`). Then `runner.github-runner-group.add-existing-runners` to associate already-registered org runners.

## Registry mirrors

Azure: `runner.acr-registry-mirror-ensure` / `-reconcile` / `-teardown`. Cloud Run / Artifact Registry: `runner.cloud-run-registry-mirror-ensure` / `-reconcile` / `-teardown`. Related: `cloud-run-job-reap`.

## Software-delivery log cleanup

Retention controller (usually claimed, not human-started): `runner.software-delivery.cleanup-execution-log-dispatch` → `cleanup-execution-log` (DAG) with `cleanup-execution-log-claim-prepare`, `-provider-runtime`, `-workflow-history`, `-main-store`. Pairs with ticket software-delivery cleanup (`orkestia-tickets`).

## Integration tests

Credential-isolated Kubernetes Job, secretless evidence. Executor-shaped: `runner.integration-test.redeem` → `dispatch` → `status` → `complete` (exit + result digests only; no command output or credentials). Needs `runner_instance_uuid`, `runner_execution_uuid`, `workspace_lease_uuid`, `coding_artifact_uuid`, `head_oid`, `test_id`.

## Agent image

`runner.agent-image-resolve` — resolve the platform agent image for agent-purpose groups.

## Reads leftover

`data.runner.list-events`, `list-resources`, `list-instances`, `list-stuck`, `list-scheduling-diagnostics`.
