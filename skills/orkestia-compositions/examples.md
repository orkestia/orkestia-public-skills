# Worked composition examples

Placeholder UUIDs and names are examples. Copy workflow type names and `input_mapping` keys; substitute live values. Omit `organization_uuid`. Confirm every child type with `get_workflow_schema` before `composition.save`.

`input_mapping` (from `composition.validate`): param → `{source: input|step|static, field|step|value}`.

---

## 1. Two-layer DAG: parallel stamp + greeting, then format

Layer 1 runs `control.time.now` and `control.value.build` in parallel. Layer 2 binds both outputs into `control.value.format` (`{0}` / `{1}` — composition-friendly; no nested `values` dict).

```json
{
  "name": "hello-stamp",
  "layers": [
    {
      "name": "gather",
      "steps": [
        {
          "name": "now",
          "workflow_type": "control.time.now",
          "input_mapping": {
            "format": { "source": "static", "value": "iso8601" }
          }
        },
        {
          "name": "who",
          "workflow_type": "control.value.build",
          "input_mapping": {
            "fields": { "source": "input", "field": "who" }
          }
        }
      ]
    },
    {
      "name": "render",
      "steps": [
        {
          "name": "line",
          "workflow_type": "control.value.format",
          "input_mapping": {
            "template": { "source": "static", "value": "Hello {0} at {1}" },
            "arg0": { "source": "step", "step": "who", "field": "result" },
            "arg1": { "source": "step", "step": "now", "field": "iso8601" }
          }
        }
      ]
    }
  ]
}
```

**Validate (no persist), then save:**

```
get_workflow_schema(workflow_type="composition.validate")
start_workflow(
  workflow_type="composition.validate",
  initial_data={"definition": <json above>, "include_dry_run": true},
  triggered_by="mcp:agent"
)
```

When `passed` is true:

```
start_workflow(
  workflow_type="composition.save",
  initial_data={
    "name": "hello-stamp",
    "definition": <json above>,
    "description": "Greeting plus UTC stamp",
    "tags": ["example", "glue"],
    "source_session_uuid": "<optional-dgi-session-uuid>"
  },
  triggered_by="mcp:agent"
)
```

Save returns `composition_uuid`, `lineage_uuid`, `workflow_type` (e.g. `virtual.aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee@1`), `version`, `status`, `superseded_versions`.

**Run** (inputs are whatever `source: "input"` mapped — here `who` should be an object `control.value.build` accepts as `fields`, e.g. `{"name": "Ada"}`):

```
start_workflow(
  workflow_type="virtual.<composition_uuid>@1",
  initial_data={"who": {"name": "Ada"}},
  triggered_by="mcp:agent"
)
watch_workflow(workflow_id)
```

`list_workflow_types(prefix="virtual.")` may list compiled types; it is not inventory. Use `data.composition.list` / `get`. Audit:

```
list_workflows(workflow_type="virtual.<composition_uuid>@1")
start_workflow(
  workflow_type="audit.workflow-run.query",
  initial_data={"workflow_type": "virtual.<composition_uuid>@1"}
)
```

---

## 2. Filter then pluck

Keep rows whose `status` equals `open`, then extract `id`.

```json
{
  "name": "open-ids",
  "layers": [
    {
      "name": "filter",
      "steps": [
        {
          "name": "open_rows",
          "workflow_type": "control.collection.filter",
          "input_mapping": {
            "items": { "source": "input", "field": "items" },
            "op": { "source": "static", "value": "eq" },
            "field": { "source": "static", "value": "status" },
            "value": { "source": "static", "value": "open" }
          }
        }
      ]
    },
    {
      "name": "pluck",
      "steps": [
        {
          "name": "ids",
          "workflow_type": "control.collection.pluck",
          "input_mapping": {
            "items": { "source": "step", "step": "open_rows", "field": "result" },
            "field": { "source": "static", "value": "id" }
          }
        }
      ]
    }
  ]
}
```

`control.collection.filter` `op` had an empty schema description — if validate returns `repairs` / `errors`, re-read `get_workflow_schema("control.collection.filter")` and adjust. `eq` is listed on `control.predicate.compare` / `control.flow.guard`; treat a validate failure as authoritative.

Run with `items` like `[{"id": "a", "status": "open"}, {"id": "b", "status": "closed"}]`.

---

## 3. Predicate, switch, then guard

One `input_mapping` param binds **one** source. `control.predicate.combine` wants a **list** of booleans (`clauses`) — do not point `clauses` at a single compare `result`. Fold a known list with static (or a prior list-producing step), then label and guard.

```json
{
  "name": "ready-gate",
  "layers": [
    {
      "name": "fold",
      "steps": [
        {
          "name": "both",
          "workflow_type": "control.predicate.combine",
          "input_mapping": {
            "clauses": { "source": "input", "field": "flags" },
            "mode": { "source": "static", "value": "all" }
          }
        }
      ]
    },
    {
      "name": "label",
      "steps": [
        {
          "name": "branch",
          "workflow_type": "control.switch.select",
          "input_mapping": {
            "value": { "source": "step", "step": "both", "field": "result" },
            "cases": { "source": "static", "value": { "true": "go", "false": "hold" } },
            "default": { "source": "static", "value": "hold" }
          }
        }
      ]
    },
    {
      "name": "assert",
      "steps": [
        {
          "name": "must_go",
          "workflow_type": "control.flow.guard",
          "input_mapping": {
            "a": { "source": "step", "step": "branch", "field": "matched" },
            "op": { "source": "static", "value": "eq" },
            "b": { "source": "static", "value": "go" },
            "reason": { "source": "static", "value": "not ready" }
          }
        }
      ]
    }
  ]
}
```

Run `initial_data`: `{"flags": [true, true]}`. `mode` is `all` / `any` / `none`. Compare operators on `control.flow.guard` / `control.predicate.compare`: `eq`, `ne`, `in`, `not_in`, `truthy`, `falsy`, `gt`, `gte`, `lt`, `lte`, `contains`, `not_contains`, `regex`, `is_null`, `not_null`.

Simpler two-step variant (guard on a single compare, no combine):

```json
{
  "name": "must-be-paid",
  "layers": [
    {
      "name": "test",
      "steps": [
        {
          "name": "paid",
          "workflow_type": "control.predicate.compare",
          "input_mapping": {
            "a": { "source": "input", "field": "paid" },
            "op": { "source": "static", "value": "truthy" }
          }
        }
      ]
    },
    {
      "name": "assert",
      "steps": [
        {
          "name": "gate",
          "workflow_type": "control.flow.guard",
          "input_mapping": {
            "a": { "source": "step", "step": "paid", "field": "result" },
            "op": { "source": "static", "value": "eq" },
            "b": { "source": "static", "value": true },
            "reason": { "source": "static", "value": "unpaid" }
          }
        }
      ]
    }
  ]
}
```

---

## 4. Merge overlay + named template

Build a base object and an overlay in parallel; merge (overlay wins); interpolate `{name}` via `control.value.template`.

```json
{
  "name": "merge-then-template",
  "layers": [
    {
      "name": "parts",
      "steps": [
        {
          "name": "base",
          "workflow_type": "control.value.build",
          "input_mapping": {
            "fields": { "source": "input", "field": "base_fields" }
          }
        },
        {
          "name": "overlay",
          "workflow_type": "control.value.build",
          "input_mapping": {
            "fields": { "source": "input", "field": "overlay_fields" }
          }
        }
      ]
    },
    {
      "name": "merge",
      "steps": [
        {
          "name": "combined",
          "workflow_type": "control.value.merge",
          "input_mapping": {
            "base": { "source": "step", "step": "base", "field": "result" },
            "overlay": { "source": "step", "step": "overlay", "field": "result" },
            "deep": { "source": "static", "value": true }
          }
        }
      ]
    },
    {
      "name": "text",
      "steps": [
        {
          "name": "message",
          "workflow_type": "control.value.template",
          "input_mapping": {
            "template": { "source": "static", "value": "Ship to {city} for {name}" },
            "values": { "source": "step", "step": "combined", "field": "result" }
          }
        }
      ]
    }
  ]
}
```

Run `initial_data`: `base_fields` / `overlay_fields` objects whose keys include `city` and `name` after merge.

---

## 5. Poll until a read-only probe is true, then HTTP hatch (optional)

`control.poll.until` is `read_only: false`. The probe `workflow_type` **must** be a read-only type you confirmed with `get_workflow_schema`. Do not invent a probe name.

```json
{
  "name": "wait-then-ping",
  "layers": [
    {
      "name": "wait",
      "steps": [
        {
          "name": "until_ready",
          "workflow_type": "control.poll.until",
          "input_mapping": {
            "workflow_type": { "source": "static", "value": "<read-only-probe-type>" },
            "input": { "source": "input", "field": "probe_input" },
            "result_path": { "source": "static", "value": "green" },
            "equals": { "source": "static", "value": true },
            "interval_seconds": { "source": "static", "value": 60 },
            "deadline_seconds": { "source": "static", "value": 3600 }
          }
        }
      ]
    },
    {
      "name": "notify",
      "steps": [
        {
          "name": "ping",
          "workflow_type": "control.http.request",
          "input_mapping": {
            "method": { "source": "static", "value": "POST" },
            "url": { "source": "input", "field": "webhook_url" },
            "body": { "source": "step", "step": "until_ready", "field": "observed" },
            "fail_on_http_error": { "source": "static", "value": true }
          }
        }
      ]
    }
  ]
}
```

Replace `<read-only-probe-type>` only after `get_workflow_schema` shows `read_only: true`. Prefer a first-class catalog workflow over `control.http.request`. `body` is a string on the HTTP schema — if validate rejects a json binding, `control.value.cast` `to: "str"` (or `control.value.template`) in an intermediate layer.

---

## 6. Evolve, GitOps, expose

**Version + activate** (after example 1 is saved):

```
start_workflow(
  workflow_type="composition.version",
  initial_data={
    "composition_uuid": "<uuid-from-save>",
    "definition": <updated definition>,
    "source_session_uuid": "<optional-dgi-session>"
  }
)
start_workflow(
  workflow_type="composition.activate",
  initial_data={"composition_uuid": "<new-version-uuid>"}
)
```

New runnable name is `virtual.<uuid>@<new-version>` from the version output. `lineage_uuid` is unchanged.

**Plan (read-only) then import drafts:**

```
start_workflow(
  workflow_type="composition.plan",
  initial_data={
    "definitions": [{"name": "hello-stamp", "definition": <json>}],
    "active": {"hello-stamp": "1.0.0"}
  }
)
```

When `summary` looks right and GitHub is wired (`orkestia-github`):

```
start_workflow(
  workflow_type="composition.import",
  initial_data={
    "github_connection_uuid": "<connection-uuid>",
    "repository": "owner/name",
    "ref": "main",
    "manifest": {
      "definitions_path": "compositions/",
      "active": {"hello-stamp": "1.0.0"}
    },
    "activate": false
  }
)
```

Set `activate: true` only when you intend to release `manifest.active`. Inventory: `data.composition.list` with `status: "draft"` then `composition.activate` per row.

**Schedule the virtual type:**

```
start_workflow(
  workflow_type="schedule.create",
  initial_data={
    "target_workflow_type": "virtual.<uuid>@1",
    "interval_minutes": 60,
    "name": "hello-hourly",
    "initial_data": {"who": {"name": "scheduler"}},
    "active": true
  }
)
```

**Expose to app end-users** (composition side; app + PKCE in `orkestia-app-platform`):

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

Read `exposed`, `ineligible_steps`. Revoke with `identity.app.unexpose-virtual-workflow`. End-users may start **only** exposed virtual workflows.

**Staff:** set `entrypoint_workflow` on `staff.event-binding.create` to the virtual type — see `orkestia-staff`.
