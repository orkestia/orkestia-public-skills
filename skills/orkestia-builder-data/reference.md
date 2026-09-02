# AppData / VDS reference

Recipes: [SKILL.md](SKILL.md).

## Ownership

| Mode | Who binds principal |
| --- | --- |
| `owner` | server from end-user token |
| `organization` | server from workspace membership + Identity org-owned flag |

Forbidden in VDS field lists: `organization_uuid`, `end_user_uuid`, `status`, `payload`, `metadata`, UUID system columns.

## CLI

```bash
orkestia identity set-org-owned [--yes]
orkestia appdata plan [--allow-organization-ownership]
orkestia appdata apply [--yes]
orkestia appdata inspect
```

## Record atomics (wrap, do not expose)

Typical types (confirm with `get_workflow_schema`):

- `data.appdata.record.query`
- `data.appdata.record.read`
- `data.appdata.record.write`
- `data.appdata.record.update`
- `data.appdata.transaction.apply`

Always pin `database_slug` and `table_slug` in composition source. Pass `app_organization_uuid` from composition **input** `workspace_uuid` for org-owned tables (server still verifies).

## Query policy

Only `allowedFilters` / `allowedSorts` that are indexed. Empty success ≠ access denied.

## Artifacts (ignore)

`.orkestia/appdata.plan.json`, `appdata.apply.json`, `appdata.structure.json`.
