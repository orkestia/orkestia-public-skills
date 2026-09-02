# Builder Framework reference

Task recipes live in [SKILL.md](SKILL.md). This is the compact map of commands, files, env, and packages.

## CLI commands

| Command | Purpose | Live mutation |
| --- | --- | --- |
| `orkestia create <name>` | scaffold | no |
| `orkestia dev` | codegen + Vite | may bring up configured live defs |
| `orkestia build [--prod]` | codegen + static SPA | no |
| `orkestia codegen` | project workflow structure | no |
| `orkestia composition push` | emit authoring JSON | no |
| `orkestia composition push --save` | save + activate | yes |
| `orkestia composition push --save --expose` | save, activate, expose, lock | yes |
| `orkestia composition expose [--yes]` | end-user exposure | with `--yes` |
| `orkestia identity provision [--yes]` | Identity app | with `--yes` |
| `orkestia identity allow-dev-origin [--yes]` | CORS origin | with `--yes` |
| `orkestia identity set-org-owned [--yes]` | org-owned AppData auth | with `--yes` |
| `orkestia identity workspace query` | list workspaces | read |
| `orkestia identity workspace create … --yes` | create workspace | yes |
| `orkestia identity workspace add-member … --yes` | add member | yes |
| `orkestia identity workspace invite … --yes` | invite | yes |
| `orkestia identity workspace assign-role … --yes` | assign role | yes |
| `orkestia appdata plan` | structure dry-run | server dry-run |
| `orkestia appdata apply [--yes]` | apply structure | with `--yes` |
| `orkestia appdata inspect` | live structure | read |
| `orkestia resources validate` | local check | no |
| `orkestia resources inspect` | live inventory | read |
| `orkestia resources import` | generate selectors | read |
| `orkestia resources plan` | diff | read |
| `orkestia resources apply [--yes] [--allow-provision]` | apply | with `--yes` |
| `orkestia staff compile` / `render` | blueprint / graph | no |
| `orkestia staff validate` / `plan` | server validate/diff | read |
| `orkestia staff apply --dry-run` / `--yes` | audited apply | server |
| `orkestia staff watch <id>` | watch apply or run | read |
| `orkestia app bringup [--yes]` | provision + push + expose | with `--yes` |
| `orkestia apphost publish [--yes]` | managed static release | with `--yes` |
| `orkestia deploy` | external static **plan** | no direct cloud mutation |

Run `orkestia --help` for the current option set.

## Conventional layout

```text
app/
  data/**/*.data.ts
  pages/**/*.page.tsx
  resources/**/*.resources.ts
  staff/**/*.staff.ts
  workflows/**/*.vw.ts
src/main.tsx
src/App.tsx
orkestia.config.ts
vite.config.ts
.orkestia/
```

| Suffix | Discovered as |
| --- | --- |
| `.vw.ts` | virtual workflow |
| `.data.ts` | Virtual Data Structure |
| `.resources.ts` | Resource-as-Code |
| `.staff.ts` | Staff desired state |
| `.page.tsx` | file-system route |
| `.dashboard.ts` | Dashfront document (when used) |

## Generated artifacts

| Path | Typical policy |
| --- | --- |
| `.orkestia/<name>.composition.json` | optionally tracked |
| `.orkestia/composition.push-state.json` | project policy |
| `.orkestia/app.lock.json` | usually tracked |
| `.orkestia/catalog.snapshot.json` | ignored |
| `.orkestia/appdata.*.json` | ignored |
| `.orkestia/resources.*.json` | ignored |
| `.orkestia/staff.blueprint.json` | review artifact / usually ignored |
| `.orkestia/staff.{validation,plan,apply}.json` | ignored |
| `.orkestia/apphost/` | ignored |
| `.orkestia/generated/` | project policy |
| `dist/` | normally ignored |

## Environment

| Variable | Secret/private |
| --- | --- |
| `ORKESTIA_MEMBER_TOKEN` | secret |
| `ORKESTIA_ORGANIZATION_UUID` | private identifier |
| `ORKESTIA_APPROVED_BY_USER_UUID` | private identifier |
| `ORKESTIA_WORKFLOW_API_BASE_URL` | public config override |

The CLI loads ignored `.env`; shell values take precedence.

## Packages

| Package | Responsibility |
| --- | --- |
| `@orkestia/app` | config, `AppShell`, router, Vite (`withReactSingletons`) |
| `@orkestia/auth` | PKCE session |
| `@orkestia/react` | `OrkestiaProvider`, `useWorkflow`, `useRun`, `useAuth`, `RequireAuth` |
| `@orkestia/runtime` | token-bound client, `RunStore`, watch/reconnect/poll |
| `@orkestia/workflows` | `defineComposition`, `t`, `cond`, combinators |
| `@orkestia/data` | VDS DSL, AppData bindings |
| `@orkestia/dashfront` | `defineDashboard`, analytics envelope |
| `@orkestia/resources` | connections, runner groups, model profiles |
| `@orkestia/staff` | Staff blueprint authoring |
| `@orkestia/codegen` | structure → component descriptors |
| `@orkestia/components` | headless run/DAG/record primitives |
| `@orkestia/ui` | styled product layer |
| `@orkestia/contracts` | types-only workflow contracts |
| `@orkestia/cli` | project lifecycle |

## React phase model

`useWorkflow().phase` is derived locally:

```text
idle -> starting -> pending/running -> completed | failed
```

Stream disconnect and timeout are not terminal unless an authoritative snapshot is terminal.

## Live command discipline

1. Validate or compile offline.
2. Inspect live state.
3. Plan.
4. Review source hash, scope, and operations.
5. Apply with `--yes` (and `--allow-provision` when creating cloud capacity).
6. Watch terminal state.
7. Inspect the live result.
8. Keep receipts out of git.

## Boot modes

| Mode | When | Auth |
| --- | --- | --- |
| `sign-in` | Identity descriptor present (default product) | PKCE end-user |
| `member` | explicit `mode: "member"` or no Identity | host-supplied member token |

Never serialize a member token through `virtual:orkestia/config`.
