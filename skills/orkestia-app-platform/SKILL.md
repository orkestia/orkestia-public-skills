---
name: orkestia-app-platform
description: >-
  Ship an end-user product on Orkestia — provision an identity app with PKCE
  OIDC sign-in, manage end-users/seats/groups/workspaces, expose compositions as
  the app's business logic, give it a bounded agent, store data in appdata
  virtual tables and documents, host the frontend on apphost, and gate features
  with flags. Also covers org-member API tokens, invitations, and membership
  needed while shipping. Use when the user mentions Sign in with Orkestia,
  identity.app, end-users, seats, appdata, apphost, AppHost, hosted site,
  <slug>.app.orkestia.dev, bundle.zip, "app not found", feature flags, PKCE,
  or exposing workflows to app customers.
---

# Orkestia app platform

Your organization provisions an **identity app**. Its **end-users** (your customers) get hosted PKCE login, seats, groups, workspaces, owner-scoped data, an optional bounded agent, and hosting. They are **not** org members. Per `rule://orkestia-auth-setup`, the stack wires with no human steps.

There is no `appfeatures` or `appusers` namespace. Features are `policy.feature-flag.*` plus exposed compositions. Users are `identity.end-user.*` + `identity.seat.*` + `identity.app-organization.*`.

Catalog counts move. Re-list before claiming a type exists:

```
whoami()
list_workflow_types(prefix="identity.")
list_workflow_types(prefix="appdata.")
list_workflow_types(prefix="apphost.")
list_workflow_types(prefix="policy.")
list_workflow_types(prefix="data.appdata.")
```

Do **not** pass `organization_uuid` (or `actor`) in `initial_data` unless a schema declares it **and** it is not context-injected. MCP injects org scope from the token.

## When to load

Load this skill when the user wants to:

- Add "Sign in with Orkestia" to a product (PKCE, `client_key`, hosted login)
- Invite or disable app customers, watch seat caps, or buy end-user seat packs
- Model access groups or in-app workspaces
- Expose a composition as the only business logic end-users may run
- Attach a bounded end-user agent
- Declare virtual tables, write owner-scoped records, or host `<slug>.app.orkestia.dev`
- Mint an **org-member** API token while shipping (not an end-user credential)

Use `orkestia-mcp-operating-loop` for the discovery → schema → start → watch loop. Use `orkestia-subscription` to pay for seats or to satisfy `apphost.site.claim` preconditions. Use `orkestia-builder` (and its sibling builder skills) when the product is a TypeScript/React app in the Builder Framework — CLI, `orkestia.config.ts`, and exposed virtual workflows from code.

## Use cases

1. Provision "Sign in with Orkestia" and wire PKCE.
2. Invite or create end-users; watch seats; buy packs; disable/delete to free a seat.
3. Groups (one group per user, capabilities) and app-organizations (workspaces).
4. Expose a composition; the app POSTs `/api/workflows` with the end-user JWT.
5. Point the app at an AgentConfig; end-users ask via `agents.end-user.ask`.
6. Appdata: apply a VirtualDataStructure, write/query records, batch transactions, documents, org-published rows.
7. Host: claim a live-mode site → upload a release → publish → rollback / set serving mode.
8. Feature flags via `policy.feature-flag.apply`.
9. Org-member identity while shipping: API tokens, org invitations, membership.

## How to recipes

Assume `whoami()` already ran. Before every mutation, `get_workflow_schema(<type>)` and fill only caller-supplied fields. Then `start_workflow` → `watch_workflow` (or `get_workflow_status`).

### 1. Provision "Sign in with Orkestia"

1. `get_workflow_schema("identity.app.provision")`.
2. `start_workflow("identity.app.provision", { "name": "<app name>", "redirect_uris": ["http://localhost:5173/callback", "https://<app>/callback"] })`.
3. Watch the run. Terminal output includes `identity_app_uuid`, `client_uuid`, public PKCE `client_key` (not a secret — safe in browser source), `redirect_uris`, and `integration` (`issuer`, `discovery_url`, `authorize_url`, `code_exchange_url`, `jwks_url`, plus `flow` / `sdk`).
4. **Frontend:** PKCE authorization-code against those endpoints. SDK `@orkestia/auth` (`github:orkestia/orkestia-auth-sdk`; `npm i github:orkestia/orkestia-auth-sdk` until the package is on npm).
   - `signIn()`: PKCE verifier + challenge, redirect to `authorize_url` (hosted login at login.orkestia.dev).
   - On `/callback`: POST `{ code, code_verifier }` to `code_exchange_url` → RS256 JWT.
   - Verify locally against `jwks_url` (`iss` = `issuer`). The token never appears in a URL.
5. Localhost later: `identity.app.allow-dev-origin` with `identity_app_uuid` + `origin` (optional `callback_path`, `dry_run`).
6. More callbacks: `identity.app.configure-client` (safe-by-default validation). Optional `identity.app.add-federation` (upstream SSO), `identity.app.set-email-domains` (live-mode allowlist).
7. Graduate **dev → live** with `identity.app.set-mode` (`identity_app_uuid` + `mode`). Catalog: one-way, irreversible. Confirm `mode` on the schema before starting. `apphost.site.claim` requires live mode.

Keep `identity_app_uuid` and `client_key`. List apps with `identity.app.query`.

### 2. Invite / create end-users and manage seats

1. `start_workflow("identity.seat.status", { "identity_app_uuid": "<uuid>" })` → `cap`, `consumed`, `free`, `over_cap_pending`.
2. If `free` is 0, buy a pack (raises the cap `identity.seat.status` reads):

   ```
   get_workflow_schema("subscription.billing.end-user-seat-pack.checkout")
   start_workflow("subscription.billing.end-user-seat-pack.checkout", {
     "identity_app_uuid": "<uuid>",
     "pack_size": <integer>,
     "success_url": "https://<app>/billing/success",
     "cancel_url": "https://<app>/billing/cancel"
   })
   ```

   Open `checkout_url` in a browser. Do **not** use `subscription.end-user-seat-pack.checkout` — that stub returns pending-support status and does not complete checkout. See `orkestia-subscription`.
3. `identity.seat.grant` also raises the cap (`identity_app_uuid`, `batch_size`, `source`). Read the schema for allowed `source` values; do not invent them. Prefer the paid checkout for customer packs.
4. Create: `identity.end-user.create` (`identity_app_uuid`, `email`) → `end_user_uuid`, `seated`.
5. Mail access: `identity.end-user.invite` (`identity_app_uuid` plus `end_user_uuid` and/or `email`; optional `app_organization_uuid`, `resend`, `expires_in_hours`).
6. List: `identity.end-user.query`. Login-time gate is `identity.end-user.admit` (admit/deny + seat) — operators do not normally start this; the hosted login does.
7. Free a seat: `identity.end-user.disable` (`identity_app_uuid`, `end_user_uuid`) or `identity.end-user.delete` (soft-delete). Hard cleanup after soft-delete: `identity.end-user.purge`. Force re-login: `identity.end-user.session.revoke`.

### 3. Groups and app-organizations

**Groups** — one access group per end-user, capability-based:

1. `identity.end-user.group.seed-defaults` for the app, or `identity.end-user.group.define` (`identity_app_uuid`, `slug`, `title`).
2. `identity.end-user.group.set-capabilities` (`identity_app_uuid`, `group_slug`, `capabilities` list). Confirm capability strings on the schema; do not invent them.
3. `identity.end-user.assign-group` (`identity_app_uuid`, `end_user_uuid`, `group_slug`; optional `force`). Output includes `previous_group` / `new_group`.
4. Read: `identity.end-user.group.list`.

**App-organizations** — workspaces inside the app (not the Orkestia org):

1. `identity.app-organization.create` (`identity_app_uuid`, `name`, `slug`; optional `kind`, `metadata`) → `app_organization_uuid`.
2. Invite: `identity.app-organization.invite` (`identity_app_uuid`, `app_organization_uuid`, plus `end_user_uuid` and/or `email`; optional `group_slug`).
3. Active member: `identity.app-organization.add-member`. Role: `identity.app-organization.assign-role`. List: `identity.app-organization.query`.
4. End-user side (end-user JWT): `identity.end-user.organization.query` / `get` / `switch`.

### 4. Expose a composition as the only end-user business logic

End-users may start **only** virtual (composed) workflows you exposed. Build the composition first (`orkestia-compositions`).

1. `get_workflow_schema("identity.app.expose-virtual-workflow")`.
2. `start_workflow("identity.app.expose-virtual-workflow", { "identity_app_uuid": "<uuid>", "composition_uuid": "<uuid>", "version": 1 })`.
3. Watch. Output includes `exposed`, `step_count`, `ineligible_steps`. Eligibility is checked; ineligible steps block exposure.
4. Optional audience: `identity.composition.set-audience` (`identity_app_uuid`, `composition_uuid`, `audience`; optional `groups`). Confirm `audience` on the schema. Read: `identity.composition.audience-query`.
5. Backfill the capability catalog: `identity.app.reconcile-catalog`. Revoke: `identity.app.unexpose-virtual-workflow`.
6. The **app** POSTs `/api/workflows` with the end-user JWT as Bearer. Orkestia injects the end-user principal immutably; workflows return only that user's data.

Inventory compositions with `data.composition.list`, not `list_workflow_types`. Compiled `virtual.<uuid>@<version>` types **may** appear under `prefix="virtual."`; an empty browse does not mean none exist (`orkestia-compositions`).

### 5. Bounded end-user agent

1. Create or pick an org-owned AgentConfig (`orkestia-agents`).
2. `identity.app.set-end-user-agent` (`identity_app_uuid`, optional `end_user_agent_config_uuid`) → `enabled`, `end_user_agent_config_uuid`.
3. End-user calls `agents.end-user.ask` or `agents.end-user.ask-stream`. Tools are exactly the exposed compositions; every call is re-authorized under the calling end-user.

Do not launch `agents.session-launch` as the end-user surface.

### 6. Appdata

Records are owner-scoped and policy-checked. `identity_app_uuid` / `end_user_uuid` on record writes are server-resolved from the end-user token (input ignored unless it agrees).

1. Apply a VirtualDataStructure: `data.appdata.structure.apply` (`identity_app_uuid`, `structure` dict; optional `dry_run`, `apply_plan`). Read the schema for the `structure` shape — do not invent keys. Inspect: `data.appdata.structure.query`.
2. Write: `data.appdata.record.write` (`database_slug`, `table_slug`, `payload`; optional `app_organization_uuid`, `idempotency_key`). Read/query/update/delete: `data.appdata.record.read` / `query` / `update` / `delete`.
3. Atomic batch: `data.appdata.transaction.apply` with `operations` — ordered `{op: 'create'|'update'|'delete', database_slug, table_slug, payload (create), record_uuid (update/delete), patch (update), resource_ref?}`. Optional batch `idempotency_key`.
4. Documents: `data.appdata.document.request-upload` (`storage_connection_uuid`, `bucket`, `kind`; optional `content_type`, `visibility_scope`, `ref_table_slug`, `ref_record_uuid`) → `document_uuid` plus server-chosen `bucket` / `key`. Upload the object, then `data.appdata.document.confirm` (`document_uuid`; optional `size`, `checksum`). Then `query` / `download-url` / `delete`.
5. Org-published rows visible to every end-user: first `identity.app.set-org-owned` (`identity_app_uuid`, `org_owned_enabled: true`). Then `appdata.publish-as-app` (`identity_app_uuid`, `database_slug`, `table_slug`, plus `payload` **or** `payloads`; table must declare ownership kind `app`). Keep `record_uuids`. Retract with `appdata.retract-as-app` (`identity_app_uuid`, `database_slug`, `table_slug`, `record_uuids`, `reason` — reason is required; no filter form).

### 7. Host the frontend (exact MCP sequence)

A claimed hostname is **not** a live page. Claim writes a `hosted_site` with `active_release_uuid = null`. Until `apphost.release.publish` succeeds, `https://<slug>.app.orkestia.dev` returns CloudFront **`app not found`**.

There is **no** MCP tool that accepts the zip. `apphost.release.create` only mints a **presigned S3 POST** (private bucket, one key, size-capped, ~900s TTL). The **client runtime** must HTTP-upload `bundle.zip`. The pod then publishes. Do not confuse this with Hostinger (`hostinger.*`) or `storage.upload.presigned-url` — those are other ticket factories.

**Do not say the app is live** after provision or claim. Live means: GET the URL returns the site HTML **and** `apphost.site.get` shows a non-null `active_release_uuid`.

#### Preconditions

1. Identity app exists (`identity.app.provision` — recipe 1). Keep `identity_app_uuid`.
2. App is **live**, not `dev`. If needed: `identity.app.set-mode` with `identity_app_uuid` + `mode` from the schema (one-way). Confirm `mode` on the schema; do not invent values.
3. Org has a qualifying platform subscription (`orkestia-subscription`). Claim is subscription-gated.

#### A. Claim (MCP)

1. `get_workflow_schema("apphost.site.claim")`.
2. `start_workflow("apphost.site.claim", { "identity_app_uuid": "<uuid>", "slug": "<optional>" })`. Slug `^[a-z][a-z0-9-]{2,39}$`; omit to derive from the app name. Immutable after claim; idempotent per identity app.
3. Keep `site_uuid`, `slug`, `url` (`https://<slug>.app.orkestia.dev`), `created` / `already_exists`.

#### B. Open a release (MCP)

1. `get_workflow_schema("apphost.release.create")`.
2. `start_workflow("apphost.release.create", { "site_uuid": "<uuid>" })`. Omit `organization_uuid` / `created_by_user_uuid` (context-injected).
3. Keep `release_uuid`, `upload_url`, `upload_fields`, `expires_in_seconds`, `max_bundle_bytes`, `prefix`.
4. If create fails, stop. Do not invent an upload URL.

#### C. Build `bundle.zip` (runtime filesystem)

Publish requires a zip with **`index.html` at the archive root** (not in a subfolder). Extra static files are fine. Rejected: zip-slip paths, missing root `index.html`, over `max_bundle_bytes`.

Minimal page:

```html
<h1>Hello world</h1>
```

```bash
printf '%s\n' '<h1>Hello world</h1>' > index.html
zip -X bundle.zip index.html
```

SPA: zip the built `dist/` **contents** so `index.html` is at zip root.

#### D. POST the zip (runtime HTTP — not a workflow)

`upload_url` is typically `https://<bucket>.s3.amazonaws.com/`. The bucket is **private**; the form is a short-lived ticket for one key.

1. Resolve `upload_url` (DNS). If it fails, **stop** — see Failure below. Do not call publish.
2. Multipart POST: every key in `upload_fields` as a form field (use the returned names; do not invent or drop fields). Last field: `file` = `bundle.zip` bytes (`curl -F` semantics).
3. Expect HTTP 2xx/204 from S3. Anything else: stop, keep `release_uuid`, do not publish.
4. The presign expires (`expires_in_seconds`, default 900). After expiry, run **create again** — do not reuse old fields.

#### E. Publish (MCP) — only after a successful POST

1. `get_workflow_schema("apphost.release.publish")`.
2. `start_workflow("apphost.release.publish", { "release_uuid": "<uuid>" })`.
3. Watch. Success: `url`, `slug`, `bundle_sha256`, `bundle_bytes`, `uploaded_count`, `callback_registered`. Publish HEADs `bundle.zip`, extracts to the immutable prefix, flips CDN routing, appends `https://<slug>.app.orkestia.dev/callback` on the identity client, prunes old releases.
4. If publish says `bundle not uploaded`, the POST never landed. Do not retry publish until D succeeds (new create if the ticket expired).

#### F. Verify (required)

1. `start_workflow("apphost.site.get", { "site_uuid": "<uuid>" })` — `active_release_uuid` must be the release you published.
2. `start_workflow("apphost.site.release-list", { "site_uuid": "<uuid>" })` — that release `status` is published and `is_active` is true. `pending_upload` with null `bundle_bytes` means D never happened.
3. HTTP GET `url`. Success: the HTML you zipped. **`app not found`**: no active release (claim-only or failed D/E).

#### After it is live

- Rollback: `apphost.release.rollback` (`site_uuid`; optional `release_uuid`, default previous published).
- Serving mode: `apphost.site.set-mode` (`site_uuid`, `mode`: `active` | `redirect` | `suspended`; `redirect_target` required iff `redirect`).
- Custom hostname: `apphost.site.domain-attach` / `domain-list` / `domain-detach` (read schemas first).
- Reads: `apphost.site.get` / `list`, `apphost.site.release-list`.

#### Failure: runtime cannot reach S3

If DNS or HTTPS to `upload_url` fails (common in ChatGPT / locked-down agent sandboxes):

- Report **exactly**: identity app (uuid), site (`site_uuid`, `slug`, `url`), release (`release_uuid`, `status=pending_upload`), that MCP create succeeded, that **this runtime cannot POST to the presigned URL**, that publish was **not** started.
- Do **not** claim the Hello World page is live.
- Do **not** try Hostinger, `storage.object.put`, or another provider as a substitute.
- Do **not** loop create/publish hoping bytes appear.
- If the user has a Builder repo and CLI, hand off to `orkestia-builder-ops` (`orkestia apphost publish --yes`) — the CLI does D on a machine that can reach S3.

TypeScript/React apps with `@orkestia/*`: prefer that CLI path. This recipe is the **MCP-only** path (no app repo).

### 8. Feature flags

1. `policy.feature-flag.apply` (`identity_app_uuid`, `flag_key`, `enabled`; optional `flag_type`, `plan_tier`). Confirm optional enums on the schema.
2. Read: `policy.feature-flag.query`. Remove: `policy.feature-flag.delete`.
3. Runtime checks: `policy.decision.evaluate` / `evaluate-batch`. Plan entitlement over billing: `policy.entitlement.query`.

### 9. Org-member API token (shipping, not end-users)

These tokens belong to **org members**, not end-users. Short path only — not a full IdP skill.

1. `get_workflow_schema("identity.api-token.create")`.
2. `start_workflow("identity.api-token.create", { "name": "<label>" })` — optional `ttl_seconds` or `expires_at`.
3. Watch. Copy `token` / `plaintext_token` **once**; `identity.api-token.query` returns metadata only (no secret).
4. Rotate: `identity.api-token.rotate`. Revoke: `identity.api-token.revoke`. Rename: `identity.api-token.update`.
5. Invite an org member: `identity.org-invitation.create` (`email`; optional `role`, `message`, `expires_in_days`). Then `query` / `resend` / `reveal-link` / `cancel`. Recipient: `accept` / `decline`. Membership: `identity.membership.query`, `update-role`, `remove`.

## Object model

| Object | What it is | Handle |
|---|---|---|
| Identity app | Tenant + public PKCE OIDC client | `identity_app_uuid`, `client_key`, `client_uuid` |
| End-user | App customer in Orkestia's store | `end_user_uuid` |
| Seat | Cap on seated end-users for one app | `identity.seat.status` |
| Group | One capability set per end-user | `group_slug` |
| App-organization | Workspace inside the app | `app_organization_uuid` |
| Exposed composition | The only workflow type end-users may start | `composition_uuid` + `version` |
| Appdata structure | Virtual databases → tables → fields | `database_slug` / `table_slug` |
| Hosted site | `<slug>.app.orkestia.dev` | `site_uuid` (slug immutable) |
| Hosted release | Immutable uploaded bundle | `release_uuid` |
| Org-member API token | Current user's token, not an end-user | `token_uuid` (plaintext once) |

## Day-to-day reads

Prefer `read_only: true` / featured query workflows. Do **not** start `data.identity.*` persist/prune rows — those are internals (`featured: false`).

- Apps: `identity.app.query`
- End-users: `identity.end-user.query`, `audit-query`, `whoami` (end-user JWT)
- Seats: `identity.seat.status`
- Groups: `identity.end-user.group.list`
- Workspaces: `identity.app-organization.query`; end-user `organization.query` / `get`
- Composition audience: `identity.composition.audience-query`
- Appdata: `data.appdata.structure.query`, `record.read` / `query`, `document.query` / `download-url`
- Host: `apphost.site.get` / `list`, `site.release-list`
- Flags: `policy.feature-flag.query`, `policy.entitlement.query`
- Org members: `identity.api-token.query`, `identity.membership.query`, `identity.org-invitation.query`, `identity.user.query`, `identity.organization.get` / `query`

## Gotchas

- `client_key` is public by design (PKCE). Never treat it as a client secret.
- `identity.app.set-mode` (dev → live) is **one-way**. Claim hosting only after live.
- `apphost.site.claim` needs live mode **and** a qualifying subscription; slug cannot change.
- Claim ≠ live. `url` existing plus CloudFront `app not found` means no published release.
- MCP never uploads `bundle.zip`. Create returns a ticket; the runtime POSTs; then publish. No `apphost.release.upload` type.
- `upload_fields` is the entire form. POST every returned field, then `file=@bundle.zip`. Ticket TTL is `expires_in_seconds`.
- Do not send AppHost bytes through Hostinger, `storage.upload.presigned-url`, or `storage.object.put`.
- Disable/delete frees the seat; `admit` is the login-time gate, not a provisioning substitute.
- `publish-as-app` requires `identity.app.set-org-owned` (`org_owned_enabled: true`) and an `app`-owned table.
- Record writes ignore a forged `end_user_uuid` unless it matches the end-user token.
- `subscription.end-user-seat-pack.checkout` (no `.billing.`) is a pending-support stub. Paid packs: `subscription.billing.end-user-seat-pack.checkout`.
- Do not invent `appfeatures.*` or `appusers.*`.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, schema, start, watch, recovery
- `orkestia-compositions` — author the virtual workflow you expose
- `orkestia-agents` — AgentConfig behind `set-end-user-agent` / `agents.end-user.ask`
- `orkestia-subscription` — seat packs, platform checkout, hosting entitlement
- `orkestia-staff` — org-member workforce (not app end-users)
- `orkestia-runners` — hosted runner metering that billing also sees
- `orkestia-tickets` — delivery cost ledger (`ticket.software-delivery.cost-*`)

## Additional resources

- Workflow map: [reference.md](reference.md)
- Worked scenarios: [examples.md](examples.md)
- MCP rule: `rule://orkestia-auth-setup`
