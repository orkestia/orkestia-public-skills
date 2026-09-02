# Builder ops reference

Recipes: [SKILL.md](SKILL.md).

## Resources CLI

```bash
orkestia resources validate
orkestia resources inspect
orkestia resources import --all
orkestia resources import --provider gcp --name "Primary GCP" --as gcp-primary --out app/resources/cloud.resources.ts
orkestia resources plan
orkestia resources apply [--yes] [--allow-provision]
```

Plan ops per declaration: `bind` | `create` | `validate` | `noop`.

Helpers: `existingConnection`, `managedConnection`, `runnerGroup`, `modelProfile`, `env`, `secretEnv`, `secretJsonEnv`, `connectionAccountRef`.

## Staff CLI

```bash
orkestia staff compile
orkestia staff render --format dot|mermaid|d2|graphml|json
orkestia staff validate
orkestia staff plan
orkestia staff apply --dry-run --approved-by-user-uuid <user_uuid>
orkestia staff apply --yes --approved-by-user-uuid <user_uuid> --watch
orkestia staff watch <apply_run_uuid|wf_...>
```

Server types (confirm with catalog): `staff.staff-blueprint-validate`, `staff.staff-blueprint-diff`, `staff.save-blueprint`, `staff.cockpit-apply-plan`, `staff.cockpit-apply-status`.

## Publish CLI

```bash
orkestia build --prod
orkestia apphost publish [--yes]
orkestia deploy    # plan only
```

## Resolution order for Staff live commands

1. `.orkestia/composition.push-state.json` → stamped `virtual.<uuid>@<version>`
2. `.orkestia/resources.apply.json` → `resourceOutput(...)`
3. Fail closed if either is missing when referenced
