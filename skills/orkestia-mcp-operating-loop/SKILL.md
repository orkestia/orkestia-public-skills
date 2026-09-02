---
name: orkestia-mcp-operating-loop
description: >-
  Operates Orkestia through its public MCP server (orkestia-core / user-orkestia):
  identity, catalog discovery, schema and prerequisite checks, starting and watching
  runs, and recovering failed, gated, or stuck workflows. Load this first whenever
  using any orkestia-core tool; when the user asks what workflows exist, how to find
  a capability, how to start a run, why a run is stuck, or how to retry, resolve, or
  terminate a failure. Every domain skill assumes this loop.
---

# Orkestia MCP operating loop

This skill is the universal how-to for the public MCP server. Orkestia exposes no REST API and no source to callers: every capability is a registered, schema-typed workflow. Call `whoami` first, discover the type, read the schema (and prerequisites when flagged), start a run, watch it, then recover with the matching run tool. Do not invent tool names or workflow types; if a name is not in a tool result, it is not a claim you can make.

```
mcp_auth()            # only when the namespace needs a token
whoami()
list_workflow_namespaces()
list_workflow_types(q=… | prefix=… | limit=0)
get_workflow_schema(type) → get_workflow_prerequisites(type, variant)  # if has_prerequisites
get_workflow_dag(type) | get_workflow_definition(type)                 # DAGs / “what does this do”
start_workflow(type, initial_data) → workflow_id
watch_workflow(id) | get_workflow_status(id)
# recover: retry_workflow | resolve_workflow | force_terminate_workflow
```

## When to load

Load this skill at the start of any Orkestia **MCP** session, before a domain skill. If the user is building an `@orkestia/*` application (CLI, React shell, `*.vw.ts`), load `orkestia-builder` as well — MCP remains how you confirm catalog types and inspect runs. Load it when the user asks what they can do, how to find a workflow they cannot name, whether a start is safe, how to read a finished run, why a run failed or sat idle, or how to retry / resolve / abandon it. Load it when the `user-orkestia` namespace is `needsAuth` or a tool returns an authentication error — call `mcp_auth` with no arguments, then `whoami` again. Load it when the user wants to *see* a fleet or cluster instead of a prose list (`open_app`).

## Use cases

1. **Orient in a new session.** The agent just connected and does not know the org or the catalog. Outcome: identity confirmed, namespaces listed, a capability found by keyword (`q=`).
2. **Safe read vs mutation.** The user wants “list my connections” versus “create an AWS connection.” Outcome: a `read_only: true` (or `data.*`) type is started freely; a mutating type is schema-checked and confirmed before `start_workflow`.
3. **Start and watch.** The user wants a capability executed and the result. Outcome: a `workflow_id`, a terminal snapshot, and `state_data` read as the output.
4. **Retry a failure.** The user asks why a run failed and whether it can be tried again. Outcome: `retry_workflow` on a terminal `failed` run after the cause is understood.
5. **Remediation gate.** A DAG is parked in `remediation_pending` instead of compensating. Outcome: the suggested fix is applied, then `resolve_workflow` with `remediated` (resume) or `denied` (compensate and fail).
6. **Stuck or stale run.** The user asks why a run has not moved. Outcome: `list_stuck_workflows` triage, then retry, resolve, or last-resort `force_terminate_workflow`.
7. **Find or run a composition.** Outcome: inventory via `data.composition.list` (not catalog browse). Compiled types may appear under `prefix="virtual."`; absence there still does not mean the org has none. Audit runs with run tools or `audit.workflow-run.query`.
8. **Featured vs internals.** The catalog is large and full of DAG substeps. Outcome: start the human entry point (`connection.setup`, `k8s.app.deploy`), not `*-validate`, `*.prepare`, `__pre`/`__post`, or underscore internals.

## How to

### 1. Orient (who am I, what exists, find a name)

1. If the namespace is unauthenticated, call `mcp_auth` with empty arguments, then continue.
2. Call `whoami`. Record `organization_uuid`, `user_id`, `username`, `token_type`. Never ask the user for the org id. Never put it in `initial_data` unless that type’s schema declares the field (and then it must match this value). Prefer omitting fields whose schema `source.kind` is `context` — the server injects them.
3. Call `list_workflow_namespaces` for `total`, `first_level`, `by_kind`, and `by_scope`. Treat those numbers as a live snapshot, not a frozen fact.
4. Call `list_workflow_types` with `limit` `0` (no `prefix`) to read overlays only: `namespaces`, `featured` (first page, capped), `featured_total`, `recent_activity`.
5. When you do not know the name, call `list_workflow_types` with `q` set to keywords (every whitespace-separated term must match). Compose `q` with `prefix` and `featured` when you already know a namespace. Example: `q="query connections"` returns `connection.query`.
6. Drill with `list_workflow_types` `prefix="<namespace>."` (include the trailing dot). Page with `limit` / `offset`. Set `detail` `true` only when you need `input_fields` inlined.

### 2. Decide safe-read vs mutation

1. On the type row, read `read_only` and `workflow_kind`. `read_only: true` (ReadOnlyDataWorkflow) and most `data.*` types are safe to start without a side-effect warning.
2. For anything else, call `get_workflow_schema` (inputs, `read_only`, `has_prerequisites`, `field_groups`) or `get_workflow_definition` (states, transitions, DAG). Confirm intent with the user before mutating.
3. If `has_prerequisites` is `true`, call `get_workflow_prerequisites` with `workflow_type` and `variant` (for `connection.setup`, `variant="aws"` and so on). Hand the returned markdown to the user; platform identity is already filled in. Do not start until the guide’s external pre-conditions exist.
4. For DAGs, call `get_workflow_dag` for layers / steps / compensate, or `get_workflow_definition` when you also need the generated parent state machine.

### 3. Start and watch a run

1. Call `start_workflow` with `workflow_type` and `initial_data`. Fill only schema fields the caller must supply. Keep `triggered_by` as a short source such as `"mcp:agent"`.
2. Capture `workflow_id` from the result (shape `wf_…`). That id is the run, not the type.
3. If the snapshot is already `is_terminal: true` (common for fast reads such as `connection.query`), skip waiting and read `state_data`.
4. Otherwise call `watch_workflow` with that `workflow_id` (optional `timeout_seconds`, default 300) instead of polling. Use `get_workflow_status` for a one-shot snapshot, including `state_data.remediation` on a gate.
5. On success, `state_name` is typically `completed`, `terminal_status` is `success`. Domain output lives in `state_data` (for `connection.query`: `connections`, `count`). On failure, read `state_data.failure_reason` / `error` and the history via `get_workflow_history` (`include_state_data` only on the run you are inspecting).

### 4. Recover a failed run (`retry_workflow`)

1. Confirm the run is terminal and failed: `get_workflow_status` (`state_name` `failed`, `terminal_status` `failed`) or `list_workflows` with `workflow_type`, `state_name="failed"`.
2. Read why it failed (`state_data`, or `get_workflow_history` with `include_state_data` `true`). Fix the external cause when there is one.
3. Call `retry_workflow` with `workflow_id`. Optional `resolution_method` / `resolution_reason` are audit notes (for example `"config_change"`). The engine retries from the failed state. This tool rejects runs that are not in a terminal failed state — do not use it on `remediation_pending` or on a still-running run.

### 5. Remediation gate (`resolve_workflow`)

1. Find gated runs with `list_workflows` `state_name="remediation_pending"` (you need the `workflow_type`), or notice `state_name` `remediation_pending` on `get_workflow_status`. The run is **non-terminal**.
2. Read `state_data.remediation`. A typical option has `kind="workflow"`, a `ref` (fix workflow type), and inputs whose `"$state.…"` paths resolve against this run’s `state_data`.
3. Apply the suggested fix first (often `start_workflow` on `ref`). Watch that fix to completion.
4. Call `resolve_workflow` with `resolution="remediated"` so only the failed DAG step re-runs and earlier outputs are kept. Pass `reason` describing the fix. Use `resolution="denied"` to skip the fix: deferred compensation runs and the parent fails terminally.
5. Do not call `retry_workflow` here. Do not call `force_terminate_workflow` unless the user is abandoning the run entirely.

### 6. Stuck or stale run (`list_stuck_workflows` then pick a recovery)

1. Call `list_stuck_workflows` (default `older_than_minutes` 10). Leave `include_state_data` false — a stuck DAG can blow the result size. Each row includes `stuck_for_minutes`, `probable_cause`, and `suggested_action`.
2. Inspect the chosen `workflow_id` with `get_workflow_status` and `get_workflow_history` (`include_state_data` `true` once).
3. Choose **one**:
   - Terminal failed and the cause is fixed → `retry_workflow`.
   - Parked in `remediation_pending` → recipe 5.
   - Confirmed stale, non-terminal, should be abandoned (usually after provider resources are cleaned up or verified absent) → `force_terminate_workflow` with a required `reason`. Optional guards: `expected_state_name`, `expected_workflow_type`, `older_than_minutes` (default 10). This appends an **unrecoverable failed** terminal state. The API rejects terminal runs, fresh runs (younger than the age floor), and state/type mismatches.
4. `force_terminate_workflow` is last resort. Prefer retry or resolve when the run can still succeed.

| Run looks like | Tool |
|---|---|
| Terminal `failed`, cause fixed | `retry_workflow` |
| `state_name` is `remediation_pending` | `resolve_workflow` (`remediated` / `denied`) |
| Non-terminal, idle, confirmed abandon | `force_terminate_workflow` (required `reason`) |
| Still progressing, or watch timed out | `get_workflow_status` — wait or watch again |

### 7. Virtual / composition types

1. `list_workflow_types` lists **library catalog** types. Compiled virtual workflows (`virtual.<uuid>@<version>` from `composition.save` / `composition.activate`) **may** also appear when you pass `prefix="virtual."` — that browse is not the composition inventory (pagination, drafts, archived versions, and inactive lineages will not match `data.composition.list`). Empty browse still does **not** mean the org has none. Inventory: `data.composition.list` / `data.composition.get`. See `orkestia-compositions`.
2. To see what actually ran, call `list_workflows` when you already know the type name, or start `audit.workflow-run.query` (`read_only: true`) with optional `workflow_type_prefixes` (e.g. `["virtual."]`), `state_name`, `is_terminal`, `since` / `until`. Omit `organization_uuid` (context-injected). Use `audit.workflow-run.get-history` for one run’s transition log; the query list omits `state_data` on purpose.
3. App end-users may run **exposed** composition virtual workflows, not arbitrary catalog types. See `orkestia-compositions` and `orkestia-app-platform`.

### 8. Featured entry points vs internals

1. `featured: true` is the library author’s “human-runnable” hint. Page with `featured=true` to list them. Do not treat the flag as sufficient: some DAG steps (`connection.persist_connection`, description “DAG step”) are also featured.
2. Skip types whose **names or descriptions** mark them as internals: `*-validate`, `*-complete`, `*.prepare`, underscore segments (`ticket._scheduler.poll`, `agents._ft-dataset.*`), `__pre` / `__post` wrappers, and descriptions that say “DAG step” or “compensation.”
3. Start the parent (`connection.setup`, `k8s.app.deploy`, `runner.environment-build.request`), not children such as `connection.validate_credentials` or `kubernetes.namespace.ensure`. Confirm the parent with `get_workflow_dag` when `is_dag` is true.

### 9. Visual console (`open_app`)

When the user wants to see a fleet, cluster, or namespace, call `open_app` (optional `route`: `/fleet`, `/cluster/<connection_uuid>`, `/cluster/<connection_uuid>/ns/<namespace>`). Do not also start the same Kubernetes workflows in that turn. After the console opens, comment in one sentence; do not re-list what is on screen.

## Object model

| Idea | Meaning |
|---|---|
| Catalog type | A registered capability. `list_workflow_types` / `get_workflow_schema`. Count is a capability count, not “N production runs.” |
| Run | One execution. `start_workflow` returns `workflow_id` (`wf_…`). Status, history, retry, resolve, terminate, `list_workflows`, `list_stuck_workflows` all take this id (or filter runs by type). |
| `workflow_type` vs `workflow_id` | Kind versus instance. Never pass a type name to a run tool, or a `wf_…` id to a catalog tool. |
| Kinds | `state_machine` (3-state atomics are common), `dag` (layered steps), `data` (persistence / query). |
| Scopes | What the type binds to: `organization`, `none`, `library`, `subscription`, `app`, `actor`, `project`, `system`. Read live counts from `list_workflow_namespaces`. |
| `read_only` | Safe to start without side effects. |
| Identity | Bearer token → `whoami`. Org scopes every run server-side. |

**Cross-domain map.** `connection.*` is the credential root (runners, registry, network, GitHub, storage, AI models take a connection UUID). `ticket.*` is the work ledger every domain writes into. `subscription.*` gates paid surfaces. `composition.*` virtual workflows (built with `control.*` primitives, activated, then exposed with `identity.app.expose-virtual-workflow`) are the business logic app end-users may run. `identity.app.provision` is the one-call path for Sign in with Orkestia; see `orkestia-app-platform`.

## Day-to-day reads

These do not mutate provider resources. They may still create a short-lived **run** when you `start_workflow` a data type — that is expected.

- Catalog: `whoami`, `list_workflow_namespaces`, `list_workflow_types`, `get_workflow_schema`, `get_workflow_definition`, `get_workflow_dag`, `get_workflow_prerequisites`, `list_plugins`.
- Runs: `get_workflow_status`, `get_workflow_history`, `list_workflows`, `list_stuck_workflows`, `watch_workflow` (waits; does not change the run).
- Visual: `open_app`.
- Auth: `mcp_auth` (only when the server needs a token).
- Data types with `read_only: true` (examples: `connection.query`, `connection.get`, `audit.workflow-run.query`, `publisher.calendar.list`, `data.runner.list-stuck`).

Mutating run tools: `start_workflow` (except confirmed read-only types), `retry_workflow`, `resolve_workflow`, `force_terminate_workflow`.

## Gotchas

- `list_workflow_types` is the catalog; `list_workflows` is runs of **one** type. Mixing them is the most common error.
- Do not pass `organization_uuid` “to be helpful.” Context-sourced fields are injected. If a schema requires the field without a context source, pass `whoami`’s value and nothing else.
- `featured_total` is large; featured is a hint, not “the only types you may start.”
- `watch_workflow` default timeout is 300 seconds. A still-running DAG is not a failure; call `get_workflow_status` after a timeout.
- `get_workflow_history` omits `state_data` unless `include_state_data` is true. `list_stuck_workflows` / `list_workflows` do the same by default.
- `list_plugins` lists engine plugins (`aws`, `github`, `connection`, …), not workflow types. Use it when diagnosing missing provider access, not for discovery.
- Ground every claim: a registered type is a capability. To say what ran, read a run tool or `audit.workflow-run.query`.
- `retry_workflow` = terminal failed. `resolve_workflow` = `remediation_pending`. `force_terminate_workflow` = abandon a stale non-terminal run as unrecoverable.

## Sibling skills

`orkestia-connections`, `orkestia-runners`, `orkestia-github`, `orkestia-tickets`, `orkestia-compositions`, `orkestia-staff`, `orkestia-agents`, `orkestia-registry-network`, `orkestia-app-platform`, `orkestia-subscription`. This loop is how each of those domains is discovered and run; they add object-specific workflows, not a second MCP protocol.

## Additional resources

- Tool map grouped by job: [reference.md](reference.md)
- Worked start / recover / audit scenarios: [examples.md](examples.md)
