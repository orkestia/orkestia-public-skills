# Worked first sessions

Placeholder ids (`wf_…`, UUIDs) are examples. Copy tool names and argument keys; substitute live values. Never pass `organization_uuid` or `actor` in `initial_data` for the types below; both are context-injected.

## 1. Operator: "I just connected Claude. What do I have and what can I do?"

```
whoami()
list_workflow_types(limit=0)
start_workflow("identity.organization.query", {})
start_workflow("identity.membership.query-by-org", {})
start_workflow("subscription.billing.summary", {})
start_workflow("connection.query", {})
```

Each `start_workflow` on a read-only type usually returns already terminal. Read `state_data` directly; call `watch_workflow` only when `is_terminal` is false.

Report as one table:

| Item | Value |
|---|---|
| Organization | `<name>` (`<uuid from whoami>`) |
| Members | 1 owner |
| Plan | `platform_subscription.status` from the billing summary |
| Connections | 0 |

Then the honest next step: "You have no provider connected, so cloud, GitHub, and Kubernetes namespaces will stop at prerequisites. Two things work right now with nothing attached: a hello-world run, and Sign in with Orkestia for an app of yours. Which first?"

## 2. Hello world, then the first mutation

```
get_workflow_schema("control.collection.distinct")
start_workflow("control.collection.distinct", { "items": ["a", "b", "a", "c"] })
```

Expected terminal `state_data`: `result` = `["a", "b", "c"]`, `count` = `3`. Say what happened: a **type** ran as a **run** (`wf_…`) and produced an **output**.

Then, after the user confirms the app name and callback:

```
get_workflow_schema("identity.app.provision")
start_workflow("identity.app.provision", {
  "name": "acme-portal",
  "redirect_uris": ["http://localhost:5173/callback"]
})
watch_workflow("wf_…")
```

Keep `identity_app_uuid`, `client_uuid`, `client_key`, and `integration` from `state_data`. Continue in `orkestia-app-platform`.

## 3. App builder: "I have a Lovable prototype. How do I give it real login and a Stripe backend?"

1. `whoami()`.
2. Login first because it needs nothing external: recipe 2 above with the app's real callback URLs. The `integration` block gives the front end everything it needs; the `client_key` is public.
3. Stripe next: `get_workflow_schema("connection.setup")` → read the `stripe` field group → `get_workflow_prerequisites("connection.setup", variant="stripe")` → hand the guide to the user (a restricted `rk_…` key is expected; `pk_…` keys are rejected). Continue in `orkestia-connections`.
4. Business logic the app's end-users may call is a **composition** exposed to the identity app. Continue in `orkestia-compositions`, then `identity.app.expose-virtual-workflow` from `orkestia-app-platform`.
5. If the user is writing TypeScript against `@orkestia/*`, switch to `orkestia-builder`; the same three objects (identity app, connection, exposed composition) are declared in code there.

## 4. Agent developer: "Give my LangGraph agent access."

1. `whoami()` to confirm the human session.
2. `get_workflow_schema("identity.api-token.create")`. Caller fields: `name`, optional `ttl_seconds` or `expires_at`.
3. Confirm the token name and lifetime with the user, then:

```
start_workflow("identity.api-token.create", { "name": "langgraph-dev", "ttl_seconds": 2592000 })
```

4. The plaintext token is in the terminal `state_data` once. Hand it to the user in the reply; do not write it anywhere else.
5. The agent sends `Authorization: Bearer <token>` to `https://mcp.orkestia.dev/mcp`. Its first call should be `whoami`.
6. Later: `identity.api-token.query` to list, `identity.api-token.rotate` to replace, `identity.api-token.revoke` to kill.

## 5. "What can Orkestia do for a restaurant?"

The user has a goal and no vocabulary.

```
list_workflow_types(q="order delivery")
start_workflow("chat.onboarding.explore", { "user_message": "What can Orkestia do for a restaurant that takes delivery orders?" })
```

Read `assistant_message` and `referenced_types` from the second run. For every referenced type, `get_workflow_schema` before repeating it as a capability. If the second run comes back `state_name: failed` with `failure_reason: platform_org_not_configured` (what the public server returned on 2026-09-04), say the assistant is not configured, and answer from the `q=` results alone. Then route: provider namespaces (for example `ifood.*`) go through `orkestia-connections` first; automation across them goes through `orkestia-compositions`.

## 6. `whoami` fails

- Authentication error in Claude Code → `mcp_auth()` with no arguments, then `whoami` again.
- Bearer-token client with a 401 → the token is expired or revoked. Mint a new one from an authenticated session (example 4) or the console.
- `whoami` succeeds but the user says "that is not my company" → the token binds one organization. They are a member of more than one; `identity.organization.query` lists them. Switching organizations is done in the console session that issued the token, not over MCP.
- No account at all → sign up in the web console, create the organization at `/onboarding`, then reconnect. Nothing in the catalog does this.
