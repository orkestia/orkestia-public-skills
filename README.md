# Orkestia Public Skills

Domain knowledge skills for operating the **Orkestia** platform through its public MCP server (`orkestia-core`) — written for agents and users who have **no access to source code or internal documentation**. The MCP catalog is the single source of truth: every capability is a registered, schema-typed workflow discovered and run through the MCP tools.

All content is derived from the live MCP catalog (workflow listings, schemas, prerequisites, and the server's `concept://` / `rule://` resources). Catalog snapshot: 2026-08-31 — 4,546 workflow types across 91 first-level namespaces. The catalog is always authoritative; verify specifics with `list_workflow_types()` and `get_workflow_schema()` rather than treating counts in these files as frozen.

This pack covers **platform operating domains** (identity, connections, runners, tickets, staff, apps, billing). It does not wrap every provider catalog (AWS, DocuSign, Hostinger, Xero, …). For those, use the operating loop: discover by prefix, read the schema, then start.

## Skills

| Skill | Domain |
|---|---|
| `orkestia-mcp-operating-loop` | The discovery → prerequisites → run → recovery loop every domain uses |
| `orkestia-connections` | Provider credentials (`connection.*`) — the root object everything references |
| `orkestia-runners` | Compute fleets (`runner.*`): groups, environments, executions, warm pools, DevKit |
| `orkestia-github` | Wiring GitHub (PAT / OAuth / App) and operating repos, PRs, CI (`github.*`) |
| `orkestia-tickets` | The work ledger (`ticket.*`): ingress, plans, git-work, delivery governance |
| `orkestia-compositions` | Building virtual workflows (`composition.*` + `control.*`) |
| `orkestia-staff` | The AI workforce (`staff.*`): org units, actors, dispatch, cockpit, founder queue |
| `orkestia-agents` | Agent runtime (`agents.*`): configs, skills, MCP servers, sessions, cost |
| `orkestia-registry-network` | Synced inventories (`registry.*`, `network.*`) consumed by runners and deploys |
| `orkestia-app-platform` | End-user apps: `identity.app`, end-users, seats, `appdata`, `apphost`, feature flags |
| `orkestia-subscription` | Stripe-backed billing (`subscription.*`): checkout, seats, add-ons, metering |

## Format

Each skill is a directory:

| File | Role |
|---|---|
| `SKILL.md` | The playbook. When to load, named use cases, step-by-step how-to recipes, object model, safe reads, gotchas. YAML frontmatter: `name`, `description` (third person, WHAT + WHEN). Keep under 500 lines. |
| `reference.md` | Workflow map grouped by job-to-be-done. Not an alphabetical dump. One level deep from `SKILL.md`. |
| `examples.md` | Worked scenarios with real workflow types and example `initial_data`. |

`SKILL.md` must teach **how to operate** the domain, not only list that a feature exists. Every primary flow is a numbered recipe an agent can follow through MCP.
