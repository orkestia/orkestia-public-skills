# Runner worked scenarios

Omit `organization_uuid` from every `initial_data` object. Watch mutating runs with `watch_workflow`. UUIDs below are placeholders.

## 1. Orkestia-hosted pool (subscription-gated)

Platform-paid compute. One hosted pool per backend (`kubernetes` default, or `azure_vm`). Idempotent — re-enable returns the existing pool. Entitlement: `orkestia-subscription`.

```json
{
  "workflow_type": "runner.hosted-tenant-provision",
  "initial_data": {
    "name": "Orkestia hosted runners",
    "backend_type": "kubernetes"
  }
}
```

Confirm `data.runner.get-group` shows `hosted: true` and `status` ACTIVE. Then `agents.runner-group.enable` if sessions should land here (SKILL.md recipe 3).

Metering tick (stops overruns past `max_session_duration_s`, one **BillableEvent** per newly-terminal execution):

```json
{
  "workflow_type": "runner.hosted-usage-reconcile",
  "initial_data": { "runner_group_uuid": "<hosted-group-uuid>" }
}
```

Disable (refuses while work is in flight unless `force`):

```json
{
  "workflow_type": "runner.hosted-tenant-disable",
  "initial_data": { "backend_type": "kubernetes" }
}
```

## 2. Tear down a group and purge execution secrets

1. Optional dry-run purge first:

```json
{
  "workflow_type": "runner.execution-secrets-purge",
  "initial_data": {
    "runner_group_uuid": "<group-uuid>",
    "dry_run": true,
    "limit": 500,
    "reason": "pre-delete hygiene"
  }
}
```

2. Drop `dry_run` (or set `false`) to scrub `environment` / log keys. Target one execution with `runner_execution_uuid` instead of the group (mutually exclusive). Time-bound with `created_after` / `created_before`. If `truncated` is true, re-run.

3. Delete infrastructure:

```json
{
  "workflow_type": "runner.group-deletion",
  "initial_data": { "runner_group_uuid": "<group-uuid>" }
}
```

Do not start `group-deletion.deregister` / `.finalize`. For hosted pools use scenario 1 disable, not this DAG.

## 3. Enable coding runtime + artifact storage

Needs a customer storage `CloudConnection` (`orkestia-connections`). Capacity 512 MiB–1 TiB; retention 7–90 days. Artifact lifecycle is `orkestia-tickets` (`ticket.coding-artifact.*` / storage).

**At create** (agent + DevKit shown; same fields work on hosted Kubernetes / Azure VM agent groups):

```json
{
  "workflow_type": "runner.group-creation",
  "initial_data": {
    "name": "devkit-coding",
    "backend_type": "devkit",
    "purpose": "agent",
    "integration_type": "none",
    "runner_scope": "organization",
    "max_count": 2,
    "coding_runtime_enabled": true,
    "coding_artifact_storage_connection_uuid": "<storage-connection-uuid>",
    "coding_artifact_capacity_bytes": 536870912,
    "coding_artifact_retention_days": 30
  }
}
```

**On an existing group** — `runner.group-update` (DAG reconciles the bucket). Re-read that schema before clearing `coding_runtime_enabled`; the field description says disable is not a casual flag flip.

```json
{
  "workflow_type": "runner.group-update",
  "initial_data": {
    "runner_group_uuid": "<group-uuid>",
    "coding_runtime_enabled": true,
    "coding_artifact_storage_connection_uuid": "<storage-connection-uuid>",
    "coding_artifact_capacity_bytes": 1073741824,
    "coding_artifact_retention_days": 14
  }
}
```

The create DAG calls `storage.coding-artifact-bucket.ensure` when those fields are set.

## 4. Bind an existing GitHub organization runner group

Does **not** create or move GitHub runners. The Orkestia group must already exist (recipe 1). `github_runner_group_ref` is GitHub's integer group id.

```json
{
  "workflow_type": "runner.github-runner-group.bind-existing",
  "initial_data": {
    "runner_group_uuid": "<orkestia-group-uuid>",
    "github_runner_group_ref": 123456,
    "github_runner_group_name": "production-linux"
  }
}
```

`github_runner_group_name` is optional; when set, the live GitHub name must match exactly.

Then associate already-registered org runners (still no create/delete):

```json
{
  "workflow_type": "runner.github-runner-group.add-existing-runners",
  "initial_data": { "runner_group_uuid": "<orkestia-group-uuid>" }
}
```

Confirm bindings on `data.runner.get-group` (`github_runner_group_ref`, `github_runner_group_name`).

## 5. Ensure an ACR cache-rule mirror

For Azure-backed groups that pull through ACR. Input is the Orkestia group; the DAG validates, stores the pull secret, grants IAM, ensures the mirror repository, verifies, finalizes.

```json
{
  "workflow_type": "runner.acr-registry-mirror-ensure",
  "initial_data": { "runner_group_uuid": "<azure-group-uuid>" }
}
```

Later: `runner.acr-registry-mirror-reconcile` (same UUID). Teardown: `runner.acr-registry-mirror-teardown`. Cloud Run equivalent: `runner.cloud-run-registry-mirror-ensure`.

## 6. Operator scale-check when webhooks are quiet

Prefer GitHub `workflow_job` (`orkestia-github`) for day-to-day demand. If the group is below `min_count` or queued jobs are not launching:

```json
{
  "workflow_type": "runner.scale-check-group",
  "initial_data": {
    "runner_group_uuid": "<group-uuid>",
    "batch_limit": 3
  }
}
```

`batch_limit` caps launches this call (default: remaining headroom to `max_count`). Then `data.runner.pool-status` or `data.runner.list-executions`.

Manual analogue of the webhook queued path:

```json
{
  "workflow_type": "runner.dispatch-from-job-queued",
  "initial_data": {
    "repository_full_name": "acme/api",
    "runner_labels": ["orkestia", "linux"],
    "github_job_ref": 987654321
  }
}
```

Use this only when you are replaying a known queued job; the live webhook already calls it.
