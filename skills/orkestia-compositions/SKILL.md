---
name: orkestia-compositions
description: >-
  Builds, validates, versions, and runs Orkestia virtual workflows (composition.*)
  assembled from catalog steps and control.* primitives. Use when the user wants
  reusable multi-step business logic without writing code, to evolve or import a
  composition lineage, to glue catalog steps with control.* (filter, map, template,
  merge, predicates, switch, guard, poll, HTTP), or to expose a composition so app
  end-users can run it — the only kind of workflow those end-users may start.
---

# Orkestia compositions

A composition is a saved multi-step DAG. `composition.save` compiles it into an org-owned **virtual workflow type** `virtual.<uuid>@<version>`. That type is how an org ships reusable business logic without code, and it is the **only** kind of workflow an app’s end-users may run.

Call `whoami` first. Omit `organization_uuid` (and `actor` on identity.app types) — they are context-injected. Discover live names with `list_workflow_types` `prefix="composition."`, `prefix="control."`, `prefix="data.composition."`. Read `get_workflow_schema` before any mutating start.

## When to load

Load this skill when the user wants to design, validate, save, version, activate, archive, rename, or import a composition; when they ask to run `virtual.<uuid>@<version>`; when they need glue without code (`control.*`); when they want GitOps-style plan/import from GitHub; or when they want to schedule a composition, bind it as a Staff `entrypoint_workflow`, or expose it to app end-users. If they are authoring `*.vw.ts` or running `orkestia composition push`, load `orkestia-builder-workflows` instead (same platform, TypeScript/CLI path).

## Use cases

1. **Design a 2-layer composition.** Parallel steps in layer 1; layer 2 wires earlier outputs. Pre-flight with `composition.validate` (no persist), then `composition.save`. Outcome: `{composition_uuid, lineage_uuid, workflow_type, version}`.
2. **Run it.** `start_workflow("virtual.<uuid>@<version>", {…})`. Outcome: a `workflow_id` and terminal `state_data`. Virtual types are not a catalog inventory — see Gotchas.
3. **Evolve a lineage.** Append with `composition.version`, re-validate with `composition.activate`, archive / rename. `lineage_uuid` is the stable handle; save/version may supersede prior active versions.
4. **GitOps.** Read-only `composition.plan` (diff desired vs saved), then `composition.import` from a GitHub repo as drafts; activate per manifest.
5. **Glue without code.** `control.collection.filter` / `map`, `control.value.template` / `merge` / `format`, `control.predicate.combine`, `control.switch.select`, `control.flow.guard`, `control.poll.until`, `control.http.request` (escape hatch). Full primitive map in [reference.md](reference.md).
6. **Wire outward.** Recurring `schedule.*`; Staff event binding `entrypoint_workflow` (`orkestia-staff`); expose to end-users with `identity.app.expose-virtual-workflow` (`orkestia-app-platform`).

## How to

### 1. Design, validate, save (2-layer DAG)

Dialect (`composition.validate` schema): `{name, layers: [{name, steps: [...]}]}`. Steps in a layer run in parallel. Each step has `name`, `workflow_type`, and optional `input_mapping`: param → `{source: input|step|static, field|step|value}`. Use `input_mapping` for wiring. Legacy per-step `inputs` is only warned.

```
whoami()
list_workflow_types(prefix="composition.")
get_workflow_schema(workflow_type="composition.validate")
get_workflow_schema(workflow_type="composition.save")
```

1. Draft the definition. Layer 1: independent steps. Layer 2: `source: "step"` bindings to earlier step **names** and output **fields**.
2. Pre-flight (read-only, no persist):

```
start_workflow(
  workflow_type="composition.validate",
  initial_data={
    "definition": { ... },
    "include_dry_run": true
  }
)
```

3. Read `passed`, `errors`, `warnings`, `repairs`. Optional `dry_run` is `{passed, errors, evaluated}` when `include_dry_run` is true. Fix until `passed` is true.
4. Persist:

```
start_workflow(
  workflow_type="composition.save",
  initial_data={
    "name": "order-summary",
    "definition": { ... },
    "description": "optional",
    "tags": ["optional", "list"],
    "source_session_uuid": "<dgi-session-uuid>"
  }
)
```

`name` is unique per org+version. `description`, `tags`, and `source_session_uuid` (DGI / REPLICATE provenance) are optional. Omit `created_by_uuid` unless you have a reason to set it.

5. Capture outputs: `composition_uuid`, `lineage_uuid` (stable across versions), `workflow_type` (the `virtual.<uuid>@<version>` string), `version`, `status`, `superseded_versions` (prior active versions archived by this write), `validation_passed`.

A worked 2-layer definition is in [examples.md](examples.md). Confirm each child `workflow_type` with `get_workflow_schema` before save.

### 2. Run a virtual type

```
start_workflow(
  workflow_type="virtual.<composition_uuid>@<version>",
  initial_data={ ...inputs the definition maps from source: input... }
)
watch_workflow(workflow_id)
```

Fill only fields the definition’s `source: "input"` mappings expect. Confirm with `get_workflow_schema` / `get_workflow_dag` on that virtual type name once you have it from save/list/get.

**Catalog browse is not the inventory.** Compiled types **may** appear under `list_workflow_types(prefix="virtual.")`; that page is still not `data.composition.list` (drafts, archived versions, and inactive lineages can be missing). An empty browse does **not** mean the org has none. Inventory: `data.composition.list` / `get` below. Audit runs:

```
list_workflows(workflow_type="virtual.<uuid>@<version>")
start_workflow(
  workflow_type="audit.workflow-run.query",
  initial_data={"workflow_type_prefixes": ["virtual."]}
)
```

Pair with `audit.workflow-run.get-history` for one run’s transition log (the query list omits `state_data` on purpose).

### 3. Evolve: version, activate, archive, rename

`lineage_uuid` is the stable handle. `composition_uuid` is one version row. `composition.version` takes any existing version of the lineage.

```
get_workflow_schema(workflow_type="composition.version")
start_workflow(
  workflow_type="composition.version",
  initial_data={
    "composition_uuid": "<existing-version-uuid>",
    "definition": { ...new definition... },
    "description": "optional",
    "tags": ["optional"],
    "source_session_uuid": "<optional-dgi-session>"
  }
)
```

Same optional provenance fields as save. Outputs match save, including a new `workflow_type` / `version` and `superseded_versions`.

**Activate** re-validates against the **current** registry and sets the row active:

```
start_workflow(
  workflow_type="composition.activate",
  initial_data={"composition_uuid": "<uuid>"}
)
```

Read `validation_passed` / `validation_errors`. Activation can fail if a child type disappeared from the catalog.

**Archive** (no longer startable): `composition.archive` with `composition_uuid`. **Rename** the lineage (does not change runnable `virtual.<uuid>@<version>` strings): `composition.rename` with `composition_uuid` + new `name`. **Soft-delete archived rows:** `composition.delete-archived`. For a real delete, `confirm` must be the string `delete_archived` (not required for `dry_run: true`). Optional selectors: one `composition_uuid`, `composition_uuids`, or lineage `name`; omit selectors for broad org cleanup. `delete_schedules: true` also drops schedules targeting those virtual types.

### 4. GitOps: plan then import

`composition.plan` is `read_only: true`. `definitions` is a list of `{name, definition}`. Optional `active` is `{name: semver}` from a manifest.

```
get_workflow_schema(workflow_type="composition.plan")
start_workflow(
  workflow_type="composition.plan",
  initial_data={
    "definitions": [{"name": "order-summary", "definition": { ... }}],
    "active": {"order-summary": "1.0.0"}
  }
)
```

Read `plan` (per row: `action`, `current_version`, `current_status`, `next_version`, `validation_passed`, `errors`, `warnings`) and `summary` keyed by `create` / `update` / `no_op` / `promote` / `error`.

Then import from GitHub (drafts; activate per manifest). Identity: `github_repository_uuid` **or** `github_connection_uuid` + `repository` (`owner/name`). Optional `ref` (branch/tag/SHA; default = repo default). Wire GitHub first — `orkestia-github`.

```
get_workflow_schema(workflow_type="composition.import")
start_workflow(
  workflow_type="composition.import",
  initial_data={
    "github_connection_uuid": "<uuid>",
    "repository": "owner/name",
    "ref": "main",
    "manifest": {
      "definitions_path": "compositions/",
      "active": {"order-summary": "1.0.0"}
    },
    "activate": false
  }
)
```

`manifest` shape: `{definitions_path, definitions?, active: {name: semver}}`. `activate: true` activates versions named in `manifest.active` (the release flag). Default is drafts. Outputs: `imported`, `activated`, `repo`, `summary`.

### 5. Glue with `control.*` (no custom code)

Discover: `list_workflow_types(prefix="control.")`. Almost all are `read_only: true` state machines. Confirm fields with `get_workflow_schema` before binding them in a definition. Tiny patterns (full map in [reference.md](reference.md)):

**Filter a list, then pluck one field** (two layers):

```
layer 1: control.collection.filter  items ← input, op/value/field static or input
layer 2: control.collection.pluck   items ← step filter.result, field static
```

**Named placeholders vs composition-friendly format:** `control.value.template` interpolates `{name}` from a `values` dict. `control.value.format` interpolates `{0}`…`{7}` from top-level `arg0`…`arg7` so a composition can bind a step ref without nesting inside `values`.

**Merge two objects, overlay wins:** `control.value.merge` (`base`, optional `overlay`, optional `deep`). Typical layer 2 after two parallel builders.

**Booleans then a branch label:** `control.predicate.compare` (`a`, `op`, `b`) → `control.predicate.combine` (`clauses`, `mode` `all`/`any`/`none`) → `control.switch.select` (`value`, `cases`, optional `default`).

**Fail the branch instead of branching:** `control.flow.guard` (`a`, `op`, optional `b`, optional `reason`). Same operator set as compare (`eq`, `ne`, `in`, `not_in`, `truthy`, `falsy`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`, `regex`, `is_null`, `not_null`).

**Wait on a read-only probe:** `control.poll.until` — `workflow_type` (probe), `result_path`, optional `equals` (default true), `stop_when_truthy`, `interval_seconds`, `deadline_seconds`. Probe must be read-only; confirm on its schema.

**No first-class workflow:** `control.http.request` (`method`, `url`, optional `headers`/`body`/`timeout_seconds`/`fail_on_http_error`). `read_only: false` — last-resort escape hatch.

### 6. Wire outward (schedule, Staff, app end-users)

**Schedule.** Discover `list_workflow_types(prefix="schedule.")`. Recurring start:

```
get_workflow_schema(workflow_type="schedule.create")
start_workflow(
  workflow_type="schedule.create",
  initial_data={
    "target_workflow_type": "virtual.<uuid>@<version>",
    "interval_minutes": 15,
    "name": "optional-label",
    "initial_data": { ... },
    "active": true
  }
)
```

Also: `schedule.list` / `get`, `pause` / `resume`, `update`, `delete`.

**Staff event binding.** Point `entrypoint_workflow` at the virtual type when creating/updating a binding (`staff.event-binding.create`). Full binding fields and actor wiring: `orkestia-staff`.

**Expose to app end-users** (composition side). This is the **only** kind of workflow those users may run. App provisioning, PKCE, seats, and the `/api/workflows` call live in `orkestia-app-platform`. Schema (present in this catalog):

```
get_workflow_schema(workflow_type="identity.app.expose-virtual-workflow")
start_workflow(
  workflow_type="identity.app.expose-virtual-workflow",
  initial_data={
    "identity_app_uuid": "<app-uuid>",
    "composition_uuid": "<uuid>",
    "version": 1
  }
)
```

Eligibility-checked. Outputs include `exposed`, `step_count`, `ineligible_steps`. Revoke with `identity.app.unexpose-virtual-workflow` (same ids; `version` optional). `identity.app.reconcile-catalog` backfills the capability catalog — see the app-platform skill.

## Object model

| Object | Meaning |
|---|---|
| Definition | Serializer dialect `{name, layers:[{name, steps:[…]}]}`. Steps in a layer are parallel; later layers bind earlier outputs via `input_mapping`. |
| `input_mapping` | Per-param `{source: input\|step\|static, field\|step\|value}`. `input` + `field`; `step` + `step` (step name) + `field` (output field); `static` + `value`. |
| Composition row | One saved version. Identified by `composition_uuid`. Status: `draft` / `active` / `archived` (`data.composition.list` filter). |
| `lineage_uuid` | Stable handle across every version. Rename changes the human `name`, not this id and not the virtual type string. |
| Virtual type | Runnable name `virtual.<uuid>@<version>` returned as `workflow_type` from save/version/activate. Org-owned compiled DAG. |
| `superseded_versions` | Prior **active** lineage versions archived by save/version. |
| `source_session_uuid` | Optional DGI / REPLICATE provenance on save and version. |

## Day-to-day reads

`read_only: true` — start freely. Omit `organization_uuid`.

```
start_workflow(workflow_type="data.composition.list", initial_data={})
start_workflow(workflow_type="data.composition.list", initial_data={"status": "active", "name": "order-summary", "limit": 50})
start_workflow(workflow_type="data.composition.get", initial_data={"composition_uuid": "<uuid>", "include_compiled": false})
```

- `data.composition.list` — optional `status` (`draft` \| `active` \| `archived`), `name` (lineage name), `limit` (default 50). Output: `compositions`, `count`.
- `data.composition.get` — required `composition_uuid`; optional `include_compiled`. Output: `composition`.

Also read-only: `composition.validate`, `composition.plan`. Catalog inspect: `get_workflow_schema` / `get_workflow_dag` on a known `virtual.<uuid>@<version>`. Run inspect: `get_workflow_status`, `get_workflow_history`, `list_workflows`, `audit.workflow-run.query`.

## Gotchas

- **Virtual types are not the catalog inventory.** `prefix="virtual."` may list compiled org types; do not use it (or an empty result) to decide whether the org has compositions. Use `data.composition.list`. Start a known type as `virtual.<uuid>@<version>`. Audit with run tools / `audit.workflow-run.query`.
- `lineage_uuid` is stable; `composition_uuid` is one version. Save/version can archive prior active versions (`superseded_versions`).
- `organization_uuid` is required in schemas but context-injected — omit it. Same for `actor` on `identity.app.expose-virtual-workflow`.
- Activate re-checks the **live** registry. A composition that saved last month can fail activate if a child type is gone.
- `composition.delete-archived` needs `confirm="delete_archived"` for a real delete. Prefer `dry_run: true` first. Optional `delete_schedules`.
- `control.http.request` and `control.poll.until` are not read-only. Prefer catalog provider workflows over the HTTP hatch.
- App end-users may run **exposed compositions only**, not arbitrary catalog types.
- `name` on save is unique per org+version. Rename does not rewrite existing `virtual.<uuid>@<version>` strings.

## Sibling skills

- `orkestia-mcp-operating-loop` — whoami, schema, start/watch, recovery.
- `orkestia-app-platform` — identity app, PKCE, seats, expose/unexpose, end-user agent. This skill covers the composition side of expose only.
- `orkestia-staff` — `staff.event-binding.create` `entrypoint_workflow`.
- `orkestia-github` — connection + repo identity required by `composition.import`.

## Additional resources

- Control primitives and composition lifecycle map: [reference.md](reference.md)
- Worked definitions and run/expose traces: [examples.md](examples.md)
