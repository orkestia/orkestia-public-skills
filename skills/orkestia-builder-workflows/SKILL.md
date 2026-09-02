---
name: orkestia-builder-workflows
description: >-
  Authors Orkestia virtual workflows in TypeScript (defineComposition, t, cond,
  layers, fanOut, loop, compensation), transpiles them to composition authoring
  JSON, saves/activates/exposes them with the orkestia CLI, and consumes them
  from React via the exposure lock and useWorkflow. Use when editing *.vw.ts,
  composition push/expose, app.lock.json, or wiring a browser to virtual.* types.
  Pair with orkestia-compositions for MCP JSON; this skill is the code path.
---

# Builder workflows (TypeScript compositions)

`@orkestia/workflows` describes a virtual workflow in TypeScript. The CLI emits **composition authoring JSON** (the shape `composition.save` accepts). The **server** validates types, compiles the DAG, stamps the content hash, versions, activates, and executes.

You do **not** emit compiled DAG JSON from TypeScript. Re-implementing the compiler drifts on `content_hash` and the `step` → `state_data` rename.

Browser callers use the **exposure lock**, never atomic platform types. MCP inventory of compositions remains `data.composition.list` (`orkestia-compositions`).

## When to load

Load when the user authors `app/workflows/*.vw.ts`, runs `orkestia composition push` / `expose`, binds `.orkestia/app.lock.json`, or asks why `useWorkflow` failed with `NOT_EXPOSED_TO_END_USERS`.

Load `orkestia-compositions` when they want MCP `composition.validate` / `save` without an app repo. Load `orkestia-builder` for AppShell, tokens, and CLI lifecycle.

## Use cases

1. **Author a domain command** with symbolic wiring and `cond`, not JavaScript `if`.
2. **Offline transpile** (`push` without `--save`) then **save + activate**.
3. **Expose** end-user compositions and bind React to the lock.
4. **Protect** operator-only compositions (`enduser: false`) and queue work for Staff.
5. **Depend on another local composition** by source name, not a frozen `virtual.<uuid>@<version>`.

## How to

### 1. Author (`*.vw.ts`)

Composition code runs at **authoring time**. `c.input.x` and step handles are **symbolic refs**. Concatenation, arithmetic, and `if (handle.ready)` do not work — the DSL throws `SymbolicValueError`. Put transforms in a registered atomic workflow.

```ts
import { cond, defineComposition, t } from "@orkestia/workflows";

export default defineComposition(
  {
    name: "order-approve",
    description: "Approve an order and append an audit event.",
    inputs: {
      workspace_uuid: t.uuid(),
      order_uuid: t.uuid(),
      decision: t.string(),
      decided_at: t.string(),
      idempotency_key: t.string(),
    },
    metadata: { enduser: true },
  },
  (c) => {
    const order = c.step("data.appdata.record.read", {
      database_slug: "orders",
      table_slug: "order",
      app_organization_uuid: c.input.workspace_uuid,
      record_uuid: c.input.order_uuid,
    });

    const approved = cond.allOf(
      cond.truthy(order.found),
      cond.eq(c.input.decision, "approved"),
    );

    const updated = c.step("data.appdata.record.update", {
      database_slug: "orders",
      table_slug: "order",
      app_organization_uuid: c.input.workspace_uuid,
      record_uuid: c.input.order_uuid,
      patch: { state: "approved", decided_at: c.input.decided_at },
    }).when(approved);

    const event = c.step("data.appdata.record.write", {
      database_slug: "orders",
      table_slug: "order_event",
      app_organization_uuid: c.input.workspace_uuid,
      payload: {
        order_uuid: c.input.order_uuid,
        event_kind: "approved",
        occurred_at: c.input.decided_at,
      },
      idempotency_key: c.input.idempotency_key,
    }).when(approved);

    c.output({
      order_uuid: updated.record_uuid,
      event_uuid: event.record_uuid,
    });
  },
);
```

Mark browser-eligible compositions with `metadata: { enduser: true }`. Protected:

```ts
metadata: { enduser: false, operator_only: true }
```

Metadata is not authorization. Identity must still **expose** the active type; the server still enforces principal, workspace, and capabilities.

Confirm every child `workflow_type` exists (`get_workflow_schema` / MCP, or a typed SDK binding). The scaffold `demo.echo.run` is not guaranteed in any org.

### 2. Layers, parallelism, fan-out, loops

Independent steps share a layer (parallel). A consumer of a prior output is leveled later. Ties keep authoring order.

```ts
c.layer("load-policy", () => {
  role = c.step("control.value.get", { data: user.record, path: "role" });
  state = c.step("control.value.get", { data: item.record, path: "state" });
});
```

- `c.parallel(...)` — explicit parallel authoring
- `fanOut(source.items, item => ...)` — map a collection
- `loop({ maxIterations, breakWhen }, ...)` — **bounded** server iteration
- `c.layer(...).compensateWith(...)` — saga compensation
- `.unrecoverable()` — cannot compensate

Keep loops bounded. The server owns execution and recovery, not process memory.

`cond` shapes: equality/ordering, truthy/falsy, membership, negation, `allOf`, `anyOf`. Referenced values must be available from an earlier layer when the compiler requires it.

Inputs via `t.string()`, `t.integer().optional()`, `t.boolean()`, `t.uuid()`, `t.list(t.string())`, `t.dict()`. `c.output(...)` is presence-driven: a skipped conditional step may omit fields.

### 3. Offline push, then save

```bash
orkestia composition push
```

Writes `.orkestia/*.composition.json`. No network. Does **not** prove types exist.

```bash
export ORKESTIA_MEMBER_TOKEN=...
export ORKESTIA_ORGANIZATION_UUID=...
orkestia composition push --save
```

Waits for save + activation. Server errors name unknown types and bad mappings.

Hashes and resolved types land in `.orkestia/composition.push-state.json`. An exact repeat for the same API + token fingerprint can skip; `--force` re-round-trips. That cache is **not** execution idempotency.

### 4. Expose and lock

```bash
orkestia composition push --save --expose
# or
orkestia composition expose
orkestia composition expose --yes
```

`.orkestia/app.lock.json` maps **logical source name** → executable virtual type. Browser code reads the lock. Direct atomics from the browser fail closed.

### 5. Consume in React

```ts
import appLock from "../.orkestia/app.lock.json";
const type = appLock.exposedWorkflows["order-approve"]?.workflowType;
```

```tsx
const run = useWorkflow(type);
void run.start({ workspace_uuid, order_uuid, decision, decided_at, idempotency_key });
```

Fill only `source: "input"` fields. Inner steps (`source: "step"` / `static`) are orchestration, not form fields — a 12-step composition often has three inputs.

### 6. Local composition dependencies

Do not commit org-specific `virtual.<uuid>@<version>` into reusable source. Map leftovers in config:

```ts
export default {
  name: "my-app",
  compositionDependencies: {
    "virtual.old-dependency@1": "local-dependency-name",
  },
};
```

Live push orders local deps and rewrites to the active type from the same run.

When Staff tools point at local compositions, **`composition push --save` first**. Live Staff commands resolve through push-state and fail closed if the type is missing or inactive.

### 7. Idempotent commands

A robust command: read current state → validate expected state/capability on the server → transition → append an immutable event with a **deterministic idempotency key** → return stable ids.

## Gotchas

- **No expression language** in composition JSON. Transforms are atomic workflows (`control.value.*` or domain types).
- **`enduser: true` ≠ exposed.** Run `--expose` / `identity.app.expose-virtual-workflow`.
- **Optional outputs** may be absent when `.when(...)` skips a step.
- **Do not call** `composition.save` from the browser. That is a member-plane CLI/MCP job.
- Typed SDK imports (Node workflow SDK) are optional; string types like `"data.appdata.record.query"` always work if the catalog has them.

## Additional resources

- Combinator map: [reference.md](reference.md)
- Worked files: [examples.md](examples.md)
- Hub: [orkestia-builder](../orkestia-builder/SKILL.md)
- MCP JSON path: [orkestia-compositions](../orkestia-compositions/SKILL.md)
