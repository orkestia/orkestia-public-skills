# Dashfront reference

Recipes: [SKILL.md](SKILL.md).

## Package exports

- `defineDashboard`
- `IDENTITY_UUID`
- envelope types: `scalar` | `timeseries` | `table` | `categorical` | `error`
- `buildDashboardQueryInput`

## Invariants

| Rule | Why |
| --- | --- |
| No `lumk_` / `lump_` in the browser | ingest keys are operator secrets |
| No org/user/app/actor in panel bind | server-resolved principal |
| Lumen v1 = metrics only | logs/error groups rejected |
| Groups optional | omit `access` → all exposed end-users |

## Panel sources

| Source | Shape |
| --- | --- |
| Workflow | `{ workflow: "<type>", bind: { … IDENTITY_UUID … } }` |
| Lumen metric | `{ lumen: { signal: "metric", name, project } }` |

## Not this package

| Surface | Where |
| --- | --- |
| `dashfront.save` / `dashfront.dashboard.query` | org catalog (when installed) |
| Chart renderer | app UI / future `DashboardView` |
| Visual editor | not in the framework authoring package |
