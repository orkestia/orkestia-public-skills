# TypeScript composition examples

Confirm child types with `get_workflow_schema` (MCP) or the live catalog before `--save`. Omit `organization_uuid` from inputs — the server injects org scope.

---

## 1. Workspace-scoped query wrapper (expose this, not the atomic)

```ts
import { defineComposition, t } from "@orkestia/workflows";

export default defineComposition(
  {
    name: "note-query",
    description: "List notes in the active workspace.",
    inputs: {
      workspace_uuid: t.uuid(),
      limit: t.integer().optional(),
    },
    metadata: { enduser: true },
  },
  (c) => {
    const result = c.step("data.appdata.record.query", {
      database_slug: "notes",
      table_slug: "note",
      app_organization_uuid: c.input.workspace_uuid,
      limit: c.input.limit,
    });
    c.output({ records: result.records, count: result.count });
  },
);
```

```bash
orkestia composition push
orkestia composition push --save --expose
```

Slugs are **fixed in source**. Callers cannot pick an arbitrary table.

---

## 2. Invalid author-time JavaScript (will throw)

```ts
const first = c.step("provider.lookup", { key: c.input.key });
// SymbolicValueError — no expression node in composition JSON
const invalid = first.value + "/suffix";
```

**Valid:** a later atomic that accepts `value` + `suffix`, or `control.value.template` / `format` with mapped args.

**Valid wiring:**

```ts
const first = c.step("provider.lookup", { key: c.input.key });
c.step("provider.consume", { value: first.value });
```

---

## 3. Conditional update + idempotent event

See `order-approve` in [SKILL.md](SKILL.md). After `--save --expose`, React:

```tsx
const run = useWorkflow(appLock.exposedWorkflows["order-approve"].workflowType);
void run.start({
  workspace_uuid: workspaceUuid,
  order_uuid: orderUuid,
  decision: "approved",
  decided_at: new Date().toISOString(),
  idempotency_key: `order-approve:${orderUuid}:approved`,
});
```

Retrying the same idempotency key must not double-append the event (server/table rules).

---

## 4. Validation sequence before Staff

```bash
orkestia composition push
pnpm typecheck
orkestia composition push --save
orkestia composition expose --yes
orkestia staff validate
```
