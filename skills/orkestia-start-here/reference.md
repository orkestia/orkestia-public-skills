# Start here — reference

Grouped by job. Verify every type with `get_workflow_schema` before starting it; catalog names and counts move.

## Connect a client

Public endpoint: `https://mcp.orkestia.dev/mcp` (Streamable HTTP). Health probe: `https://mcp.orkestia.dev/health`. OAuth discovery: `https://mcp.orkestia.dev/.well-known/oauth-authorization-server`.

| Client | Auth mode | What the user does |
|---|---|---|
| Claude web, Claude Desktop, Claude Code | OAuth 2.1 + dynamic client registration | Add the server URL; sign in through the hosted login when prompted. In Claude Code, `mcp_auth` (no arguments) re-triggers the flow. |
| Cursor, Windsurf, opencode, other native MCP clients | OAuth + loopback callback | Add the server URL; complete the browser sign-in. |
| Lovable, Replit Agent, hosted builders | OAuth when the platform documents its callback, otherwise a bearer token | Follow the platform's MCP-server dialog; paste a token from `identity.api-token.create` if OAuth is unavailable. |
| OpenAI Agents, LangGraph, LangChain, Warp cloud agents, custom runners | Static `Authorization: Bearer <token>` header | Mint a token (below), configure `server_url` to the endpoint, pass the header. |
| Slack | Bridge app, not direct MCP | Out of scope for day zero. |

Every mode ends the same way: `whoami` returns `user_id`, `username`, `organization_uuid`, `token_type`, `principal_type`, `exp`.

## Account and organization (web console)

| Step | Where | MCP equivalent |
|---|---|---|
| Sign up, verify email, first login | Web console `/register` | none |
| Create organization (name, optional domain) | Web console `/onboarding`, shown automatically when the account has none | none — `identity.organization.*` has only `get` and `query` |
| Accept an invitation | Automatic on first login | `identity.org-invitation.accept` (token) |

## First-session reads

All `read_only: true`. Omit context-sourced fields (`organization_uuid`, `actor`).

| Question | Tool or type | Output to read |
|---|---|---|
| Who am I, which org | `whoami` | `organization_uuid`, `principal_type`, `token_type` |
| What exists | `list_workflow_types(limit=0)` | `namespaces`, `featured`, `featured_total`, `recent_activity` |
| Which orgs am I in | `identity.organization.query` | `organizations`, `count` |
| Who is on the team | `identity.membership.query-by-org` (optional `role`) | `users`, `count` |
| Pending invites | `identity.org-invitation.query` | list |
| Am I paying, what am I entitled to | `subscription.billing.summary` (optional `identity_app_uuid`) | `platform_subscription`, `entitlements`, `items`, `actions` |
| My API tokens | `identity.api-token.query` | list |
| Which providers are wired | `connection.query` (optional `filters` object) | `connections`, `count` |
| Ask the catalog in prose | `chat.onboarding.explore` (`user_message`, optional `history`) | `assistant_message`, `referenced_types`; may fail with `platform_org_not_configured` (observed 2026-09-04), then use `q=` |

## Hello-world types (`control.*`)

`read_only: true`, `requires_organization_uuid: false`, no prerequisites.

| Type | Caller inputs | Output |
|---|---|---|
| `control.collection.distinct` | `items` (json), optional `field` | `result`, `count` |
| `control.text.split` | `text`, optional `separator`, `maxsplit` | list |
| `control.text.join` | `items`, optional `separator` | string |
| `control.text.replace` | `text`, `find`, `replace`, optional `regex` | string |
| `control.text.extract_matches` | `text`, `pattern`, optional `fields`, flags | rows |

Browse the rest with `list_workflow_types(prefix="control.")`.

## First mutations (confirm before each)

| Type | Needs | Output to keep |
|---|---|---|
| `identity.app.provision` | `name`; optional `redirect_uris`, `mode`, `dev_allowed_emails`, `org_owned_enabled` | `identity_app_uuid`, `client_uuid`, `client_key`, `integration` |
| `identity.api-token.create` | `name`; optional `ttl_seconds`, `expires_at` | plaintext token (shown once), `token_uuid` |
| `identity.org-invitation.create` | `email`; optional `role`, `message`, `expires_in_days` | `invitation_uuid`, `email_dispatched` |
| `connection.setup` | `provider_type` + that provider's field group; read prerequisites first | `connection_uuid`, `test_passed`, `persisted` |
| `subscription.platform.checkout` | `success_url`, `cancel_url`, plan and seat fields per schema | Stripe Checkout URL |

Not first mutations: `runner.*` provisioning (billable compute), `k8s.app.deploy`, `apphost.site.claim` (needs live-mode identity app and subscription state), anything under `aws.*` / `gcp.*` / `azure.*` (needs a connection).

## Skip these on day zero

Names with `-validate`, `-complete`, `.prepare`, `__pre`, `__post`, underscore segments (`ticket._scheduler.poll`, `agents._session-launch.*`), and descriptions containing "DAG step" or "compensation." Also `user.onboarding` (Cognito-side account hook, not a user entry point) and the `demo.*` pipeline (unfeatured demo steps).
