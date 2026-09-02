---
name: orkestia-staff
description: Build and operate an Orkestia AI workforce — org units, hiring actors from agent configs, schedule/event/manual dispatch, RBAC and seats, the founder review queue, the Cockpit blueprint flow, and operator dashboards. Use when standing up a staff, hiring or pausing actors, wiring dispatch, reviewing the founder queue, applying a Cockpit plan, or checking whether actors are healthy.
---

# Orkestia staff

Staff is the **org chart**. Named **Actors** sit in **OrgUnits**, get dispatched, budgeted, role-bound, and supervised. Agents is the **machinery**: an Actor is an existing **AgentConfig** hired into the org (`staff.hire-actor`). Create the config first (see `orkestia-agents`); this skill hires and operates it.

Do not pass `organization_uuid` in `initial_data` — `whoami()` already scoped it. Confirm mutations with `get_workflow_schema` before `start_workflow`. Prefer `featured: true` rows; skip `staff.internal-workflow-*` and other `featured: false` inbox internals.

## When to load

Load this skill when the user wants to:

- Build a staff (Cockpit blueprint → validate → diff → apply)
- Create a unit tree and hire, pause, resume, or archive actors
- Wire scheduled, event, or manual dispatch
- Work the founder review queue or Slack/Telegram inbox connectors
- Grant/revoke roles, set RBAC mode, or mint actor tokens
- Answer “is this actor healthy / what is running / are we overspending / org-chart health?”

Load `orkestia-agents` when the work is configs, skills, MCP servers, or sessions rather than the org chart. Load `orkestia-builder-ops` when Staff is declared as `*.staff.ts` and applied with `orkestia staff apply`.

## Use cases

1. **Cockpit-build a staff** (primary) — plan a blueprint, validate, diff, apply, watch status.
2. **Hand-hire into a unit tree** — create OrgUnits, hire from an AgentConfig, pause vs archive.
3. **Dispatch** — scheduled (`dispatch-due-actors` / `manage-actor-schedule`), event-binding, or manual `invoke-actor`.
4. **Human in the loop** — founder queue vs actor inbox, respond/close envelopes, Slack/Telegram connectors.
5. **RBAC and seats** — role bindings, RBAC mode, mint tokens; paid seats live in `subscription.actor-rbac-seat.*`.
6. **Operator dashboards** — five reads for health, running work, spend, and org-chart health.

## How to recipes

### 1. Build a staff (Cockpit) — primary

Do not hand-assemble units and hires unless the user asks. Cockpit produces a reviewable blueprint and applies it with step tracking.

1. `whoami()`. Discover with `list_workflow_types(prefix="staff.")`.
2. Start a planning session:

```
start_workflow("staff.cockpit-session-start", {
  "mode": "<confirm via get_workflow_schema>",
  "intent": "<what this staff should do>"
})
```

Required: `mode`, `intent`. Optional: `user_uuid`, `context_snapshot`, `constraints`. Output includes `session_uuid`. Append follow-ups with `staff.cockpit-session-update`. Read live context with `staff.cockpit-context` (guidance-package inventory + config pins).

3. Generate a blueprint — either:

```
start_workflow("staff.cockpit-plan", {
  "mode": "<same mode>",
  "intent": "<staffing request>",
  "session_uuid": "<from step 2>",
  "target_org_unit_uuid": "<optional parent unit>",
  "max_actors": 5
})
```

or `staff.cockpit-plan-from-template` with required `template_key` (optional `variables`, `save_blueprint`). Plan output includes `blueprint`, optional `blueprint_uuid`, `validation_preview`, and `recommended_next_workflows`.

4. Version it unless the plan already saved:

```
start_workflow("staff.save-blueprint", {
  "name": "<blueprint name>",
  "mode": "<same mode>",
  "blueprint": { },
  "session_uuid": "<optional>",
  "status": "draft"
})
```

`status` defaults to `draft`. List/load with `staff.list-blueprints` / `staff.get-blueprint`.

5. Validate (read-only). Required field is the blueprint JSON:

```
start_workflow("staff.staff-blueprint-validate", { "blueprint": { }, "strict": true })
```

Check `valid`, `errors`, `missing_dependencies`, `unsafe_permissions`, `budget_risk`, `duplicate_responsibility`, `tool_schema_issues`. Use `normalized_blueprint` downstream.

6. Diff against live roster (read-only):

```
start_workflow("staff.staff-blueprint-diff", {
  "blueprint": { },
  "require_valid": true
})
```

Review `operations`, `destructive_operations`, `missing_approvals`, and the create/update/attach/grant/archive counts.

7. Apply. `approved_by_user_uuid` is required but injected from caller context — do not ask the user for it. Pass `blueprint_uuid` or inline `blueprint`. Dry-run first; set `allow_destructive` only after reviewing archive/grant ops:

```
start_workflow("staff.cockpit-apply-plan", {
  "blueprint_uuid": "<uuid>",
  "dry_run": true
})
```

Then the same call with `dry_run` omitted/false. Optional: `approval_envelope_uuid`, `idempotency_key`, `selected_operation_refs`, `continue_on_step_failure`. Output `apply_run_uuid`.

8. Watch:

```
start_workflow("staff.cockpit-apply-status", {
  "apply_run_uuid": "<from apply>",
  "include_step_details": true
})
```

Read `status`, `failed_operations`, `next_retryable_step`, `rollback_notes`, `created_resources`.

Assisted helpers (not the happy path): `staff.actor-builder-discover`, `staff.actor-builder-turn`, `staff.actor-kit-draft`, `staff.capability-recommend`, `staff.tool-scope-plan`, `staff.policy-suggest`, `staff.configure-runtime-baseline`, `staff.apply-baseline` (read-only dry-run of a declarative document). `staff.import-from-filesystem` is platform-admin only.

### 2. Unit tree, then hire (hand path)

Only when Cockpit is the wrong tool (one actor, already-known config).

1. Confirm an AgentConfig exists: `start_workflow("data.agents.list-configs", {})` — see `orkestia-agents` if you need to create one.
2. Create units. Required: `type`, `name`, `title`. Catalog description: OrgUnit kinds are **BU / Vertical / Unit**. Nest with `parent_org_unit_uuid`.

```
start_workflow("staff.create-unit", {
  "type": "BU",
  "name": "engineering",
  "title": "Engineering"
})
```

Then a child with `parent_org_unit_uuid` from `org_unit_uuid`. Optional `charter`. Manager: `staff.assign-team-manager` / `staff.clear-team-manager`. Reads: `staff.list-units`, `staff.get-unit`. Update: `staff.update-unit`. Soft-delete: `staff.archive-unit`. Hard-delete: `staff.purge-unit` (archived, no dependents).

3. Hire. Required: `agent_config_uuid`, `name`, `archetype`. Confirm `archetype` via `get_workflow_schema("staff.hire-actor")` — do not invent values. Optional: `org_unit_uuid` (omit = org-root), `schedule`, `triggers`, `on_invoke` (workflow fired on invoke), `capability_surface`, `urgency_class`.

```
start_workflow("staff.hire-actor", {
  "agent_config_uuid": "<from data.agents.list-configs>",
  "name": "pr-reviewer",
  "archetype": "<from schema>",
  "org_unit_uuid": "<optional unit>"
})
```

Output `actor_uuid`. Reads: `staff.list-actors`, `staff.get-actor`, `staff.get-actor-definition`.

4. Pause vs archive:

- **Pause** (`staff.pause-actor`, optional `reason`) — dispatcher **skips PAUSED** actors; reverse with `staff.resume-actor` (status back to ACTIVE).
- **Archive** (`staff.archive-actor`) — soft-delete, `status=DEPRECATED`, `archived_at` set. Not a pause. Prefer pause for temporary stop.

Update dispatch/capability metadata with `staff.update-actor`.

### 3. Three dispatch paths

Wire `on_invoke` at hire/update before relying on invoke.

**Scheduled**

- Edit the cadence: `staff.manage-actor-schedule` — required `actor_uuid` + `action`. Description: enable, disable, edit, or run. Confirm `action` via schema. Optional schedule fields: `schedule`, `patch`, `enabled`, `mode`, `interval_seconds`, `next_fire_at`, `task`, `input_data`, `on_invoke`, `dry_run`.
- Fire whoever is due: `staff.dispatch-due-actors` (no required caller fields). Optional `actor_uuid` to limit, `dry_run`, `max_dispatches`, `respect_agent_capacity`. Output `checked` / `due` / `dispatched` / `skipped`. PAUSED actors are skipped.
- Read: `staff.list-actor-schedules`.

**Event-driven**

```
start_workflow("staff.event-binding.create", {
  "actor_uuid": "<uuid>",
  "source": "<event source>",
  "event_type": "<event type>",
  "entrypoint_workflow": { }
})
```

Required: `actor_uuid`, `source`, `event_type`. Optional: `action`, `enabled`, `filters`, `input_template`, `entrypoint_workflow`, `dedupe_window_seconds`. CRUD: `staff.event-binding.get` / `list` / `update` / `archive`. Matching events run through `staff.dispatch-event-to-actor`. GitHub tag/branch creates are ingested by `github.create-dispatch-staff-event` (webhook pipeline — do not start it yourself; see `orkestia-github`). Prove an approved delivery was consumed: `staff.approval-delivery-evidence`.

**Manual**

```
start_workflow("staff.invoke-actor", {
  "actor_uuid": "<uuid>",
  "input_data": { }
})
```

Schedules the actor's `on_invoke` now. Optional `context`, `attachment_uuids`, `triggered_by`, `report_failures`. Output includes `run_uuid` / `session_uuid`.

### 4. Human in the loop

Actors write **outbox envelopes**, not email.

| Surface | Workflow | When |
|---|---|---|
| Founder queue | `staff.list-founder-queue` | Org-wide pending review, severity-routed. Operator inbox. Optional `severity`, `actor_uuid`, `org_unit_uuid`, `include_payload`. |
| Actor outbox | `staff.get-actor-outbox` | One actor's pending envelopes. |
| Actor inbox | `staff.list-actor-inbox` | What **that actor** sees: pending prompts, notifications, operator responses. Scope `actor`. |

**Founder/operator loop**

1. `start_workflow("staff.list-founder-queue", { "include_payload": true })`
2. Answer: `staff.respond-envelope` — required `actor_uuid`, `envelope_uuid`, `decision` (confirm `decision` via schema). Optional `response_payload`, `notes`.
3. Close after review: `staff.mark-envelope-done` — required `actor_uuid`, `envelope_uuid`. Optional `done_reason`, `resolution_payload`, `allow_already_done`.

High-risk mutations (`grant-role-binding`, `set-actor-rbac-mode`, `mint-actor-token`, `cockpit-apply-plan`) accept `approval_envelope_uuid` from this flow.

**Inbox connectors (Slack / Telegram)** — catalog text on `staff.dispatch-inbox-connector`.

```
start_workflow("staff.upsert-inbox-connector", {
  "provider": "<slack or telegram — confirm schema>",
  "connection_ref": "<connection handle>",
  "destination": "<channel or chat>",
  "name": "ops-alerts"
})
```

Required: `provider`, `connection_ref`, `destination`. List: `staff.list-inbox-connectors`. Send: `staff.dispatch-inbox-connector`. Inbound: `staff.inbox-connector-callback`. Structured reports: `staff.report-pr-review-required`, `staff.report-runtime-failure`. Manager snapshot: `staff.get-manager-status`.

Do not start `featured: false` send internals (`staff.build-inbox-send-input`, `prepare-inbox-deliveries`, `deliver-inbox-message`, `record-inbox-delivery`, `summarize-inbox-deliveries`).

### 5. Roles, RBAC mode, tokens, seats

```
start_workflow("staff.grant-role-binding", {
  "role": "<confirm via schema>",
  "scope": "<confirm via schema>",
  "staff_actor_uuid": "<principal actor>",
  "org_unit_uuid": "<optional scope unit>"
})
```

Required: `role`, `scope`. `granted_by_user_uuid` is context-injected. Principal: `staff_actor_uuid` or `user_uuid` (or `principal_type` + `principal_uuid`). Revoke: `staff.revoke-role-binding`. Reads: `staff.list-role-bindings`, `staff.resolve-my-roles`.

RBAC mode: `staff.set-actor-rbac-mode` — required `actor_uuid`, `permission_mode`; optional `seat_mode`. Confirm both mode strings via schema. `updated_by_user_uuid` is injected.

Mint exportable credentials: `staff.mint-actor-token` — required `actor_uuid`; `minted_by_user_uuid` injected. Optional `name`, `expires_at`, `allowed_workflow_prefixes`, `permission_mode`, `seat_mode`. Output includes `token` (treat as secret — never echo). Revoke: `staff.revoke-actor-token`.

**Seats are not in `staff.*`.** Availability: `subscription.actor-rbac-seat.status`. Resize: `subscription.actor-rbac-seat.resize`. Every **reduction** requires `confirm_rbac_actor_seat_loss: true` — reductions may revoke Staff actor RBAC tokens. Alias `subscription.actor-rbac-seat.change` is deprecated. See `orkestia-subscription`.

### 6. Operator dashboards

Start these reads; do not dump the rest of the dashboard catalog here.

| Question | Workflow | Required |
|---|---|---|
| Is this actor healthy? | `staff.get-actor-state` | `actor_uuid`. Optional `window_hours`, `include_recent_activity`, `include_pending_counts`. Read `health`, `dispatch`, `pending`. |
| What is running? | `staff.get-active-pipelines` | Running/queued runs, owners, blockers. |
| Are we overspending? | `staff.get-roi-ribbon` | Period spend, time saved, pending review load. Pair with `data.agents.budget-status` / `cost-by-config`. |
| Org chart health? | `staff.get-org-chart-health` | Health colors for BUs, verticals, units, actors. |
| What needs a human? | `staff.list-founder-queue` | Severity-sorted review work. |

Coding preflight (reports blockers without creating work): `staff.coding-run.preflight` — required `repository_uuid`, `ticket_uuid`, `actor_uuid`, `runner_group_uuid`. Optional `target_ref`. Checks work concurrency, runner pool, actor budget, model capacity, coding artifact storage.

## Object model

- **OrgUnit** — BU / Vertical / Unit tree. `create-unit` / `update-unit` / `archive-unit` / `purge-unit`; manager `assign-team-manager` / `clear-team-manager`.
- **Actor** — `hire-actor` binds an **AgentConfig**. Lifecycle ACTIVE ↔ PAUSED (`pause-actor` / `resume-actor`) or DEPRECATED (`archive-actor`).
- **Event binding** — org-isolated trigger: `source` + `event_type` + optional `entrypoint_workflow`.
- **Envelope** — outbox item for founder review; inbox item for the actor.
- **Blueprint** — Cockpit plan document; validate → diff → apply.
- **RoleBinding** — user or actor principal, `role` + `scope`, optional unit/actor targeting.
- **Apply run** — `apply_run_uuid` from `cockpit-apply-plan`, polled via `cockpit-apply-status`.

## Day-to-day reads

Safe to start (`read_only: true`): `staff.list-units`, `staff.list-actors`, `staff.get-actor-state`, `staff.get-actor-definition`, `staff.get-actor-journal`, `staff.list-founder-queue`, `staff.list-actor-inbox`, `staff.get-actor-outbox`, `staff.list-actor-schedules`, `staff.event-binding.list`, `staff.list-blueprints`, `staff.get-blueprint`, `staff.cockpit-context`, `staff.cockpit-apply-status`, `staff.staff-blueprint-validate`, `staff.staff-blueprint-diff`, `staff.apply-baseline`, `staff.list-role-bindings`, `staff.resolve-my-roles`, `staff.list-inbox-connectors`. There is no `data.staff.*` namespace — staff reads live under `staff.*`.

## Gotchas

- **PAUSED is skipped by the dispatcher.** `dispatch-due-actors` will not fire paused actors. Resume before expecting schedules or events to run.
- **Archive is not pause.** `archive-actor` sets DEPRECATED. Use pause for a reversible stop; archive when the seat should leave the roster.
- **Cockpit first.** Hand-building (`create-unit` + `hire-actor`) skips validate/diff/apply tracking. Use Cockpit unless the user wants a single known hire.
- **Paid seats.** RBAC actor seats live in `subscription.actor-rbac-seat.*`. Reductions need `confirm_rbac_actor_seat_loss: true` and can revoke tokens. Point seat quantity work at `orkestia-subscription`.
- **Hire needs a config.** `agent_config_uuid` is required. No config → `orkestia-agents`, then hire.
- **Invoke needs `on_invoke`.** `invoke-actor` schedules that hook; it does not invent a task.
- **Skip internals.** `staff.internal-workflow-*` and `featured: false` inbox send steps are not operator entry points.
- **Tokens are secrets.** `mint-actor-token` returns `token` once — do not log it.
- **High-risk applies.** Destructive blueprint ops and RBAC grants take `approval_envelope_uuid` from the founder queue.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, schema, watch, remediation.
- `orkestia-agents` — AgentConfig, sessions, skills, MCP, cost (the machinery you hire).
- `orkestia-runners` — fleets actors run on; `agents.runner-group.enable` / `disable`.
- `orkestia-tickets` — git-work and software-delivery context sessions may carry.
- `orkestia-subscription` — `subscription.actor-rbac-seat.status` / `resize`.
- `orkestia-app-platform` — end-user apps (not staff actors).
- `orkestia-github` — `github.create-dispatch-staff-event` for tag/branch → staff.
- `orkestia-compositions` — `entrypoint_workflow` targets, including virtual types.

## Additional resources

- Workflow map by job: [reference.md](reference.md)
- Worked `initial_data` scenarios: [examples.md](examples.md)
