---
name: orkestia-compositions
description: Build, validate, version, and run Orkestia virtual workflows (composition.*) assembled from catalog steps and control.* primitives. Use when a user wants reusable multi-step business logic without code, or to expose logic to app end-users.
---

# Orkestia compositions

A composition is a saved multi-step DAG assembled from any catalog workflows, compiled into a runnable **virtual workflow type** owned by your org: `virtual.<uuid>@<version>`. It is how an org creates reusable business logic — and the **only** kind of workflow an app's end-users may run.

## Build → validate → run → evolve

```
composition.validate     # pre-flight: checks the definition against the live registry, no persist
composition.save         # validates, compiles, persists → {composition_uuid, lineage_uuid, workflow_type, version}
start_workflow("virtual.<uuid>@1", {...})     # run it like any workflow
composition.version      # append a new version to the lineage
composition.activate     # re-validate against current registry, set active
composition.archive / composition.delete-archived / composition.rename
composition.plan         # read-only diff of desired definitions vs saved state (GitOps-style)
composition.import       # pull definitions from a GitHub repo as drafts; activate per manifest
```

- Definition dialect: `{name, layers: [{steps: [...]}]}` — steps within a layer run in parallel; later layers reference earlier outputs.
- `save` inputs: `name` (unique per org+version), `definition`, optional `description`, `tags`, `source_session_uuid` (DGI provenance).
- Reads: `data.composition.list` (filter by name/status), `data.composition.get`.

## The glue — `control.*` (34 pure primitives)

Purpose-built so compositions stay expressive without custom code:

- **Collections**: `filter`, `map`, `sort`, `group_by`, `reduce`, `pluck`, `distinct`, `flatten`, `slice`, `match` (record matching with decimal tolerance).
- **Values**: `build`, `get` (dotted path), `set`, `merge`, `cast`, `coalesce`, `template` (`{name}` placeholders), `format` (positional `{0}`..`{7}` — composition-friendly).
- **Predicates & branching**: `predicate.compare`, `predicate.combine` (all/any/none), `switch.select` (cases table), `flow.guard` (assert or fail the branch).
- **Flow/util**: `flow.wait`, `poll.until` (poll a read-only probe until a predicate holds), `time.now`, `math.compute`, `text.split/join/replace/extract_matches`, `policy.evaluate_matrix`, `version.select_latest/lag_summary`, `http.request` (generic REST escape hatch).

## Wiring outward

- Run directly, or schedule with `schedule.*`.
- Target from a Staff event binding (`entrypoint_workflow`).
- Expose to app end-users: `identity.app.expose-virtual-workflow` (eligibility-checked); revoke with `unexpose-virtual-workflow`.

## Gotchas

- Virtual types are per-organization and resolved on demand — they **never** appear in `list_workflow_types`. An empty `prefix="virtual."` browse means "not a catalog type", never "the user has none". Audit actual runs with `audit.workflow-run.query`.
- `lineage_uuid` is the stable handle across versions; saving can supersede prior active versions (returned in `superseded_versions`).
