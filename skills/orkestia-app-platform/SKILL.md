---
name: orkestia-app-platform
description: Ship an end-user product on Orkestia — provision an identity app with PKCE OIDC sign-in, manage end-users/seats/groups/workspaces, expose compositions as the app's business logic, give it a bounded agent, store data in appdata virtual tables and documents, host the frontend on apphost, and gate features with flags. Covers identity.app, identity.end-user, identity.seat, identity.app-organization, appdata, apphost, policy.feature-flag.
---

# Orkestia app platform ("Sign in with Orkestia")

Your organization provisions an **identity app**; its **end-users** (your customers — distinct from org members) get auth, seats, groups, workspaces, data, an agent, and hosting. Per `rule://orkestia-auth-setup`, the whole stack wires with no human intervention.

## 1 · Identity: provision & sign-in

```
identity.app.provision({name, redirect_uris})
```
One call returns everything: a **public** PKCE `client_key` (no secret — safe in browser source), `client_uuid`, and `integration` endpoints (issuer, discovery_url, authorize_url, code_exchange_url, jwks_url). End-users sign in at the hosted login (login.orkestia.dev): PKCE authorization-code → POST `{code, code_verifier}` to the exchange URL → RS256 JWT, verified locally against JWKS. SDK: `@orkestia/auth` (github:ltinteg/ltinteg-orkestia-auth-sdk); reference app: github:ltinteg/ltinteg-orkestia-demo-app.

Manage: `configure-client` (safe-by-default validation), `allow-dev-origin` (localhost), `add-federation` (upstream SSO), `set-email-domains` (sign-in allowlist), `set-mode` (dev → live, **one-way**), `deprovision`, `query`.

## 2 · End-users, seats, groups, workspaces

- **Users** (`identity.end-user.*`): `create`, `invite` (mail access), `query` (paged), `disable`/`delete` (free the seat), `purge` (hard, after soft-delete), `session.revoke` (force re-login), `whoami`, `audit-query`. `admit` is the login-time seat gate (admit/deny + seat).
- **Seats**: `identity.seat.status` (cap / consumed / free), `identity.seat.grant` (raise the cap); paid packs via `subscription.billing.end-user-seat-pack.checkout`.
- **Groups** (capability-based access): `group.seed-defaults`, `group.define`, `group.set-capabilities`, `assign-group` (one group per user), `group.list`.
- **Workspaces** (multi-tenant orgs inside your app): `identity.app-organization.create/invite/add-member/assign-role/query`; end-user side: `end-user.organization.query/get/switch`.

## 3 · Business logic & the end-user agent

End-users may start **only** the composed workflows you exposed:
- `identity.app.expose-virtual-workflow({identity_app_uuid, composition_uuid, version})` (eligibility-checked); `unexpose-virtual-workflow`; `reconcile-catalog` backfills the capability catalog.
- The app POSTs to `/api/workflows` with the end-user JWT as Bearer — Orkestia injects the end-user principal immutably, so workflows return only that user's data.
- Agent surface: `identity.app.set-end-user-agent` points the app at an org-owned AgentConfig; then `agents.end-user.ask` / `ask-stream` run a bounded session under the calling end-user's authority (tools = exposed compositions, every call re-authorized).

## 4 · Data — appdata

- **Virtual tables**: `data.appdata.structure.apply` (a VirtualDataStructure: databases → tables → fields), `structure.query`. Records (owner-scoped, policy-checked): `record.write/read/query/update/delete`; `transaction.apply` runs an ordered batch atomically in one commit.
- **Documents**: `document.request-upload` (server-chosen storage coordinates) → `confirm` → `query` / `download-url` / `delete`.
- **Org-published rows** visible to every end-user: `appdata.publish-as-app` / `retract-as-app` — gated by the app's org-owned flag (`identity.app.set-org-owned`).

## 5 · Hosting & features

- `apphost.site.claim` reserves `<slug>.app.orkestia.dev` for a provisioned, **live-mode** identity app (subscription-gated; per-org site quota; slug immutable; idempotent per app).
- Releases are immutable: `release.create` (pending_upload + presigned size-capped POST for bundle.zip) → `release.publish` (byte-quota check, safe extract to immutable prefix, CDN KVS routing flip, registers the site's `/callback` on the identity client, prunes beyond retention) → `release.rollback` (re-point to any published release). `site.set-mode`: active / redirect / suspended. Reads: `site.get/list`, `site.release-list` (flags the currently served release).
- Feature flags per app: `policy.feature-flag.apply` (module/workflow on/off), `query`, `delete`.

## Naming note

There is no `appfeatures` or `appusers` namespace in the catalog — the feature surface is `policy.feature-flag.*` + workflow exposure; the user surface is `identity.end-user.*` + `identity.seat.*` + `identity.app-organization.*`.
