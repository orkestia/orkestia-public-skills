---
name: orkestia-mcp-operating-loop
description: The universal loop for operating Orkestia through its public MCP server — identity, catalog discovery, schema and prerequisite checks, starting and watching runs, and recovering stuck or gated workflows. Load this first whenever working with any orkestia-core MCP tool; every domain skill assumes it.
---

# Orkestia MCP operating loop

Orkestia exposes no REST endpoints and no source to its users. Every capability is a **registered, schema-typed workflow** discovered and run through the public MCP server. The catalog (snapshot 2026-08-20: 2,374 types, 67 namespaces — 1,946 state machines, 287 data reads, 141 DAGs) is the single source of truth; never claim a capability you did not read from a tool result.

## The loop

```
whoami() → list_workflow_namespaces() → list_workflow_types(prefix=...)
  → get_workflow_schema(type) → get_workflow_prerequisites(type)   # when has_prerequisites
  → start_workflow(type, initial_data) → watch_workflow(id) | get_workflow_status(id)
```

## Rules

1. **Identity is server-side.** `whoami()` returns your `organization_uuid`, resolved from the Bearer token; it scopes every run automatically. Never ask a user for it and never pass it in `initial_data` unless the schema explicitly declares it (schemas that do inject it from context).
2. **Reads are safe, mutations deserve a schema check.** Rows with `read_only: true` (ReadOnlyDataWorkflow) and the whole `data.*` namespace can be started freely. For creates/modifies, read the schema first and confirm intent.
3. **Prerequisites before starts.** If `get_workflow_schema` returns `has_prerequisites: true`, call `get_workflow_prerequisites(type, variant=...)` — it renders a per-provider setup guide with Orkestia's own identity (e.g. its AWS principal for trust policies) already filled in server-side.
4. **DAGs are inspectable.** `get_workflow_dag(type)` shows layers, steps, child workflow types, and compensation steps. `get_workflow_definition(type)` gives the full state machine.
5. **Recovery is built in.**
   - `list_stuck_workflows` — non-terminal runs idle too long.
   - `retry_workflow(id)` — re-run eligible failures.
   - **Remediation gate:** a DAG step that fails on a *fixable* precondition parks the run in `remediation_pending` instead of compensating. Read `state_data.remediation` via `get_workflow_status`; apply the suggested fix (often a `kind="workflow"` option naming the fix workflow), then `resolve_workflow(id, resolution="remediated")` — only the failed step re-runs, earlier outputs are kept. `resolution="denied"` compensates and fails the run.
6. **Routing hints on every row.** `featured: true` marks human-runnable entry points — prefer them and skip internal `*-validate` / `*-complete` / `*.prepare` sub-steps. `scope` says what a workflow binds to: `organization` (1,391), `library` (381), `subscription` (26), `app` (12), `actor` (3).
7. **Ground every claim.** A registered type is a capability, not evidence of a run. Catalog `total` is a capability count. To say what *ran*, read run tools or `audit.workflow-run.query`. Virtual (composition) types never appear in `list_workflow_types` — absence there means "not a catalog type", not "none exist".

## Cross-domain dependency map

- `connection.*` is the credential root: runner groups, registry accounts, network accounts, GitHub/GitLab bindings, storage, and AI model bindings all reference a CloudConnection UUID.
- `ticket.*` is the shared work ledger every domain writes into.
- `subscription.*` gates paid surfaces (hosted runners, app hosting, seats).
- `composition.*` output (virtual workflows) is the only business logic app end-users may run.
