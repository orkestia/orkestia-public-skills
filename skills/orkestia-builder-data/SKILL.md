---
name: orkestia-builder-data
description: >-
  Models Orkestia AppData as TypeScript Virtual Data Structures (@orkestia/data:
  db, table, field), plans and applies structure with the orkestia CLI, and wraps
  record/query/transaction atomics in exposed compositions. Use when editing
  *.data.ts, ownership (owner vs organization/workspace), appdata plan/apply,
  query policy, or wrapping data.appdata.record.* for the browser.
---

# Builder AppData

`@orkestia/data` compiles TypeScript Virtual Data Structures (VDS) into the input `data.appdata.structure.apply` accepts. Domain compositions then call `data.appdata.record.*` and `data.appdata.transaction.apply`.

The **server** resolves the authenticated principal and enforces query policy. The browser never calls generic AppData atomics; it calls **your** exposed wrappers with **fixed** database/table slugs.

## When to load

Load when the user declares `app/data/*.data.ts`, runs `orkestia appdata plan|apply|inspect`, hits ownership/capability errors on records, or wants workspace-shared vs owner-private data.

Load `orkestia-builder-workflows` to wrap record ops. Load `orkestia-app-platform` for MCP-only AppData without a TS repo.

## Use cases

1. **Declare a database** with indexed filters/sorts and a safe ownership mode.
2. **Authorize org-owned tables** (`identity set-org-owned` + `--allow-organization-ownership`).
3. **Apply** structure, then **inspect**.
4. **Wrap** query/write/update in `enduser: true` compositions.
5. **Transaction + event table** for auditable commands.

## How to

### 1. Declare VDS

```ts
import { db, field, table } from "@orkestia/data";

export default db("work_orders", {
  tables: [
    table("work_order", {
      ownership: "organization",
      fields: {
        title: field.string({ required: true, indexed: true }),
        state: field.enum(["open", "in_progress", "done"], {
          default: "open",
          indexed: true,
        }),
        scheduled_at: field.timestamp({ indexed: true }),
        details: field.text(),
      },
      query: {
        allowedFilters: ["state", "scheduled_at"],
        allowedSorts: ["scheduled_at"],
      },
    }),
  ],
});
```

Place under `app/data/*.data.ts`.

| Mode | Declaration | Scope |
| --- | --- | --- |
| Owner | omit or `ownership: "owner"` | authenticated end-user |
| Organization | `ownership: "organization"` | active app-organization / workspace |

**Do not declare** `organization_uuid`, `end_user_uuid`, or other ownership system fields. The server binds them.

### 2. Safe-profile rules (compiler rejects)

- Database and table slugs: lowercase `[a-z0-9_]`; database slugs start with a letter.
- Reserved names are banned (`status`, `payload`, `metadata`, UUID-shaped system columns). Use `state`, `event_details`, `external_ref`.
- Filters/sorts must be **explicitly allowed** and index-compatible.
- Full scans stay disabled; query limits are bounded.

### 3. Plan and apply

Organization ownership is opt-in locally **and** authorized once on the Identity app:

```bash
export ORKESTIA_MEMBER_TOKEN=...
export ORKESTIA_ORGANIZATION_UUID=...

orkestia identity set-org-owned
orkestia identity set-org-owned --yes

orkestia appdata plan --allow-organization-ownership
orkestia appdata apply
orkestia appdata apply --yes
orkestia appdata inspect
```

The org-owned flag is **not** a field on `structure.apply` and cannot be spoofed by an end-user request.

Keep `.orkestia/appdata.*.json` ignored (live metadata). Do not treat a client-generated `apply_plan` as a portable source artifact.

### 4. Wrap atomics (browser path)

```ts
import { defineComposition, t } from "@orkestia/workflows";

export default defineComposition(
  {
    name: "work-order-query",
    inputs: {
      workspace_uuid: t.uuid(),
      filters: t.dict().optional(),
      limit: t.integer().optional(),
    },
    metadata: { enduser: true },
  },
  (c) => {
    const result = c.step("data.appdata.record.query", {
      database_slug: "work_orders",
      table_slug: "work_order",
      app_organization_uuid: c.input.workspace_uuid,
      filters: c.input.filters,
      limit: c.input.limit,
    });
    c.output({ records: result.records, count: result.count });
  },
);
```

Writes:

```ts
c.step("data.appdata.record.write", {
  database_slug: "work_orders",
  table_slug: "work_order",
  app_organization_uuid: c.input.workspace_uuid,
  payload: c.input.payload,
  idempotency_key: c.input.idempotency_key,
});

c.step("data.appdata.record.update", {
  database_slug: "work_orders",
  table_slug: "work_order",
  app_organization_uuid: c.input.workspace_uuid,
  record_uuid: c.input.record_uuid,
  patch: c.input.patch,
});
```

Payload/patch keys must match declared fields. Prefer typed composition inputs for high-risk commands; dictionaries only when the domain workflow validates them.

Then `orkestia composition push --save --expose`.

### 5. Query results vs auth failures

An empty list can mean: no rows, wrong workspace, filters exclude, or no access. Treat **zero records** as a successful empty state. Treat **capability / ownership errors** as a failed run and show them separately.

Workspace capability errors are not transport bugs. Confirm membership, active workspace, role/group, renewed session, and that the composition is the workspace-aware wrapper.

### 6. Transactions and events

Use `data.appdata.transaction.apply` when several writes must be one operation. For audit:

```text
command → validate projection → update projection
  → append immutable event (idempotency key)
```

Corrections append compensating events; do not edit history in place.

## Gotchas

- **`set-org-owned` is member-plane.** There is no safe end-user input that enables it.
- **Passing another workspace UUID does not grant access.** The server verifies membership.
- **UI capability checks** do not replace server authorization.
- Production `orkestia build --prod` enforces AppData gates — structure drift fails the release, not just runtime.

## Additional resources

- Field/ownership map: [reference.md](reference.md)
- Wrappers: [examples.md](examples.md)
- Workflows: [orkestia-builder-workflows](../orkestia-builder-workflows/SKILL.md)
- MCP AppData: [orkestia-app-platform](../orkestia-app-platform/SKILL.md)
