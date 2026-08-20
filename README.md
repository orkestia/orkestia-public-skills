# Orkestia Public Skills

Domain knowledge skills for operating the **Orkestia** platform through its public MCP server (`orkestia-core`) — written for agents and users who have **no access to source code or internal documentation**. The MCP catalog is the single source of truth: every capability is a registered, schema-typed workflow discovered and run through the MCP tools.

All content was derived exclusively from the live MCP catalog (workflow listings, schemas, prerequisites, and the server's `concept://` / `rule://` resources). Catalog snapshot: 2026-08-20 — 2,374 workflow types across 67 namespaces. The catalog is always the authoritative list; verify specifics with `list_workflow_types()` and `get_workflow_schema()`.

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

Each skill is a directory with a `SKILL.md` carrying YAML frontmatter (`name`, `description`) and the domain playbook: what the domain is, its object model, how to wire it, how to use it day-to-day, and its gotchas.
