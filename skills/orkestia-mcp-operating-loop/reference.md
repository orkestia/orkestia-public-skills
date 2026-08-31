# MCP tool map (by job)

Live catalog shape (verify with `list_workflow_namespaces`, do not freeze): kinds `dag` / `data` / `state_machine`; scopes `organization`, `none`, `library`, `subscription`, `app`, `actor`, `project`, `system`. Namespace `user-orkestia` (server `orkestia-core`).

Every tool below is a real MCP tool. `workspace_id` is accepted and ignored on most calls.

## Authenticate and identify

| Tool | When |
|---|---|
| `mcp_auth` | Namespace `needsAuth`, or a prior call failed with an authentication error. Empty arguments. Then call `whoami`. |
| `whoami` | First call of every session, and after re-auth. Returns `user_id`, `organization_uuid`, `organization_id` (alias), `username`, `token_type`, `principal_type`. Org is applied to runs server-side. |

Never ask the user for `organization_uuid`. Omit `initial_data` fields with `source.kind` `context`. If a schema declares `organization_uuid` without context injection, pass the `whoami` value and it must match.

## Discover the catalog (types, not runs)

| Tool | When |
|---|---|
| `list_workflow_namespaces` | Cheap first map: `total`, `first_level`, `second_level`, `by_kind`, `by_scope`. |
| `list_workflow_types` | Browse or search **types**. Filters: `prefix`, `q` (keyword AND over name + description), `featured` (`true` / `false` / omit), `limit` (0–500; **0 = overlays only**), `offset`, `detail`. With no `prefix` and `offset` 0, also returns `namespaces`, `featured` (capped page), `featured_total`, `recent_activity`. |

`list_workflow_types` does **not** list runs. Compiled `virtual.*` types **may** appear under `prefix="virtual."`; that is not the composition inventory — use `data.composition.list` (`orkestia-compositions`). Empty browse does not mean the org has none.

## Inspect one type (still not a run)

| Tool | When |
|---|---|
| `get_workflow_schema` | Required inputs, `read_only`, `has_prerequisites`, `field_groups`, DAG summary. Prefix match returns `{prefix, message, workflows: [...]}`. |
| `get_workflow_definition` | Full behavior: fields, kind, DAG, declared state machine (states, transitions, timeouts). Prefer this when the user asks what a type *does*. |
| `get_workflow_dag` | Layers, steps (`name` + `workflow_type`), compensate. Returns `is_dag: false` when the type is not a DAG. |
| `get_workflow_prerequisites` | Only when schema/definition has `has_prerequisites: true`. Pass `variant` (e.g. `"aws"` on `connection.setup`). Markdown guide includes platform identity (`resolved_values`). |

## Start, wait, and read one run

| Tool | When |
|---|---|
| `start_workflow` | Create a run. Required: `workflow_type`, `initial_data`. Returns `workflow_id` plus an initial snapshot (`state_name`, `is_terminal`, `state_data`, …). |
| `watch_workflow` | Block until terminal (SSE). Use instead of polling. Default `timeout_seconds` 300. Same terminal shape as status. |
| `get_workflow_status` | One-shot latest snapshot, including `state_data`. Use this to read `state_data.remediation`. |
| `get_workflow_history` | Chronological states, oldest first. Default omits `state_data`. Unknown id → `{error: "NotFoundError", message: "Workflow not found"}`. |

## Query many runs

| Tool | When |
|---|---|
| `list_workflows` | Runs of **one** `workflow_type`. Optional `state_name`, `is_terminal`, `limit`, `include_state_data`. Envelope `{workflows, count, limit, has_more}`. How you find `remediation_pending` for a known type. |
| `list_stuck_workflows` | Non-terminal auto-advance runs idle too long. Optional `workflow_type`, `older_than_minutes` (default 10), `stuck_for_seconds` (overrides minutes). Rows include `stuck_for_minutes`, `probable_cause`, `suggested_action`. Keep `include_state_data` false. |
| `audit.workflow-run.query` | **Workflow**, not MCP tool: org-scoped run list across types (`workflow_type_prefixes`, time range, actor). `read_only: true`. Use when you do not have a single type, or when hunting virtual runs. Pair with `audit.workflow-run.get-history` and `audit.workflow-run.aggregate`. |

## Recover a run

| Tool | Use when | Do not use when |
|---|---|---|
| `retry_workflow` | Terminal **failed** run; cause addressed. Optional `resolution_method`, `resolution_reason`. | `remediation_pending`, still running, already succeeded. |
| `resolve_workflow` | `remediation_pending` gate. `resolution`: `"remediated"` (fix applied — re-run only the failed step) or `"denied"` (compensate and fail). Optional `reason`, `resolved_by`. | Terminal failed (use retry). Stale abandon (use force terminate). |
| `force_terminate_workflow` | Last resort: confirmed stale **non-terminal** run to abandon. Required `reason`. Guards: `expected_state_name`, `expected_workflow_type`, `older_than_minutes` (default 10). Result is unrecoverable failed. | Terminal runs, fresh runs, “maybe it will finish,” gated runs you still intend to fix. |

## Visual console and engine diagnostics

| Tool | When |
|---|---|
| `open_app` | User wants to **see** fleet / cluster / namespace. Optional `route`: `/fleet` (default), `/cluster/<connection_uuid>`, `/cluster/<connection_uuid>/ns/<namespace>`. Do not start the same Kubernetes workflows in that turn. One-sentence comment after open. |
| `list_plugins` | Engine plugins (`connection`, `aws`, `github`, `gcp`, `stripe`, …). Diagnose missing provider access. Not a substitute for `list_workflow_types`. |

## Catalog vs run cheat sheet

| Question | Tool |
|---|---|
| What namespaces exist? | `list_workflow_namespaces` |
| What can I start? | `list_workflow_types` (`q` / `prefix` / `featured`) |
| What does this type need? | `get_workflow_schema` / `get_workflow_definition` |
| What layers does this DAG have? | `get_workflow_dag` |
| What ran? | `list_workflows` or `audit.workflow-run.query` |
| Why is this id stuck? | `list_stuck_workflows` then `get_workflow_status` |
| Show me the cluster | `open_app` |

## Cross-domain objects (not extra MCP tools)

Operate these through the same loop; domain skills list the types.

- **Connection** — credential root. Entry: `connection.setup` (prerequisites + `field_groups`). Reads: `connection.query`, `connection.get`. Internals (do not start): `connection.validate_credentials`, `connection.test_connection`, `connection.persist_connection`, `connection.sync_resources`.
- **Ticket** — work ledger (`ticket.open`, `ticket.transition`, …).
- **Subscription** — paid-surface gate (`subscription.*`).
- **Composition** — virtual workflows for app end-users (`composition.save` / `activate`; `identity.app.expose-virtual-workflow`). `control.*` primitives are building blocks, not user entry points by themselves.
- **Featured vs internal names** — skip `*.prepare`, `*-validate`, `*-complete`, `__pre`/`__post`, `ticket._scheduler.poll`, `agents._ft-dataset.*`, `runner.group-creation.prepare`. Start parents such as `connection.setup`, `k8s.app.deploy`, `runner.environment-build.request`.

## `list_workflow_types` argument recipes

```
list_workflow_types(limit=0)                          # overlays only
list_workflow_types(q="query connections")            # keyword AND
list_workflow_types(prefix="connection.")             # one namespace
list_workflow_types(prefix="connection.", featured=true)
list_workflow_types(prefix="aws.ec2.", detail=true, limit=20)
```
