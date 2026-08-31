# Compositions and control primitives (by job)

Live names: `list_workflow_types(prefix="composition.")`, `prefix="control."`, `prefix="data.composition."`. Confirm fields with `get_workflow_schema`. Do not freeze counts. Omit `organization_uuid` (context-injected).

## Composition lifecycle

| Type | Job | Notes |
|---|---|---|
| `composition.validate` | Pre-flight a definition against the live registry | `read_only: true`. Required `definition`. Optional `include_dry_run`. Outputs: `passed`, `errors`, `warnings`, `repairs`; `dry_run` when requested. No persist. |
| `composition.save` | Validate, compile, persist | Required `name`, `definition`. Optional `description`, `tags`, `created_by_uuid`, `source_session_uuid` (DGI / REPLICATE). Outputs: `composition_uuid`, `lineage_uuid`, `workflow_type`, `version`, `status`, `superseded_versions`, validation fields. |
| `composition.version` | Append a version to a lineage | Required `composition_uuid` (any existing version), `definition`. Same optional provenance as save. Same output shape as save. |
| `composition.activate` | Re-validate vs current registry; set active | Required `composition_uuid`. |
| `composition.archive` | Stop a version from being startable | Required `composition_uuid`. |
| `composition.rename` | Change the human lineage name | Required `composition_uuid`, `name`. Does **not** change `virtual.<uuid>@<version>`. Outputs include `previous_name`, `updated_count`. |
| `composition.delete-archived` | Soft-delete archived rows | Optional selectors: `composition_uuid`, `composition_uuids`, `name`. `confirm` must be `delete_archived` for a real delete; not required for `dry_run`. Optional `delete_schedules`. |
| `composition.plan` | Read-only desired-vs-saved diff | `read_only: true`. Required `definitions` (`{name, definition}` list). Optional `active` (`{name: semver}`). Outputs: `plan`, `summary` (`create` / `update` / `no_op` / `promote` / `error`). |
| `composition.import` | Pull definitions from GitHub as drafts | Repo identity: `github_repository_uuid` **or** `github_connection_uuid` + `repository`. Optional `ref`. Required `manifest` `{definitions_path, definitions?, active}`. Optional `activate` (release flag). See `orkestia-github`. |

## Day-to-day composition reads

| Type | Job |
|---|---|
| `data.composition.list` | Org list. Optional `status` (`draft` \| `active` \| `archived`), `name`, `limit` (default 50). Output: `compositions`, `count`. `read_only: true`. |
| `data.composition.get` | One row by `composition_uuid`. Optional `include_compiled`. Output: `composition`. `read_only: true`. |

`composition_uuid` pickers on mutate types source `data.composition.list` (`item_path: compositions`, `value_key: composition_uuid`).

## Definition dialect

From `composition.validate` / `composition.save` field text:

- Top-level `name` plus `layers`.
- Each layer: `name` and `steps`.
- Each step: `name`, `workflow_type`, optional `input_mapping` (param → `{source: input|step|static, field|step|value}`).
- Use `input_mapping`. Legacy per-step `inputs` is only warned.
- Steps in a layer run in parallel; later layers bind earlier step outputs (`source: "step"`).

Runnable type: `virtual.<uuid>@<version>`. Inventory: `data.composition.list`. `list_workflow_types(prefix="virtual.")` may show compiled types; it is not the inventory.

## Control primitives — collections

All `read_only: true` unless noted. Typical list field is `items`; typical list output is `result`.

| Type | Job | Key inputs |
|---|---|---|
| `control.collection.filter` | Keep elements matching one comparison predicate | `items`, `op`; optional `field`, `value`. Output `result`, `count`. |
| `control.collection.map` | Unary transform (cast/case/abs/length…) on every element | `items`, `op`. Output `result`. |
| `control.collection.sort` | Sort, optional field path | `items`; optional `field`, `order`. |
| `control.collection.group_by` | Bucket into an object keyed by field path | `items`, `field`. Output `result`, `keys`. |
| `control.collection.reduce` | Aggregate count/any/all/sum/min/max | `items`, `op`. Output `value`. |
| `control.collection.pluck` | Extract one dotted field from every element | `items`, `field`; optional `default`, `skip_missing`. |
| `control.collection.distinct` | Drop duplicates, preserve order; optional by field | `items`; optional `field`. Output `result`, `count`. |
| `control.collection.flatten` | Flatten nested lists | `items`; optional `depth` (`-1` = fully flat). |
| `control.collection.slice` | Window | `items`; optional `offset` (negative = from end), `limit`. |
| `control.collection.match` | Match two record lists; no guessed collisions | `left_items`, `right_items`, `rules` (`{id?, left_field, right_field, op?, tolerance?}`; ops `eq`, `numeric_within`, `numeric_within_abs`). Optional `max_comparisons`. Outputs `matches`, `ambiguous_*`, `unmatched_*`, `summary`. |

## Control primitives — values

| Type | Job | Key inputs |
|---|---|---|
| `control.value.build` | Build one object | `fields`; optional `defaults`, `drop_null`. Output `result`. |
| `control.value.get` | Dotted/indexed path | `data`, `path`; optional `default`. Output `value`, `found`. |
| `control.value.set` | Set one key on an object | `key`; optional `base`, `value`, `drop_null`. Output `result`. |
| `control.value.merge` | Overlay wins; deep or shallow | `base`; optional `overlay`, `deep`. Output `result`. |
| `control.value.cast` | Coerce to str/int/float/bool/json/list | `value`, `to`. Output `ok`. |
| `control.value.coalesce` | First non-null in an ordered list | `candidates`. Output `value`, `found`, `index`. |
| `control.value.template` | `{name}` placeholders from a values dict | `template`; optional `values`, `strict`. Output `result`. |
| `control.value.format` | `{0}`…`{7}` from top-level `arg0`…`arg7` | `template`; optional `arg0`–`arg7`, `strict`. Composition-friendly (bind a step ref without nesting in `values`). |

## Control primitives — predicates and branching

Compare / guard operators (from those schemas): `eq`, `ne`, `in`, `not_in`, `truthy`, `falsy`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`, `regex`, `is_null`, `not_null`.

| Type | Job | Key inputs |
|---|---|---|
| `control.predicate.compare` | One operator → boolean | `op`; optional `a`, `b` (`a` may be null for is_null/not_null). Output `result`. |
| `control.predicate.combine` | Fold booleans | `clauses`; optional `mode` `all` / `any` / `none`. Output `result`. |
| `control.switch.select` | Value → branch label via cases table | `value`, `cases`; optional `default`. Outputs `matched`, `is_default`, `found`, `matched_key`. |
| `control.flow.guard` | Assert or fail the branch | `a`, `op`; optional `b`, `reason`. Output `passed`. |

## Control primitives — flow, time, text, math, policy, HTTP

| Type | Job | Key inputs | Side effects |
|---|---|---|---|
| `control.flow.wait` | Bounded delay | optional `seconds` (cap 86400) or `until_epoch` (overrides) | `read_only: true` (scheduled wait) |
| `control.poll.until` | Poll a **read-only** probe until a path equals a value | `workflow_type`, `result_path`; optional `input`, `equals` (default true), `stop_when_truthy`, `interval_seconds` (default 60, 5–3600), `deadline_seconds` (default 3600, cap 86400) | `read_only: false` |
| `control.time.now` | UTC now | optional `format` (`iso8601` / `date` / `epoch` per description), `offset_seconds` | read-only |
| `control.math.compute` | One arithmetic op | `a`, `op`; optional `b`. Ops: add/sub/mul/div/mod/pow/min/max/abs/neg/round. Output `value`. | read-only |
| `control.text.split` | String → list | `text`; optional `separator` (default whitespace), `maxsplit`. | read-only |
| `control.text.join` | List → string | `items`; optional `separator` (default empty). | read-only |
| `control.text.replace` | Literal or regex replace | `text`, `find`; optional `replace`, `regex`. | read-only |
| `control.text.extract_matches` | Regex → JSON row objects | `text`, `pattern`; optional `fields`, `ignore_case`, `multiline`, `dotall`, `max_matches`, `strip_values`, `drop_empty`, `include_match`. | read-only |
| `control.policy.evaluate_matrix` | Items vs reusable rules; summarize compliance | `items`, `rules` (`id`, `field`, `op`, optional `value`; ops match `control.predicate.compare`); optional `mode` (`all`/`any`/`none`), `identity_fields`, `name_fields`, `strict_rules`. | read-only |
| `control.version.select_latest` | Latest comparable version + lag vs current | `versions`; optional `current_version`, `version_field`, `include_prereleases`, `strict_candidates`, `strict_current`. | read-only |
| `control.version.lag_summary` | Aggregate lag evidence rows | `items`; optional `source_items`, unwrap/identity/name/version field lists, `behind_field`, `ahead_count_field`. | read-only |
| `control.http.request` | Generic REST escape hatch | `method` (GET/POST/PUT/PATCH/DELETE), `url`; optional `headers`, `body`, `timeout_seconds` (default 30, cap 300), `fail_on_http_error`. | **`read_only: false`** |

Prefer a first-class catalog workflow over `control.http.request`.

## Wiring outward (not `composition.*`)

| Type | Job |
|---|---|
| `schedule.create` | Recurring start. Required `target_workflow_type` (e.g. `virtual.<uuid>@2`), `interval_minutes`. Optional `name`, `initial_data`, `active` (default true). Discover the rest with `prefix="schedule."`. |
| `staff.event-binding.create` | Optional `entrypoint_workflow` (dict). See `orkestia-staff`. |
| `identity.app.expose-virtual-workflow` | Required `identity_app_uuid`, `composition_uuid`, `version`. Omit `actor` / `organization_uuid`. Eligibility-checked. See `orkestia-app-platform`. |
| `identity.app.unexpose-virtual-workflow` | Same ids; `version` optional. |
| `audit.workflow-run.query` | Org run list. Optional `workflow_type_prefixes` (e.g. `["virtual."]`) or exact `workflow_type`. `read_only: true`. List omits `state_data`; use `audit.workflow-run.get-history` for one run. |
