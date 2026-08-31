---
name: orkestia-runners
description: >-
  Operate Orkestia runner fleets (runner.*) — provision groups, environments,
  executions, warm pools, DevKit hosts, and hosted compute. Use when setting up
  CI compute, agent hosts, warm pools, or DevKit local runners, or when draining
  a fleet or debugging a stuck execution.
---

# Orkestia runners

A **runner group** is the fleet definition you operate. Orkestia provisions an **environment** on a cloud backend (or registers DevKit hosts), then launches **executions** for CI jobs, generic commands, or agent sessions. Warm pools keep **instances** idle so jobs skip cold start. Staff coding sessions bind a **workspace lease** onto an execution.

Do not start per-backend `environment-provision-*` / `execution-launch-*` children yourself. Start the group DAG, then use the reads and recovery recipes below. Catalog counts change; confirm with `list_workflow_types(prefix="runner.")` and `prefix="data.runner."`.

## When to load

Load this skill when the user wants to:

- Stand up **CI compute** for GitHub Actions or GitLab Runner
- Host **agent sessions** on a runner group
- Create a **DevKit** / local coding group and workspace leases
- Inspect, **drain**, or rotate a **warm pool**
- Debug a **stuck execution** or stuck group creation
- Enable an **Orkestia-hosted** pool, or tear a group down

Always run `whoami()` first. Follow `orkestia-mcp-operating-loop`: schema → start → watch. Omit `organization_uuid` from `initial_data` (injected from the token even when a schema lists it).

## Use cases

| # | Job | Entry point |
|---|---|---|
| 1 | GitHub Actions group on a cloud backend | `data.runner.list-provider-config-specs` then `runner.group-creation` |
| 2 | DevKit / local coding group + workspace leases | `runner.group-creation` (`backend_type=devkit`) then `runner.workspace-lease.*` |
| 3 | Enable the group as an agent host | `agents.runner-group.enable` (group must be `ACTIVE`) |
| 4 | Debug a running or stuck execution | `data.runner.list-executions` / `list-stuck` / `execution-logs-tail` |
| 5 | Warm pool: status, drain, rotate, reconcile | `data.runner.pool-status`, `runner.pool-drain` / `pool-rotate` / `pool-reconcile-*` |
| 6 | Demand-driven scale | `github.workflow-job` → `runner.dispatch-from-job-queued`; operator nudge `runner.scale-check-group` |

Worked `initial_data` for hosted pools, teardown, coding runtime, GitHub group bind, and ACR mirrors: [examples.md](examples.md). Backend config keys and family map: [reference.md](reference.md).

## How to (recipes)

### 1. Create a GitHub Actions group on a cloud backend

**Prereqs (other skills).** You need a provider `CloudConnection` UUID (`connection.query` — `orkestia-connections`). Optionally bind launch networking (`network_profile_uuid`) and image resolution (`registry_account_uuid`) — `orkestia-registry-network`. For `integration_type=github` you must supply `github_installation_uuid` yourself; there is no list workflow.

1. `start_workflow("data.runner.list-provider-config-specs", {})` and take the row whose `backend_type` matches the group. Fill every name in `required_keys` under `config`.
2. Confirm `get_workflow_schema("runner.group-creation")`. Required: `name`, `backend_type`, `purpose`, `integration_type`, `runner_scope`. Cloud backends also need `cloud_connection_uuid` and usually `region` (omit `region` only for bring-your-own Kubernetes).
3. Start the DAG, then `watch_workflow`:

```json
{
  "name": "gha-fargate-prod",
  "backend_type": "fargate",
  "purpose": "github_actions",
  "integration_type": "github",
  "runner_scope": "organization",
  "cloud_connection_uuid": "<aws-connection-uuid>",
  "github_installation_uuid": "<installation-uuid>",
  "region": "us-east-1",
  "min_count": 1,
  "max_count": 10,
  "runner_labels": ["orkestia", "linux"],
  "config": { "ecs_cluster_name": "<ecs-cluster-name>" }
}
```

`min_count` is the warm floor (runners kept registered so jobs claim immediately). `max_count` is the launch cap. Optional: `network_profile_uuid`, `registry_account_uuid`, `image_pull_cloud_connection_uuid`.

4. When the run is terminal, `start_workflow("data.runner.get-group", { "runner_group_uuid": "<uuid>" })` and wait until `status` is `ACTIVE` before enabling agents or expecting CI jobs.

**Re-provision** an existing row (after abort, or to retry infra): pass `runner_group_uuid` into `runner.group-creation` together with the same required fields (`name`, `backend_type`, `purpose`, `integration_type`, `runner_scope`). Supply that UUID only when the row already exists.

**Stuck creation.** `data.runner.list-stuck` (optionally `workflow_type: "runner.group-creation"`). Then `runner.group-creation-abort` with `runner_group_uuid` (force-fails the in-flight run and resets status). `runner.group-reset-status` is the inner reset only (sets `ERROR`, clears `active_workflow_uuid`). After abort, re-enter `runner.group-creation` with the same `runner_group_uuid`.

Do not start `runner.group-creation.prepare` / `.finalize`. Patch labels or counts later with `runner.group-update` (DAG; can also reconcile coding storage). `data.runner.group-update` patches the row **without** re-provisioning.

### 2. Create a DevKit / local coding group

DevKit is provider-blind local compute. **Omit** `cloud_connection_uuid`. `backend_type=devkit` is not in the config-spec catalogue — do not invent `config` keys.

```json
{
  "name": "staff-devkit",
  "backend_type": "devkit",
  "purpose": "agent",
  "integration_type": "none",
  "runner_scope": "organization",
  "min_count": 0,
  "max_count": 4
}
```

Hosts register themselves with `runner.instance-register` (protocol v2: `executor_key`, `protocol_version`, `software_version`, `capabilities`, `max_concurrency`) and stay alive via `runner.instance-heartbeat`. Drain / resume: `runner.instance-drain`, `runner.instance-resume`. You rarely start those from MCP unless you *are* the host.

**Workspace leases** bind a Staff coding session to a worktree (see `orkestia-tickets` for `ticket_git_work_uuid`):

1. `runner.workspace-lease.request` — `actor_uuid` (injected), `agent_session_uuid`, `runner_execution_uuid`, `ticket_git_work_uuid`
2. Host claims: `runner.workspace-lease.claim` (`runner_execution_uuid`, `executor_uuid`)
3. `runner.workspace-lease.heartbeat` while the session runs; `runner.workspace-lease.complete` when done
4. Read: `data.runner.workspace-lease.get` (lease UUID or execution UUID)

Claimable DevKit work: `data.runner.list-claimable`. Executions: `runner.execution-claim-next` / `execution-heartbeat` / `execution-complete`. Safe retry: `runner.execution-safe-retry`, `execution-retry-ready`, `execution-retry-reject`.

### 3. Enable a group as an agent host

The group must already be **ACTIVE** (`data.runner.get-group`). Creating with `purpose=agent` is not enough until enable runs.

```json
{ "runner_group_uuid": "<uuid>", "agent_max_concurrent": 2 }
```

`start_workflow("agents.runner-group.enable", …)`. Output includes `supports_agents`. Disable: `agents.runner-group.disable` (blocked while sessions are active). Sessions themselves are `orkestia-agents` (`agents.session-launch`).

Filter agent-capable groups: `data.runner.list-groups` with `agent_eligible_only: true` or `purpose: "agent"`.

### 4. Debug a running or stuck execution

1. `data.runner.list-executions` — optional `runner_group_uuid`, `status`, `limit` / `offset`. Read `items[].uuid`.
2. `data.runner.get-execution` with `runner_execution_uuid` — `status`, `stop_reason`, `failure_category`, `blocker`, `claim_watch`, `workspace_lease_uuid`, `agent_session_uuid`.
3. `data.runner.execution-logs-tail` — `runner_execution_uuid`, optional `tail` (default 200) and `since`. These are **already synced** events; backend `runner.execution-logs-sync-*` is what pulls from the provider.
4. Group-level stuck **engine** runs: `data.runner.list-stuck` (`older_than_seconds` default 600, optional `workflow_type`).
5. Pending coding jobs that never schedule: `data.runner.list-scheduling-diagnostics` (`runner_group_uuid`). Stale DevKit claims: `data.runner.list-stale-claims`.
6. Recovery: `retry_workflow` / `list_stuck_workflows` from the operating loop for engine runs; `runner.group-creation-abort` for a stuck **group**; `runner.execution-stop-<backend>` only when you must free a slot (GitHub `completed` already does this — recipe 6).

### 5. Warm pool: status, drain, rotate, reconcile

1. `data.runner.pool-status` with `runner_group_uuid`. Read `warm_pool_enabled`, `composition` (`provisioning` / `warm_idle` / `busy` / `draining` / `failed` / `terminated_in_last_5m`), `config`, and `per_instance`.
2. **Drain** (PENDING/IDLE/BUSY → DRAINING; busy finish the current job): `runner.pool-drain` `{ "runner_group_uuid": "<uuid>", "reason": "maintenance" }`.
3. **Rotate** (drain + nudge reconcile so the controller re-launches to the floor — AMI / hygiene / emergency replace): `runner.pool-rotate` with the same UUID + `reason`.
4. **Reconcile** (controller tick toward `min_warm_idle` / `max_count`). Prefer the backend-specific featured type:
   - `runner.pool-reconcile-ec2-vm`
   - `runner.pool-reconcile-gce`
   - `runner.pool-reconcile-fargate`
   - `runner.pool-reconcile-azure-vm`
   - `runner.pool-reconcile-kubernetes` (hosted Kubernetes pools)
   
   Input is `runner_group_uuid` (optional `queued_demand_hint` on the EC2 VM type). `runner.pool-reconcile` without a suffix is an **adapter** for parent specs — do not start it from MCP unless a schema you are composing names it.

**Do not start** `runner.pool-sweep-ec2-vm`. It is **DEPRECATED** (superseded by `runner.pool-reconcile-ec2-vm`); nothing schedules it anymore.

Per-instance kill: `runner.instance-terminate-ec2-vm` / `-gce` / `-fargate` / `-azure-vm` / `-kubernetes`.

### 6. Demand-driven scale

You almost never start dispatch yourself. GitHub `workflow_job` webhooks do:

- `queued` → `runner.dispatch-from-job-queued` (pick an **ACTIVE** group whose `runner_labels` cover the job; launch up to `max_count`)
- `in_progress` → claim-watch
- `completed` → `runner.execution-stop-<backend>` (frees the capacity slot)

See `orkestia-github` (`github.workflow-job` / `github.workflow-job-handle`).

**Operator nudge** when a group is under floor or webhooks are missing: `runner.scale-check-group` with `runner_group_uuid` (optional `batch_limit`). It reconciles active executions, then launches enough to satisfy `max(min_count, demand)` up to `max_count`. `min_count` is the warm floor; `max_count` is the launch cap.

Manual dispatch (same contract the webhook uses): `repository_full_name` + `runner_labels` required; optional `github_job_ref`, `github_workflow_run_ref`.

## Object model

```
RunnerGroup  →  environment (cloud infra, or DevKit registrations)
             →  RunnerExecution   (one launched job / session)
             →  RunnerInstance    (warm-pool or DevKit host row)
             →  workspace lease   (Staff coding session ↔ execution)
```

**Four create-time choices** (`runner.group-creation`):

| Field | Values |
|---|---|
| `backend_type` | `devkit`, `fargate`, `ec2_auto_scaling`, `ec2_vm`, `gce`, `cloud_run`, `kubernetes`, `eks`, `azure_container_apps_job`, `azure_vm`, `azure_vmss`, `do_app_job`, `do_droplet`, `mgc_vm` |
| `purpose` | `github_actions`, `gitlab_runner`, `generic`, `agent` |
| `integration_type` | `github` (`github_installation_uuid`), `gitlab` (`gitlab_connection_uuid` + project/group target), `none` |
| `runner_scope` | `organization`, or `repository` (GitHub only; needs `github_repository_uuid`) |

The group-creation DAG: prepare → optional `storage.coding-artifact-bucket.ensure` → backend `environment-provision*` (fargate, ec2, gce, cloud_run, kubernetes/eks, azure container apps, do_app_job, ec2_vm) → builder reconcile → optional hosted `pool-rotate` → finalize. Other backends still take `backend_type` + config-spec keys; verify the live DAG with `get_workflow_dag("runner.group-creation")`.

`hosted: true` on `data.runner.get-group` is **tenancy** (Orkestia-paid compute), not a backend. Hosted pools are ordinary `kubernetes` or `azure_vm` groups created by `runner.hosted-tenant-provision`.

## Day-to-day reads (`data.runner.*`)

All `read_only` featured reads below are safe to start. Pass only the UUIDs the schema requires.

| Workflow | When |
|---|---|
| `list-groups` / `get-group` | Inventory; `get-group` is the status/bindings snapshot |
| `list-executions` / `get-execution` | Jobs and sessions |
| `execution-logs-tail` | Synced log tail |
| `pool-status` / `list-instances` | Warm pool composition |
| `list-events` / `list-resources` | Group lifecycle + tracked cloud objects |
| `list-stuck` | Idle auto-advance runner workflows |
| `list-provider-config-specs` / `get-provider-config-spec` | `config` keys before create |
| `list-scheduling-diagnostics` / `list-stale-claims` | Coding / DevKit scheduling |
| `workspace-lease.get` | One lease |
| `environment-build.get` / `.list` | Immutable environment builds |
| `repository-profile.get` / `.list` | Per-repo execution profiles |
| `list-azure-environments` | Azure Container Apps environments visible to a connection |
| `list-claimable` | Pending DevKit correlations |
| `execution-assignment.get` | Provider-blind assignment envelope |

Skip from MCP unless a parent schema names them: `data.runner.group-persist`, `data.runner.group-get`, `data.runner.list-active-warm-pool-groups` (cross-org controller feed).

## Gotchas

- **`github_installation_uuid` has no list workflow.** Supply it from the org's GitHub App installation. Same for `gitlab_project_uuid`.
- GitHub **`workflow_job`** drives dispatch **and** slot-freeing (`orkestia-github`). Starting `dispatch-from-job-queued` twice for the same job fights that path.
- **`min_count`** = warm floor; **`max_count`** = launch cap. Warm-pool controllers converge toward `min_warm_idle` / `max_count` (see `pool-status.config`).
- **`runner.pool-sweep-ec2-vm` is DEPRECATED.** Use `runner.pool-reconcile-ec2-vm`.
- Secret hygiene: `runner.execution-secrets-purge` scrubs `environment` / log keys from execution metadata (one execution **or** a group, optional time bounds, `dry_run`, audited). Idempotent.
- `agents.runner-group.enable` refuses unless the group is **ACTIVE**. Disable refuses while sessions are active.
- Coding runtime (`coding_runtime_enabled`) needs `coding_artifact_storage_connection_uuid`. Capacity **512 MiB–1 TiB**, retention **7–90 days**. Artifacts live in tickets/storage (`orkestia-tickets`).
- Hosted pools are subscription-gated (`orkestia-subscription`). `runner.hosted-usage-reconcile` writes one **BillableEvent** per newly-terminal hosted execution and stops runs past `max_session_duration_s`.
- Do not start `__pre` / `__post` steps, `*.prepare` / `*.finalize` children, or `data.runner.group-persist`.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, schema, watch, retry / remediate
- `orkestia-connections` — `cloud_connection_uuid` / image-pull connection
- `orkestia-registry-network` — `registry_account_uuid`, `network_profile_uuid`
- `orkestia-github` — App install UUID, `workflow_job` dispatch and slot-freeing
- `orkestia-agents` — `agents.runner-group.enable`, session launch
- `orkestia-subscription` — hosted-pool entitlement and metering
- `orkestia-tickets` — git-work UUID, coding artifacts, delivery governance

## Additional resources

- Backend config keys, execution `*-generic` / `*-agent` variants, and job-grouped workflow map: [reference.md](reference.md)
- Worked `initial_data` (hosted pool, teardown, coding runtime, GitHub bind, ACR mirror): [examples.md](examples.md)
