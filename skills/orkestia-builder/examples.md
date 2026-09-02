# Builder Framework examples

Placeholders only. Substitute live Identity values from `identity provision` output. Never commit tokens or organization UUIDs.

---

## 1. First app: provision, origin, local run

**Goal:** a signed-in SPA on localhost that can later call an exposed virtual workflow.

```bash
export ORKESTIA_MEMBER_TOKEN=...
export ORKESTIA_ORGANIZATION_UUID=...

orkestia identity provision --yes
# Copy identity_app_uuid + client_key + redirect_uris into orkestia.config.ts
# Keep mode: "dev" and redirect_uris including http://localhost:3000/callback

orkestia identity allow-dev-origin --yes
```

In a **second** terminal with **no** member token:

```bash
pnpm dev
```

Open the configured origin, complete hosted login, land on `/callback`, then a guarded route. If CORS fails, wait for cache, confirm the origin (not the `/callback` path) was registered, and do not inject a member token into Vite.

---

## 2. Bind a workflow by lock name, not UUID

After `orkestia composition push --save --expose`:

```ts
import appLock from "../.orkestia/app.lock.json";
import { useWorkflow } from "@orkestia/react";

const noteQuery = appLock.exposedWorkflows["note-query"]?.workflowType;
if (!noteQuery) throw new Error("Run composition push --save --expose");

export function Notes({ workspaceUuid }: { workspaceUuid: string }) {
  const query = useWorkflow(noteQuery);
  return (
    <section>
      <button onClick={() => void query.start({ workspace_uuid: workspaceUuid })}>
        Load notes
      </button>
      {query.phase === "failed" ? <p>{query.error?.message}</p> : null}
      <pre>{JSON.stringify(query.output, null, 2)}</pre>
    </section>
  );
}
```

`useWorkflow` must render under `AppShell`. Fill only inputs the composition maps from `source: "input"`.

---

## 3. Member CLI vs browser

**Wrong:** `export ORKESTIA_MEMBER_TOKEN=...` then `pnpm dev` in the same shell (token can leak into the Node process that serves the SPA).

**Right:**

```bash
# terminal A — operator
export ORKESTIA_MEMBER_TOKEN=...
orkestia composition push --save --expose

# terminal B — browser app
unset ORKESTIA_MEMBER_TOKEN
pnpm dev
```

---

## 4. Release gate before AppHost

```bash
pnpm typecheck
orkestia resources validate
orkestia staff compile
orkestia composition push
orkestia appdata plan --allow-organization-ownership
orkestia build --prod

# live, after review
orkestia composition push --save --expose
orkestia apphost publish          # plan
orkestia apphost publish --yes    # mutate
```

Smoke from a clean browser profile: HTML 200, not a blank page, hosted login uses the **same** `client_key` as the claimed site, callback returns, workspace query/switch works, one exposed workflow starts.
