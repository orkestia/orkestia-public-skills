---
name: orkestia-builder-dashfront
description: >-
  Authors code-first end-user analytics dashboards with @orkestia/dashfront
  (defineDashboard, analytics result envelope, principal-bind fail-closed). Use
  when writing *.dashboard.ts, panel sources (Lumen metrics or envelope workflows),
  IDENTITY_UUID binds, access groups, or when the user asks why a dashboard must
  not call lumen-api or send organization_uuid / end_user_uuid from the browser.
---

# Builder Dashfront

`@orkestia/dashfront` is the **authoring contract** for end-user analytics: `defineDashboard`, document validation, the result envelope, and query payload builders that **never send a principal**.

It does **not** implement Python `dashfront.*` workflows, talk to `lumen-api`, or render charts. The browser never uses a `lumk_` / `lump_` key. Refresh is a single principal-bound query on the server (`dashfront.dashboard.query` when that library is available in the catalog).

Lumen stays observability ingest. Dashfront is the **customer → end-user** analytics surface.

## When to load

Load when the user defines dashboards in TypeScript, binds panels to metrics or workflows, or tries to pass identity/org/app UUIDs into panel JSON.

Load `orkestia-builder-workflows` if a panel `source.workflow` needs a new composition that **returns the envelope**. Confirm live types with MCP `list_workflow_types(prefix="dashfront.")`.

## Use cases

1. **Publish a merchant overview** with mixed workflow + Lumen metric panels.
2. **Fail closed** on forbidden binds (`organization_uuid`, `end_user_uuid`, `identity_app_uuid`, `actor`).
3. **Restrict** a dashboard to access groups (`dash:<uuid>:view`).
4. **Author a workflow** that returns the envelope so a panel can use it.

## How to

### 1. Define a dashboard

```ts
import { defineDashboard, IDENTITY_UUID } from "@orkestia/dashfront";

export default defineDashboard({
  slug: "merchant-overview",
  access: { groups: ["merchant-owner"] },
  timeRange: { default: "7d", max: "90d" },
  filters: [{ name: "status", input: "query.status" }],
  rows: [{
    panels: [
      {
        id: "gmv",
        type: "stat",
        title: "GMV",
        source: {
          workflow: "commerce.analytics.gmv",
          bind: { merchant_id: IDENTITY_UUID },
        },
      },
      {
        id: "latency",
        type: "timeseries",
        title: "API latency",
        source: {
          lumen: {
            signal: "metric",
            name: "http.server.duration",
            project: "my-app",
          },
        },
      },
    ],
  }],
});
```

`IDENTITY_UUID` is the only principal placeholder allowed in panel JSON. Identity, org, and app are **server-resolved** at query time.

Omit `access` to leave the dashboard unmanaged (all exposed end-users). Named groups require capability `dash:<dashboard_uuid>:view`.

### 2. Envelope

Panel workflows must return the analytics result envelope: `scalar` | `timeseries` | `table` | `categorical` | `error`. Use `buildDashboardQueryInput` from the package when constructing query payloads — it will not attach a principal.

### 3. Lumen source (v1)

**Metrics only.** Log lines and error groups are rejected at compile time.

### 4. Save / query (catalog)

When present in the org catalog, member-plane save/publish and end-user query are workflow types under `dashfront.*` (names move — `list_workflow_types(prefix="dashfront.")` + `get_workflow_schema`). Do not invent REST calls to Lumen from the SPA.

A `DashboardView` React renderer may not exist yet in your framework version; still **do not** call Lumen ingest APIs from the client to “preview.”

## Gotchas

- Putting `organization_uuid` / `end_user_uuid` / `identity_app_uuid` / `actor` in `bind` or query input **fails at compile time**.
- Workflow types in `source.workflow` must exist and return the envelope — same catalog discipline as compositions.
- Do not document Dashfront under Lumen product URLs; it is an app analytics surface.

## Additional resources

- Envelope and bind rules: [reference.md](reference.md)
- Worked document: [examples.md](examples.md)
- Hub: [orkestia-builder](../orkestia-builder/SKILL.md)
