---
name: orkestia-builder
description: >-
  Builds Orkestia-native TypeScript/React apps with the Builder Framework
  (@orkestia/app, CLI, workflows, data, resources, staff, dashfront). Use when
  the user is scaffolding, configuring, running, or shipping an app whose
  identity, data, business logic, workers, and hosting run on Orkestia — not
  when they only want to operate the platform through MCP. Complements
  orkestia-app-platform (MCP/identity) with the code-first CLI and React shell.
---

# Orkestia Builder Framework

The Builder Framework is a TypeScript toolkit for apps whose **identity, data, business operations, automation, AI workers, and releases** run on Orkestia. You declare desired behavior in code; the CLI validates, plans, applies, exposes, builds, and publishes; Orkestia remains the server authority.

The framework is **pre-1.0**. Public APIs are typed and tested but may still evolve.

This is the **code path**. `orkestia-mcp-operating-loop` and the other pack skills are the **MCP path** to the same platform. Use MCP to discover a workflow type or debug a run; use this skill to author an app that calls those types.

## When to load

Load this skill first whenever the user is writing `@orkestia/*` application code, running `orkestia` CLI commands, editing `orkestia.config.ts`, or asking how a React SPA should talk to Orkestia.

Load a sibling instead (or after) for a specific layer:

| Job | Skill |
|---|---|
| TypeScript compositions, push, expose, `useWorkflow` | `orkestia-builder-workflows` |
| Virtual Data Structures, AppData plan/apply | `orkestia-builder-data` |
| Connections, runners, Staff-as-Code, AppHost publish | `orkestia-builder-ops` |
| End-user analytics dashboards | `orkestia-builder-dashfront` |
| MCP identity / seats / apphost without an app repo | `orkestia-app-platform` |
| MCP composition JSON without TypeScript | `orkestia-compositions` |

## Use cases

1. **Scaffold and sign-in.** Create an app, provision an Identity app, register localhost CORS, run `pnpm dev`.
2. **Ship a domain command.** Author `.vw.ts`, push/save/expose, bind the lock in React.
3. **Keep planes separate.** Member token in a CLI terminal only; browser holds a PKCE end-user session.
4. **Plan then mutate.** Offline validate → inspect → plan → `--yes` (and `--allow-provision` for billable runners).
5. **Publish.** Production build + AppHost `--yes`, then smoke-test login and an exposed workflow.

## How the pieces fit

```text
TypeScript source
  orkestia.config.ts
  app/data/*.data.ts
  app/workflows/*.vw.ts
  app/resources/*.resources.ts
  app/staff/*.staff.ts
  src/**/*.tsx
          |
          v
orkestia CLI
  validates -> plans -> saves/activates -> exposes -> builds -> publishes
          |
          v
Orkestia
  Identity + AppData + Workflows + Connections + Runners + Staff + AppHost
```

**The load-bearing security rule:** the browser may start only **virtual workflows explicitly exposed** to its Identity app. Member credentials, provider credentials, resource provisioning, and protected Staff workflows stay outside the browser.

## How to

### 1. Install and scaffold

Until `@orkestia/*` packages are on a public registry, build from a **Builder Framework source checkout** plus a **Node workflow SDK** checkout as siblings:

```text
workspace/
  orkestia-workflow-sdk-nodejs/     # Node SDK (typed catalog client)
  orkestia-builder-framework/       # this framework
  my-orkestia-app/
```

```bash
corepack enable
# SDK first, then framework
pnpm install && pnpm build   # in the SDK checkout
pnpm install && pnpm build   # in the framework checkout
node packages/cli/dist/bin.js create my-orkestia-app
cd my-orkestia-app
pnpm install
```

If scaffolded versions are not published, `link:` the framework packages you actually import (`@orkestia/app`, `@orkestia/auth`, `@orkestia/react`, `@orkestia/runtime`, `@orkestia/workflows`, plus data/resources/staff/dashfront when used). Do not copy `packages/cli/dist/bin.js` out of the workspace; it resolves packages at runtime.

Auth in the browser is `@orkestia/auth` (same PKCE client as `github:orkestia/orkestia-auth-sdk`).

### 2. Configure the shell (public values only)

`orkestia.config.ts` is shared by Vite and the CLI. Identifiers here are **not** bearer secrets:

```ts
export default {
  name: "my-orkestia-app",
  workflowApiBaseUrl: "https://workflow-api.orkestia.dev",
  dev: { port: 3000 },
  identity: {
    identity_app_uuid: "<identity-app-uuid>",
    client_key: "<public-pkce-client-key>",
    mode: "dev",
    redirect_uris: ["http://localhost:3000/callback"],
  },
  ui: { themeKit: { id: "my-orkestia-app", colorMode: "system" } },
};
```

Never put member tokens, end-user tokens, provider credentials, organization UUIDs, user UUIDs, or cloud account coordinates in this file or in any `VITE_` variable.

If the Identity app does not exist yet:

```bash
export ORKESTIA_MEMBER_TOKEN=...
export ORKESTIA_ORGANIZATION_UUID=...
orkestia identity provision --yes
```

Copy **only** the public Identity descriptor (`identity_app_uuid`, `client_key`, redirect URIs) into config. Keep `.orkestia/` live receipts ignored.

Register the local origin (redirect URI includes `/callback`; CORS origin does not):

```bash
orkestia identity allow-dev-origin --yes
```

CORS caches can lag briefly. Do not “fix” CORS by putting a member token in the frontend.

### 3. AppShell and React singletons

```tsx
import { AppShell, type AppRoutes } from "@orkestia/app";
import config from "../orkestia.config";
import { App } from "./App";

const routes: AppRoutes = [{ path: "/", Component: App }];

createRoot(document.getElementById("root")!).render(
  <AppShell config={config} routes={routes} />,
);
```

`AppShell` installs PKCE, `/callback`, `RequireAuth`, the token-bound runtime, and providers. Hooks (`useWorkflow`, `useSession`) must run **below** it.

Linked pnpm workspaces can bundle two Reacts. Keep:

```ts
import { withReactSingletons } from "@orkestia/app/vite";
export default withReactSingletons({});
```

Import `@orkestia/ui-kit/styles.css` once at the entry point if you use the styled kit.

### 4. Token planes

| Plane | Held by | Allowed to |
|---|---|---|
| End-user (PKCE) | browser | exposed virtual workflows for that user/workspace |
| Member | CLI / trusted operator | provision, composition save, AppData structure, resources, Staff, AppHost |
| Agent | Staff runner | tools granted by the Staff blueprint |

Use a **separate terminal** for member-token CLI work. Do not export `ORKESTIA_MEMBER_TOKEN` into the Vite process.

`ORKESTIA_ORGANIZATION_UUID` is the only org env var. Do not invent aliases (`ORKESTIA_ORG_UUID` is not read).

### 5. Common lifecycle

```bash
# Offline
orkestia resources validate
orkestia staff compile
orkestia composition push
orkestia build

# Authenticated reads / plans
orkestia resources inspect
orkestia resources plan
orkestia staff validate
orkestia staff plan
orkestia appdata plan --allow-organization-ownership

# Explicit live mutations
orkestia composition push --save --expose
orkestia resources apply --yes
orkestia resources apply --yes --allow-provision   # billable runners
orkestia staff apply --dry-run --approved-by-user-uuid <user_uuid>
orkestia appdata apply --yes
orkestia apphost publish --yes
```

Commands that mutate live state require `--yes`. Runner provisioning additionally requires `--allow-provision`.

### 6. Generated state vs source

| Artifact | Commit? |
|---|---|
| `orkestia.config.ts`, `app/**/*.ts`, `src/**` | yes |
| `.orkestia/app.lock.json` (exposure binding) | usually yes |
| `.orkestia/*.composition.json` | project policy |
| `.orkestia/*.plan.json`, `*.apply.json`, `apphost/` | **no** |
| tokens, credentials, org/user/workspace UUIDs | **never** |

The CLI loads an ignored project `.env`. Existing shell values win.

### 7. Protected work: queue, don’t expose

When an end user needs a provider call, credential, or operator action:

```text
browser → exposed submit composition → workspace-owned queue record
  → Staff actor claims → protected workflow → immutable event
  → browser queries result
```

Do not expose `connection.*`, Identity admin, runner provision, or AI-provider setup to the browser to make an error go away.

## Gotchas

- **Activation is server-authoritative.** Offline `composition push` does not prove types exist in the org. `--save` reports unknown types and invalid mappings.
- **`NOT_EXPOSED_TO_END_USERS`** means the Identity app has not exposed that virtual type. Expose an app composition; do not call atomics from the browser.
- **No top-level `status` field.** Derive UI from `state_name`, `is_terminal`, and `terminal_status`. An SSE timeout is transport, not proof of workflow failure — the runtime re-GETs the run and reconnects or polls.
- **Local success ≠ live success.** A Vite build does not prove exposure, AppData structure, resources, or Staff match source.
- **Scaffold `demo.echo.run`** is a placeholder. Replace it with a type from the target catalog (`list_workflow_types` / MCP) before `--save`.
- **Do not hard-code `virtual.<uuid>@<version>`** in reusable source. Resolve logical names from `.orkestia/app.lock.json`.
- Framework does **not** re-implement the composition compiler. TypeScript emits authoring JSON only; `composition.save` compiles and stamps.

## Additional resources

- Combinators, push, expose, React: [orkestia-builder-workflows](../orkestia-builder-workflows/SKILL.md)
- VDS and records: [orkestia-builder-data](../orkestia-builder-data/SKILL.md)
- Resources, Staff, publish: [orkestia-builder-ops](../orkestia-builder-ops/SKILL.md)
- Dashboards: [orkestia-builder-dashfront](../orkestia-builder-dashfront/SKILL.md)
- Command and file map: [reference.md](reference.md)
- Worked first-app scenario: [examples.md](examples.md)
