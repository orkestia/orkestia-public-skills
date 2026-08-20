---
name: orkestia-staff
description: Build and operate an Orkestia AI workforce (staff.*, 80 types) — org units, hiring actors from agent configs, schedule/event/manual dispatch, RBAC and seats, the founder review queue, the Cockpit blueprint flow, and the operator dashboards. The deepest domain; depends on agents, runners, tickets, and subscription.
---

# Orkestia staff

Staff turns agent configurations into a governed organization: named **Actors** placed in **OrgUnits**, dispatched on schedules and events, budgeted, role-bound, and supervised through a founder review queue.

## Object model

- **OrgUnit** — BU / Vertical / Unit tree: `create-unit`, `update-unit`, `archive-unit`, `purge-unit` (only archived, no dependents); per-unit manager: `assign-team-manager` / `clear-team-manager`.
- **Actor** — `staff.hire-actor` binds an existing **AgentConfig** (see `orkestia-agents`) as a named actor: required `agent_config_uuid`, `name`, `archetype`; optional `org_unit_uuid`, `schedule`, `triggers`, `on_invoke` (workflow fired on invoke), `capability_surface`, `urgency_class`. Lifecycle: `pause-actor` (dispatcher skips PAUSED) / `resume-actor` / `archive-actor` (DEPRECATED) / `update-actor`.
- **Governance** — `grant-role-binding` / `revoke-role-binding` / `list-role-bindings` / `resolve-my-roles`; `set-actor-rbac-mode` (permission mode + seat mode; paid seats live in `subscription.actor-rbac-seat.*`); `mint-actor-token` / `revoke-actor-token` (exportable actor credentials).

## Dispatch — three paths

| Path | Wiring |
|---|---|
| Scheduled | `dispatch-due-actors` fires actors whose schedule is due; `list-actor-schedules`, `manage-actor-schedule` (enable/disable/edit/run) |
| Event-driven | `event-binding.create`: `source` + `event_type` + optional `action`, `filters`, `input_template`, `entrypoint_workflow`, `dedupe_window_seconds`. CRUD: `event-binding.get/list/update/archive`. Platform events (e.g. GitHub tag/branch creates via `github.create-dispatch-staff-event`) flow through `dispatch-event-to-actor` |
| Manual | `invoke-actor` schedules the actor's `on_invoke` workflow now |

## Human in the loop

Actors write **outbox envelopes**, not emails:
- `list-founder-queue` — pending review work org-wide, severity-routed. `get-actor-outbox` per actor.
- `respond-envelope` (operator answers), `mark-envelope-done` (closes after review).
- External delivery: `upsert-inbox-connector` / `list-inbox-connectors` (Slack/Telegram), `dispatch-inbox-connector`, `inbox-connector-callback`.
- Structured reports into the queue: `report-pr-review-required`, `report-runtime-failure`. `approval-delivery-evidence` proves an approved event delivery was consumed by a binding.
- Actor-side: `list-actor-inbox` (scope: actor) combines pending prompts, notifications, and operator responses.

## Building a staff — the Cockpit path (recommended)

```
cockpit-session-start(mode, intent)         # persistent planning session; cockpit-session-update appends follow-ups
→ cockpit-plan | cockpit-plan-from-template # editable blueprint from intent + org context
→ save-blueprint                            # version it
→ staff-blueprint-validate                  # missing deps, unsafe permissions, invalid tool/MCP schemas,
                                            # budget exposure, duplicated responsibility, missing runner/model, hierarchy errors
→ staff-blueprint-diff                      # reviewable create/update/attach/grant/archive operations
→ cockpit-apply-plan → cockpit-apply-status # step tracking, failed steps, retryables, rollback notes
```

Context/reads: `cockpit-context` (read model incl. guidance-package inventory + config pins), `get-blueprint`, `list-blueprints`. Assisted helpers: `actor-builder-discover` (registry candidates + input contracts), `actor-builder-turn`, `actor-kit-draft` (complete kit: prompt, skills, MCP scope, schedule, budget, policy), `capability-recommend`, `tool-scope-plan` (allowed/blocked tools, risk level, approval gates), `policy-suggest`, `configure-runtime-baseline`, `apply-baseline` (read-only dry-run of a declarative staff document against the live roster), `import-from-filesystem` (platform-admin only).

## Operator dashboards (all read-only)

`get-actor-state` (health per actor) · `get-actor-journal` · `get-actor-definition` · `get-active-pipelines` (running/queued runs, owners, blockers, DAG summaries) · `get-org-chart-health` · `get-dependency-graph` · `get-conversation-map` · `get-momentum` (WoW invocations, spend, failures, escalations, PRs) · `get-roi-ribbon` (spend vs time saved vs review load) · `get-focus-compass` (aligned vs attention-consuming actors) · `get-substrate-stats` (runner capacity, queues, MCP availability, cost rollups) · `list-dispatch-log` · `list-audit-events` (AUDITOR role) · `get-manager-status`.
