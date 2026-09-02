---
name: orkestia-builder-ops
description: >-
  Applies Builder Framework desired state on the member-token plane: Resource-as-Code
  (connections, agent runner groups, model profiles), Staff-as-Code (units, actors,
  schedules, tools), identity workspaces, production build, and AppHost publish.
  Use when editing *.resources.ts or *.staff.ts, running orkestia resources/staff/
  apphost commands, or shipping a static SPA to a claimed AppHost site.
---

# Builder ops (resources, Staff, publish)

Member-token work: bind infrastructure, declare a Staff org as code, and ship the static SPA. The browser never holds this token. Pair with `orkestia-connections`, `orkestia-runners`, `orkestia-staff`, and `orkestia-app-platform` when you need MCP schemas; this skill is the **CLI + TypeScript** path.

Supported Resource-as-Code kinds: **connections**, **agent-purpose** runner groups (`gce` / `cloud_run`), **model profiles**. Staff compile is local; validate/plan/apply call Staff Blueprint workflows.

## When to load

Load when the user writes `app/resources/*.resources.ts` or `app/staff/*.staff.ts`, runs `orkestia resources|staff|apphost|identity workspace|deploy`, or asks how to publish `<slug>.app.orkestia.dev`.

## Use cases

1. **Import or declare connections** without committing UUIDs or credentials.
2. **Plan/apply a runner group + model profile**, with `--allow-provision` only when creating cloud capacity.
3. **Compile Staff**, resolve local virtual workflows, dry-run, then `--yes --watch`.
4. **Workspace admin** (create/invite/assign) from the CLI.
5. **Production build + AppHost publish** with a smoke test.

## How to

### 1. Resource-as-Code

`existingConnection` must resolve **exactly one** live row. Prefer `provider` + `status: "active"`; add `name` when several connections share a provider.

```ts
import {
  defineResources,
  env,
  existingConnection,
  managedConnection,
  secretJsonEnv,
} from "@orkestia/resources";

const currentGcp = existingConnection("gcp-primary", {
  selector: { provider: "gcp", status: "active" },
});

const managedGcp = managedConnection("gcp-managed", {
  provider: "gcp",
  name: "managed-gcp",
  settings: { project_ref: env("GCP_PROJECT_ID") },
  credentials: {
    service_account_json: secretJsonEnv("GCP_SERVICE_ACCOUNT_JSON"),
  },
});

export default defineResources({
  connections: [currentGcp, managedGcp],
});
```

Literal credentials are rejected even if TypeScript is bypassed. Secrets resolve **immediately before** `connection.setup` and are **not** written to plan/apply files.

Runners and models reference connection **objects**, not live UUIDs:

```ts
runnerGroup("agent-runners", {
  name: "agent-runners",
  connection: currentGcp,
  backend: "gce",
  region: "us-central1",
  minCount: 0,
  desiredCount: 0,
  maxCount: 1,
  config: {
    project_id: connectionAccountRef(currentGcp),
    zone: "us-central1-a",
    machine_type: "e2-standard-2",
  },
});

modelProfile("primary-ai", {
  connection: currentOpenAi,
  defaultModel: "provider-model-name",
  modelConfig: { temperature: 0.2, max_tokens: 1600 },
});
```

Initial runner surface: `purpose=agent`, no CI integration, organization scope. `connectionAccountRef` pulls the provider project/account from the bound connection without committing it.

```bash
orkestia resources validate
orkestia resources inspect
orkestia resources import --all
orkestia resources plan
orkestia resources apply            # print plan
orkestia resources apply --yes
orkestia resources apply --yes --allow-provision
```

`import` writes selectors only (provider, optional name, status). It never writes connection UUIDs or credentials. Won’t overwrite unless `--force`.

Plans fingerprint organization scope so a plan from one org cannot be applied under another; the UUID itself is not stored.

**This slice does not** delete resources, replace runner groups, or rotate credentials. Immutable backend/scope/connection/region drift **fails planning** instead of replacing. An already-active managed connection is a no-op (`connection.query` cannot attest secrets still match).

### 2. Staff-as-Code

Author with `staff(...)`, `unit`, `actor`, `agentConfig`, `virtualWorkflow(...).from("./workflows/….vw.ts")`. Actor kinds: `loop`, `trigger`, `hybrid`. Scheduling is `.loop(...)`, not a `scheduled` kind.

```bash
orkestia composition push --save          # FIRST — resolve virtualWorkflow refs
orkestia resources apply --yes            # if Staff uses resourceOutput(...)
orkestia staff compile
orkestia staff render --format mermaid
orkestia staff validate
orkestia staff plan
orkestia staff apply --dry-run --approved-by-user-uuid <user_uuid>
orkestia staff apply --yes --approved-by-user-uuid <user_uuid> --watch
orkestia staff watch <apply_run_uuid>
```

`resourceOutput("runner-group", "agent-runners")` resolves from ignored `.orkestia/resources.apply.json` and **fails closed** if the resource was not applied.

Coding actors pin `runtimeProfile` and exact guidance package identity via env (package UUID/digest/oid) — compiler does not fetch package bytes. Live validation checks the org’s trusted inventory.

Event entrypoints can run a workflow **before** an LLM turn (`entrypoint.workflowType` or a `virtualWorkflow` ref). Unless `completeOnSuccess` is set, the workflow must return the `staff.actor.entrypoint.v1` contract (`complete` / `continue` / `retry_later` / `blocked` / `failed`).

Do not reimplement the Staff apply engine. Diagrams are exports (dot/mermaid/d2/graphml/json).

### 3. Workspaces (member CLI)

```bash
orkestia identity workspace query
orkestia identity workspace create --name "Example" --slug example --kind workspace --yes
orkestia identity workspace invite \
  --app-organization-uuid <uuid> \
  --email user@example.com \
  --group-slug operator \
  --yes
```

These are administrative. End-user apps use exposed wrappers for who-am-I, accessible workspaces, and switch.

### 4. Build and AppHost

```bash
pnpm typecheck
orkestia resources validate
orkestia staff compile
orkestia composition push
orkestia appdata plan --allow-organization-ownership
orkestia build --prod

orkestia composition push --save --expose
orkestia apphost publish
orkestia apphost publish --yes
```

`--yes` on AppHost: production build → ZIP with `index.html` at root → claimed site from `identity.identity_app_uuid` → presigned upload → publish → verify active release. Org scope comes from the **member token**, not an AppHost input.

Live Identity must be `mode: "live"`, HTTPS callbacks, production origins registered, **same** `client_key` as the claimed site. Publishing can succeed while login fails if Identity values point at a different app.

`orkestia deploy` emits an **external** S3/CloudFront **plan** from `config.deploy`. It does not mutate cloud from the CLI. Prefer AppHost for the integrated path.

## Gotchas

- **`--allow-provision` is billable.** Require it only when the plan creates/changes cloud capacity.
- **Staff before compositions are active** fails closed. Push `--save` first.
- **Ignore** `.orkestia/resources.*.json`, `staff.{validation,plan,apply}.json`, `apphost/`.
- **`ORKESTIA_ORGANIZATION_UUID` only** — no `ORKESTIA_ORG_UUID`.
- Vite success ≠ live Staff/resources/exposure match source.

## Additional resources

- Command details: [reference.md](reference.md)
- Staff + resources snippets: [examples.md](examples.md)
- MCP: `orkestia-connections`, `orkestia-runners`, `orkestia-staff`, `orkestia-app-platform`
