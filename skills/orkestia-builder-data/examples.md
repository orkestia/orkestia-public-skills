# AppData examples

---

## 1. Owner-scoped preferences

```ts
import { db, field, table } from "@orkestia/data";

export default db("prefs", {
  tables: [
    table("ui", {
      ownership: "owner",
      fields: {
        theme: field.enum(["system", "light", "dark"], { default: "system" }),
      },
      query: { allowedFilters: ["theme"], allowedSorts: ["theme"] },
    }),
  ],
});
```

No `identity set-org-owned`. Wrappers omit `app_organization_uuid`; the server uses the end-user principal.

---

## 2. Org-owned work orders + apply

VDS as in [SKILL.md](SKILL.md), then:

```bash
orkestia identity set-org-owned --yes
orkestia appdata plan --allow-organization-ownership
orkestia appdata apply --yes
orkestia appdata inspect
```

If plan fails on reserved field `status`, rename to `state` and re-plan.

---

## 3. Empty vs forbidden

User: “query returned no work orders.”

1. Confirm `useWorkflow` called the **wrapper** with the **active** `workspace_uuid` from session/workspace switch.
2. If the run is `completed` with `count: 0` → empty state.
3. If the run **failed** with workspace capability / ownership → membership/role, then renew session. Do not retry with a guessed UUID.
