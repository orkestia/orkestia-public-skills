# Worked examples

Placeholder ids (`wf_abc123`, connection UUIDs) are examples. Copy tool names and argument keys; substitute live values. Never put `organization_uuid` in `initial_data` unless a schema requires it without context injection.

## 1. Orient: identity, namespaces, find a type by keyword

The user says “what can you do?” or “list my cloud connections” without naming a workflow.

```
whoami()
list_workflow_namespaces()
list_workflow_types(limit=0)
list_workflow_types(q="query connections")
```

`whoami` returns `organization_uuid` (server-side; do not echo it back as a question). `list_workflow_namespaces` returns `total`, `first_level` (e.g. `connection`, `ticket`, `runner`, `data`), `by_kind`, `by_scope`. `limit=0` adds `featured`, `featured_total`, `recent_activity` without paging thousands of rows.

`q="query connections"` matches types whose name **and** description contain those terms (AND). A typical hit:

- `connection.query` — “List cloud connections for an organization”, `read_only: true`
- `data.connection.query` — compatibility alias, also `read_only: true`

If you already know the namespace:

```
list_workflow_types(prefix="connection.", limit=50)
```

Then `get_workflow_schema(workflow_type="connection.query")`. Required field `organization_uuid` has `source.kind: context` — omit it.

If tools fail with auth, call `mcp_auth()` (no arguments) and `whoami` again.

## 2. Safe read vs mutation

**Read (start freely).** Schema: `read_only: true`, `has_prerequisites: false`.

```
get_workflow_schema(workflow_type="connection.query")
start_workflow(
  workflow_type="connection.query",
  initial_data={},
  triggered_by="mcp:agent"
)
```

Optional filter (keys go **inside** `filters`, not as top-level `connection_type`):

```
start_workflow(
  workflow_type="connection.query",
  initial_data={"filters": {"connection_type": "neon"}},
  triggered_by="mcp:agent"
)
```

**Mutate (schema + confirm + prerequisites).** User: “wire AWS.”

```
get_workflow_schema(workflow_type="connection.setup")
get_workflow_prerequisites(workflow_type="connection.setup", variant="aws")
```

Schema: `read_only: false`, `has_prerequisites: true`, `field_groups.aws` = `external_ref`, `regions`, `role_arn`. Fill **only** the `aws` group plus `provider_type` / `connection_name`. Hand the prerequisite markdown to the user (IAM trust policy already contains Orkestia’s principal). After they confirm the role exists:

```
start_workflow(
  workflow_type="connection.setup",
  initial_data={
    "provider_type": "aws",
    "role_arn": "arn:aws:iam::123456789012:role/OrkestiaAccess",
    "external_ref": "ext-prod-aws-001",
    "connection_name": "prod-aws",
    "regions": ["us-east-1"]
  },
  triggered_by="mcp:agent"
)
```

Do not start DAG internals `connection.validate_credentials`, `connection.test_connection`, `connection.persist_connection`, or `connection.sync_resources`.

## 3. Start, watch, read terminal `state_data`

Continue from a read-only start. Fast data/state-machine reads often return `is_terminal: true` immediately:

```
{
  "workflow_id": "wf_abc123",
  "workflow_type": "connection.query",
  "state_name": "completed",
  "is_terminal": true,
  "terminal_status": "success",
  "state_data": {
    "connections": [ { "uuid": "…", "name": "…", "connection_type": "neon", "status": "active" } ],
    "count": 1,
    "filters": {}
  }
}
```

For a longer DAG (`k8s.app.deploy`):

```
get_workflow_dag(workflow_type="k8s.app.deploy")
start_workflow(workflow_type="k8s.app.deploy", initial_data={...schema fields...})
watch_workflow(workflow_id="wf_abc123", timeout_seconds=300)
```

If watch times out, `get_workflow_status(workflow_id="wf_abc123")`. History without bulky payloads:

```
get_workflow_history(workflow_id="wf_abc123", limit=20, include_state_data=false)
```

A 3-state read typically has `pending` then `completed`. Turn `include_state_data` on only for the run you are debugging.

When the user wants the **fleet on screen** instead of this prose:

```
open_app(route="/fleet")
```

or `route="/cluster/<connection_uuid>"`. Do not also start Kubernetes list workflows in that turn.

## 4. Retry a failed run

User: “that connection validate failed — try it again.”

```
get_workflow_status(workflow_id="wf_failed1")
get_workflow_history(workflow_id="wf_failed1", include_state_data=true)
```

Confirm `state_name` is `failed` and `is_terminal` is true. Read `state_data.failure_reason` (or `error`). Fix the external cause if any, then:

```
retry_workflow(
  workflow_id="wf_failed1",
  resolution_method="config_change",
  resolution_reason="Rotated the provider token and re-tested",
  triggered_by="mcp:agent"
)
```

Then `watch_workflow(workflow_id="wf_failed1")`.

Find other failures of the same type:

```
list_workflows(workflow_type="connection.validate", state_name="failed", is_terminal=true, limit=20)
```

`retry_workflow` rejects non-failed and non-terminal runs. A parked gate is example 5, not a retry.

## 5. Remediation gate: read envelope, fix, resolve

User: “the deploy is waiting on remediation.”

```
list_workflows(workflow_type="k8s.app.deploy", state_name="remediation_pending", is_terminal=false)
get_workflow_status(workflow_id="wf_gated1")
```

`state_data.remediation` names the failed step and options. Typical option:

```
{
  "kind": "workflow",
  "ref": "connection.validate",
  "inputs": { "cloud_connection_uuid": "$state.cloud_connection_uuid" }
}
```

Resolve `"$state.…"` against this run’s `state_data`, start the fix, watch it, then close the gate:

```
start_workflow(workflow_type="connection.validate", initial_data={"cloud_connection_uuid": "<from state>"})
watch_workflow(workflow_id="wf_fix1")
resolve_workflow(
  workflow_id="wf_gated1",
  resolution="remediated",
  resolved_by="agent",
  reason="Re-validated the cluster connection after token rotation",
  triggered_by="mcp:agent"
)
```

Only the failed DAG step re-runs; earlier layer outputs are kept. If the user refuses the fix:

```
resolve_workflow(
  workflow_id="wf_gated1",
  resolution="denied",
  reason="User declined to repair the connection; abandon this deploy",
  triggered_by="mcp:agent"
)
```

Compensation runs and the parent fails terminally.

## 6. Stuck run, virtual types, and internals

**Stuck / stale.** User: “why is this still running?”

```
list_stuck_workflows(older_than_minutes=10, limit=50)
get_workflow_status(workflow_id="wf_stale1")
get_workflow_history(workflow_id="wf_stale1", include_state_data=true)
```

Use `probable_cause` / `suggested_action`. Then:

- Terminal failed → example 4 (`retry_workflow`).
- `remediation_pending` → example 5 (`resolve_workflow`).
- Confirmed stale, non-terminal, abandon (resources gone or cleaned up):

```
force_terminate_workflow(
  workflow_id="wf_stale1",
  reason="Idle 45m in pending after the cluster was deleted; abandoning leftover run",
  expected_workflow_type="k8s.app.deploy",
  expected_state_name="pending",
  older_than_minutes=10,
  triggered_by="mcp:agent"
)
```

Last resort. Result is unrecoverable failed. The API rejects terminal runs, fresh runs, and guard mismatches.

**Virtual types.** The user names a virtual workflow returned by `composition.save` / `composition.activate` (or exposed with `identity.app.expose-virtual-workflow`). `list_workflow_types(prefix="virtual.")` **may** list compiled org types; do not treat that page (or an empty page) as the composition inventory. Use `data.composition.list`. Keyword search on the human name can miss `virtual.<uuid>@<version>`. Audit actual executions:

```
start_workflow(
  workflow_type="audit.workflow-run.query",
  initial_data={
    "workflow_type": "<virtual type name from composition.save state_data>",
    "limit": 50
  }
)
```

or `workflow_type_prefixes` such as `["virtual."]`. `state_data.items` are run summaries without `state_data` payloads; use `audit.workflow-run.get-history` for one id. If the composition is saved and activated, `start_workflow` on that virtual type name can still succeed — catalog absence is not proof the virtual type does not exist.

**Featured vs internals.** `list_workflow_types(featured=true, prefix="runner.")` still includes wrappers. Do not start:

- `runner.group-creation.prepare`
- `runner.environment-associate-capacity-providers__pre` / `__post`
- `ticket._scheduler.poll`
- `agents._ft-dataset.build-examples`

Start the parent (`connection.setup`, `k8s.app.deploy`, `runner.environment-build.request`). Confirm children with `get_workflow_dag` before you skip them.
