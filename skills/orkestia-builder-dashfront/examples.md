# Dashfront examples

---

## 1. Compile-time reject (do not do this)

```ts
bind: {
  merchant_id: IDENTITY_UUID,
  organization_uuid: "<will-fail>", // server-resolved — not allowed
}
```

Use `IDENTITY_UUID` only. If a workflow needs a workspace, expose a composition that takes `workspace_uuid` from the **end-user session** on the server, not from panel JSON.

---

## 2. Envelope-producing composition (panel source)

Author a composition that returns `{ kind: "scalar", value, unit? }` (or timeseries/table/categorical/error) as its output mapping. Confirm the exact envelope fields in `@orkestia/dashfront` types, then set:

```ts
source: { workflow: "virtual.<uuid>@<version>" }
```

Prefer a **logical name** resolved after save — do not freeze a UUID in a reusable dashboard if the CLI can bind slugs. Until that binding exists, treat the workflow type as catalog data and re-read it after `composition push --save`.

---

## 3. Unmanaged vs group-gated

```ts
// all exposed end-users of the Identity app
export default defineDashboard({ slug: "ops-public", rows: [/* … */] });

// requires dash:<dashboard_uuid>:view on the group
export default defineDashboard({
  slug: "ops-owners",
  access: { groups: ["merchant-owner"] },
  rows: [/* … */],
});
```
