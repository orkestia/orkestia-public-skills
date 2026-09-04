---
name: orkestia-start-here
description: >-
  Guides a first-time Orkestia user or agent through day zero: connecting an MCP
  client to mcp.orkestia.dev, confirming identity with whoami, checking that an
  organization, team, billing state, and provider connections exist, running a
  zero-risk hello-world workflow, running one guided first mutation, and routing
  by goal to the right domain skill. Load when the user is new to Orkestia, says
  "start with me", "where do I begin", "what can I do here", has just connected
  the MCP server, or asks how to get a token, create an organization, or take a
  first safe step. Hands off to orkestia-mcp-operating-loop for tool mechanics.
---

# Start here

Orkestia is an AI-native, multi-cloud orchestration platform. Every capability is a registered, schema-typed **workflow** you discover and run through the public MCP server. A newcomer needs four things in order: a connected client, a confirmed identity, a picture of what the organization already has, and one successful run. This skill delivers those four, then routes to a domain skill.

Ground every statement in a tool result. The catalog snapshot on 2026-09-03 held 4,550 types across 91 first-level namespaces, with 2,743 marked `featured`. Those numbers move; read `list_workflow_namespaces` for the live count. A registered type is a capability, not a production run.

```
connect client → whoami → org / team / billing / connections (reads)
→ hello world (control.*) → one guided mutation → route by goal
```

## When to load

Load this skill first whenever the person or agent is meeting Orkestia for the first time, or whenever a session starts without a known goal. Load it when the user asks how to connect Claude, Cursor, Codex, or another agent to Orkestia, how to get an API token, why `whoami` fails, whether they have an organization, what is safe to try first, or which of the pack's skills fits their intent. Once a goal is clear, hand off: `orkestia-mcp-operating-loop` for tool mechanics, then the domain skill from the routing table below. Load `orkestia-concepts` when the user wants vocabulary or a mental model rather than a first step.

## Use cases

1. **Connect a client.** The user has an Orkestia account and wants Claude, Codex, Cursor, or a custom agent talking to the platform. Outcome: the client reaches `https://mcp.orkestia.dev/mcp` and `whoami` returns an identity.
2. **No account or no organization yet.** `whoami` fails, or the user has never signed up. Outcome: the user completes sign-up and organization creation in the web console, then reconnects. Neither step is possible over MCP.
3. **First look at the org.** The user asks "what do I already have?" Outcome: organizations, members, billing state, and provider connections listed from read-only workflows.
4. **Hello world.** The user wants to see a workflow run end to end with zero risk. Outcome: a `control.*` run, a `workflow_id`, and `state_data` read as the output.
5. **First real capability.** The user wants one thing that works today with no cloud account attached. Outcome: `identity.app.provision` (Sign in with Orkestia) or a saved composition of `control.*` steps, after explicit confirmation.
6. **First provider.** The user wants AWS, GitHub, Stripe, or another provider wired. Outcome: `connection.setup` prerequisites handed to the user, then the connection created via `orkestia-connections`.
7. **"What should I do?"** The user has a goal but no vocabulary. Outcome: the goal mapped to a namespace and a skill, or an answer from `chat.onboarding.explore`.

## How to

### 1. Connect a client to the public MCP server

The public endpoint is `https://mcp.orkestia.dev/mcp` (Streamable HTTP). Health: `https://mcp.orkestia.dev/health`.

1. **Claude web, Claude Desktop, Claude Code.** Add the server by URL. The server publishes OAuth 2.1 discovery and dynamic client registration, so the client opens the hosted sign-in and stores the token itself. No manual token step. In Claude Code, if a tool returns an authentication error, call `mcp_auth` with no arguments, then `whoami` again.
2. **Cursor, Windsurf, opencode, and other native clients with OAuth.** Same URL, same OAuth flow, loopback callback.
3. **Agents that cannot open a browser** (OpenAI Agents, LangGraph, Warp cloud agents, internal runners). Send a static header `Authorization: Bearer <token>` with `server_url` set to the endpoint above. Mint the token from an already-authenticated session with `identity.api-token.create` (recipe 3, step 5) or from the web console.
4. **Verify.** Call `whoami`. Record `user_id`, `username`, `organization_uuid`, `token_type`, `principal_type`. If it returns, the client is connected and scoped to that organization.

Do not put the org UUID into any config file or environment variable "to be safe." The token already carries it.

### 2. No account, or `whoami` has no organization

1. Sign-up and organization creation happen in the **web console**, not over MCP. The user registers, verifies email, signs in, and is redirected to the onboarding form when they have no organization. The form asks for an organization name and an optional domain. The creator becomes the organization admin.
2. If the user was **invited**, the pending invitation is applied automatically on first login. Over MCP the equivalent is `identity.org-invitation.accept` with the invitation token.
3. There is no MCP workflow that creates an organization. `list_workflow_types(prefix="identity.organization.")` returns only `get` and `query`. Do not promise otherwise.
4. After the org exists, reconnect the client (recipe 1) so the token is scoped to it, then continue with recipe 3.

### 3. Read what the organization already has

All of these are `read_only: true`. Starting them creates short-lived runs, which is expected. Omit `organization_uuid` and `actor`: both are `source.kind: context` and the server injects them.

1. **Catalog overview.** `list_workflow_types(limit=0)` returns `namespaces` (counts by first and second level, by kind, by scope), `featured` (first page), `featured_total`, and `recent_activity` when there is any. Read it once; do not page thousands of rows.
2. **Organizations.** `start_workflow("identity.organization.query", {})` → `state_data.organizations`, `count`. Confirms the org from `whoami` and any others the user belongs to.
3. **Team.** `start_workflow("identity.membership.query-by-org", {})` → `users` with `role` (`owner`, `admin`, `member`). Optional `role` filter. Pending invitations: `identity.org-invitation.query`.
4. **Billing.** `start_workflow("subscription.billing.summary", {})` → `platform_subscription` (plan, status, seats), `entitlements`, `items`, `upcoming_invoice`, and `actions`, which names the exact checkout or change workflow for each purchasable thing and whether it is `available`. Read it before promising anything paid: AppHost site claims and hosted runner provisioning are gated on subscription state. To pay, the entry point is `subscription.platform.checkout` (returns a Stripe Checkout URL). See `orkestia-subscription`.
5. **API tokens.** `identity.api-token.query` lists the user's tokens. To mint one for a headless agent: `get_workflow_schema("identity.api-token.create")`, then `start_workflow` with `name` and optional `ttl_seconds` or `expires_at`. The plaintext token appears **once** in the terminal `state_data`. Hand it to the user; never echo it into logs or files. Revoke with `identity.api-token.revoke`, rotate with `identity.api-token.rotate`.
6. **Provider connections.** `start_workflow("connection.query", {})` → `connections`, `count`. Zero connections is normal for a new org and means every provider-touching namespace (`aws.*`, `github.*`, `kubernetes.*`, `stripe.*`, …) will fail prerequisites until recipe 6 runs.

Summarize the result in one short table: org, members, plan state, connection count. Do not list every namespace.

### 4. Hello world with zero risk

The `control.*` namespace holds pure data primitives: `read_only: true`, `requires_organization_uuid: false`, no prerequisites, `end_user_eligible: true`. They teach the start → watch → read-output loop without touching a provider.

1. `get_workflow_schema("control.collection.distinct")` — fields `items` (json, required), `field` (string, optional).
2. `start_workflow("control.collection.distinct", { "items": ["a", "b", "a", "c"] })`.
3. The result usually arrives already `is_terminal: true`. Read `state_data.result` (`["a", "b", "c"]`) and `state_data.count` (`3`). If it is not terminal, `watch_workflow(workflow_id)`.
4. Point out the three things the user just saw: a **type** (`control.collection.distinct`), a **run** (`wf_…`), and an **output** (`state_data`). Every capability in the platform works exactly this way.

Alternatives with the same properties: `control.text.split` (`text`, `separator`), `control.text.join` (`items`, `separator`), `control.text.replace` (`text`, `find`, `replace`). List them with `list_workflow_types(prefix="control.")`.

### 5. First guided mutation (needs no cloud account)

Pick one, confirm intent with the user, then run. Both are `read_only: false`.

**A. Sign in with Orkestia** (`identity.app.provision`). `has_prerequisites: false`. Provisions a hosted PKCE login tenant for the user's own app in one call.

1. `get_workflow_schema("identity.app.provision")`. Caller fields: `name` (required), `redirect_uris` (list), optional `mode`, `dev_allowed_emails`, `org_owned_enabled`. Omit `actor` and `organization_uuid`.
2. Confirm the app name and callback URLs with the user.
3. `start_workflow("identity.app.provision", { "name": "<app>", "redirect_uris": ["http://localhost:5173/callback"] })` → watch.
4. Output: `identity_app_uuid`, `client_uuid`, public `client_key` (not a secret), `redirect_uris`, `integration` (issuer, discovery, authorize, code-exchange, JWKS URLs). Keep the two UUIDs. Continue in `orkestia-app-platform` (MCP) or `orkestia-builder` (TypeScript app).

**B. A saved composition of `control.*` steps.** Teaches `composition.*` without a provider. Follow `orkestia-compositions`, using only `control.*` steps; the result is a `virtual.<uuid>@<version>` type the org can run and schedule.

Do not choose a provider mutation (`connection.setup`, `k8s.app.deploy`, `runner.*` provisioning) as the first mutation. Those need external setup or can bill.

### 6. First provider connection

1. `get_workflow_schema("connection.setup")` → `has_prerequisites: true`, `field_groups` keyed by `provider_type`, `prerequisite_variants`.
2. `get_workflow_prerequisites("connection.setup", variant="<provider>")`. Hand the returned markdown to the user; platform identity (for AWS, the AssumeRole principal) is already filled in.
3. Stop until the external pre-condition exists (IAM role, PAT, key). Then continue in `orkestia-connections`, which owns the per-provider payloads and the lifecycle.
4. After success, `connection.query` shows the new row and its `connection_uuid`. That UUID is what runners, registries, GitHub, storage, and AI-model workflows ask for.

### 7. Route a goal to a namespace and a skill

When the user states a goal without vocabulary, do three things in order.

1. **Ask the catalog.** `list_workflow_types(q="<two or three keywords>")`. Every term must match name or description. Prefer rows with `featured: true`; skip names with `-validate`, `.prepare`, `__pre`, `__post`, underscore segments, or descriptions that say "DAG step" or "compensation."
2. **Optionally ask the onboarding assistant.** `chat.onboarding.explore` is featured and `read_only: true`: it takes `user_message` (optional `history`), reasons over the catalog, never runs workflows, and returns `assistant_message` plus `referenced_types`. On 2026-09-04 it failed terminally with `failure_reason: platform_org_not_configured` on the public server, so try it once, and on any failure fall back to step 1 without retrying. Treat `referenced_types` as candidates to verify with `get_workflow_schema`, not as facts.
3. **Open the matching skill.**

| The user wants to… | Namespaces | Skill |
|---|---|---|
| Find, start, watch, retry any workflow | all | `orkestia-mcp-operating-loop` |
| Connect AWS, GCP, Azure, GitHub, Stripe, SQL, social platforms | `connection.*` | `orkestia-connections` |
| Operate GitHub repos, PRs, Actions, Projects | `github.*` | `orkestia-github` |
| Run CI or agent compute, warm pools, DevKit hosts | `runner.*` | `orkestia-runners` |
| Track work, gate agent fix plans, deliver code | `ticket.*` | `orkestia-tickets` |
| Build reusable multi-step logic without code | `composition.*`, `control.*` | `orkestia-compositions` |
| Stand up an AI workforce, hire actors, review a founder queue | `staff.*` | `orkestia-staff` |
| Configure agents, skills, MCP servers, sessions, cost | `agents.*` | `orkestia-agents` |
| Sync registries and cloud networking for deploys | `registry.*`, `network.*` | `orkestia-registry-network` |
| Invite teammates, change roles, mint API tokens, pay for the platform | `identity.*`, `subscription.platform.*` | `orkestia-org-and-team` |
| Give their own app login, end-users, seats, data, hosting | `identity.*`, `appdata.*`, `apphost.*`, `policy.*` | `orkestia-app-platform` |
| Pay, change plan, buy seats or add-ons | `subscription.*` | `orkestia-subscription` |
| Write a TypeScript/React app on `@orkestia/*` | CLI + code | `orkestia-builder` and siblings |
| Operate a provider catalog this pack does not wrap (Kubernetes, DocuSign, Xero, Hostinger, Neon, Cloudflare, …) | that prefix | `orkestia-mcp-operating-loop` with `prefix="<ns>."` |
| Understand a word or the mental model | — | `orkestia-concepts` |

Two surfaces, one platform: **MCP** (this pack's default; no app repo needed) and the **Builder Framework** (TypeScript, CLI, React shell). Ask which one the user is on before recommending a path.

## Object model for day zero

| Idea | Meaning |
|---|---|
| Account | A person who signed up in the web console. Holds API tokens. |
| Organization | The tenant every run is scoped to. Created in the console. `whoami` tells you which one the token binds. |
| Member | An account with a role (`owner`, `admin`, `member`) in an organization. Invited by email. |
| End-user | A customer of the user's **own** app, living in an identity app. Not a member. |
| Actor / agent | An AI principal that runs with its own token. Hired into Staff. |
| Type vs run | `list_workflow_types` lists capabilities. `start_workflow` returns a `workflow_id`; run tools take that id. |
| `read_only` | Safe to start with no side effect beyond a short-lived run. |
| `featured` | The author's hint that a type is a human entry point. A hint, not a permission. |
| `has_prerequisites` | External setup must exist before the run can succeed. Read the guide first. |
| Connection | The org-owned credential to a provider. The root object every provider namespace references by UUID. |
| Subscription | Stripe-backed. Gates hosted runners, AppHost claims, seats. Read `subscription.billing.summary`. |

## Day-to-day reads

`whoami`, `list_workflow_namespaces`, `list_workflow_types` (with `limit=0`, `q`, `prefix`, `featured`), `get_workflow_schema`, `get_workflow_prerequisites`, and the read-only types `identity.organization.query`, `identity.membership.query-by-org`, `identity.org-invitation.query`, `identity.api-token.query`, `subscription.billing.summary`, `connection.query`, every `control.*` type, `chat.onboarding.explore`.

Mutations in this skill, each behind explicit confirmation: `identity.api-token.create`, `identity.app.provision`, `identity.org-invitation.create`, `connection.setup`, `subscription.platform.checkout`.

## Gotchas

- **Org creation is web-only.** No catalog type creates an organization. Send the user to the console, then reconnect.
- **The first token comes from the console or an OAuth session.** `identity.api-token.create` needs an authenticated caller; it cannot bootstrap itself.
- **Plaintext tokens show once.** Read them from the terminal `state_data` of the create run and hand them over. Never write them to a file or a config the user did not ask for.
- **Zero connections is normal.** Do not diagnose a "broken" platform because `aws.*` fails on day zero. Run recipe 6.
- **Counts are snapshots.** Quote `list_workflow_namespaces` live, never a number from a document.
- **A capability is not a run.** Do not describe the catalog total as "N production workflows."
- **Do not start internals.** Names with `-validate`, `.prepare`, `__pre`, `__post`, underscore segments, or "DAG step" descriptions are children of a parent entry point.
- **Billable things need a second confirmation.** Runner provisioning, seat packs, checkouts, and AppHost claims move money or capacity. Read `subscription.billing.summary` first.
- **External resources stay with the human.** Orkestia produces paste-ready instructions for IAM roles, DNS, and third-party accounts. It does not create them for the user.
- **`chat.onboarding.explore` answers are candidates, and the run can fail.** Verify every `referenced_types` entry with `get_workflow_schema` before promising it. A terminal `failed` with `platform_org_not_configured` is a server-side configuration state, not a user error; fall back to `q=` search and say so.

## Sibling skills

`orkestia-concepts` (vocabulary and mental model), `orkestia-org-and-team` (teammates, tokens, platform billing), `orkestia-mcp-operating-loop` (tool mechanics every domain uses), then the domain skills in the routing table.

## Additional resources

- Client connection matrix and first-session read map: [reference.md](reference.md)
- Three first sessions worked end to end (operator, app builder, agent developer): [examples.md](examples.md)
