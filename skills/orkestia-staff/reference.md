# Staff workflow map

Catalog snapshot 2026-08-31: **96** `staff.*` types. Re-verify with `list_workflow_types(prefix="staff.")`. There is no `data.staff.*` namespace — reads are `staff.*` with `read_only: true`. Skip `featured: false` internals unless you are debugging a parent DAG.

## Org units

| Workflow | Role |
|---|---|
| `staff.create-unit` | Create BU / Vertical / Unit. Required `type`, `name`, `title`. Optional `parent_org_unit_uuid`, `charter`. |
| `staff.update-unit` | Mutable fields on an OrgUnit. |
| `staff.archive-unit` | Soft-delete (`archived_at`). |
| `staff.purge-unit` | Permanent delete of an archived unit with no dependent staff rows. |
| `staff.assign-team-manager` | One active actor becomes the unit manager. |
| `staff.clear-team-manager` | Clear that manager. |
| `staff.list-units` | List units (role-filtered). |
| `staff.get-unit` | Fetch one unit. |

## Actors

| Workflow | Role |
|---|---|
| `staff.hire-actor` | Bind an existing AgentConfig. Required `agent_config_uuid`, `name`, `archetype`. Optional `org_unit_uuid`, `schedule`, `triggers`, `on_invoke`, `capability_surface`, `urgency_class`. |
| `staff.update-actor` | Dispatch / capability metadata. |
| `staff.pause-actor` | Dispatcher skips PAUSED. Optional `reason`. |
| `staff.resume-actor` | ACTIVE again. |
| `staff.archive-actor` | Soft-delete: DEPRECATED + `archived_at`. |
| `staff.list-actors` | Roster (role-filtered). |
| `staff.get-actor` | Fetch one actor. |
| `staff.get-actor-definition` | Identity, unit, AgentConfig, dispatch hooks, capabilities, role bindings. Scope `actor`. |
| `staff.get-actor-state` | Lifecycle, sessions/runs, pending counts, health flags. Scope `actor`. |
| `staff.get-actor-journal` | Recent run/lifecycle audit journal. |

## Dispatch

| Workflow | Role |
|---|---|
| `staff.dispatch-due-actors` | Fire active actors whose schedule is due. Optional `actor_uuid`, `dry_run`, `max_dispatches`, `respect_agent_capacity`. |
| `staff.manage-actor-schedule` | Enable / disable / edit / run. Required `actor_uuid`, `action`. |
| `staff.list-actor-schedules` | Display-safe schedule summaries. |
| `staff.event-binding.create` | Required `actor_uuid`, `source`, `event_type`. Optional `action`, `filters`, `input_template`, `entrypoint_workflow`, `dedupe_window_seconds`. |
| `staff.event-binding.get` | Fetch one binding. |
| `staff.event-binding.list` | List bindings. |
| `staff.event-binding.update` | Update a binding. |
| `staff.event-binding.archive` | Disable and archive. |
| `staff.dispatch-event-to-actor` | Resolve enabled bindings and dispatch matches. |
| `staff.invoke-actor` | Schedule `on_invoke` now. Required `actor_uuid`. |
| `staff.list-dispatch-log` | Paginated dispatch + execution log. |
| `staff.approval-delivery-evidence` | Prove an approved `delivery_ref` was consumed by a binding. |

GitHub tag/branch create events are ingested by `github.create-dispatch-staff-event` (do not start; see `orkestia-github`).

## Human in the loop

| Workflow | Role |
|---|---|
| `staff.list-founder-queue` | Org-wide pending review, severity-routed. Optional `severity`, `actor_uuid`, `org_unit_uuid`, `include_payload`. |
| `staff.get-actor-outbox` | One actor's outbox (pending by default). |
| `staff.list-actor-inbox` | Inbound work **for that actor** (prompts, notifications, operator responses). Scope `actor`. |
| `staff.respond-envelope` | Required `actor_uuid`, `envelope_uuid`, `decision`. |
| `staff.mark-envelope-done` | Close after review. Required `actor_uuid`, `envelope_uuid`. |
| `staff.upsert-inbox-connector` | Slack/Telegram target. Required `provider`, `connection_ref`, `destination`. |
| `staff.list-inbox-connectors` | List connectors. |
| `staff.dispatch-inbox-connector` | Send an envelope to configured connectors (DAG). |
| `staff.inbox-connector-callback` | Apply an external connector callback. |
| `staff.report-pr-review-required` | Inbox item when a PR needs manager review. |
| `staff.report-runtime-failure` | Generic failure report. |
| `staff.get-manager-status` | Founder-review manager snapshot. |

**Skip** (`featured: false`): `staff.build-inbox-send-input`, `staff.prepare-inbox-deliveries`, `staff.deliver-inbox-message`, `staff.record-inbox-delivery`, `staff.summarize-inbox-deliveries`.

## Cockpit and blueprints

| Workflow | Role |
|---|---|
| `staff.cockpit-session-start` | Persistent planning session. Required `mode`, `intent`. |
| `staff.cockpit-session-update` | Append a follow-up instruction. |
| `staff.cockpit-context` | Read model: guidance-package inventory + config pins. |
| `staff.cockpit-plan` | Blueprint from intent. Required `mode`, `intent`. |
| `staff.cockpit-plan-from-template` | Required `template_key`. |
| `staff.save-blueprint` | Version before apply. Required `name`, `mode`, `blueprint`. `status` defaults `draft`. |
| `staff.get-blueprint` | Load one saved blueprint. |
| `staff.list-blueprints` | Filter by status, mode, template flag, search. |
| `staff.staff-blueprint-validate` | Required `blueprint`. Missing deps, unsafe permissions, tool/MCP schemas, budget, duplicates, hierarchy. |
| `staff.staff-blueprint-diff` | Required `blueprint`. Reviewable create/update/attach/grant/archive ops. |
| `staff.cockpit-apply-plan` | Apply approved blueprint. `blueprint_uuid` or `blueprint`. `approved_by_user_uuid` from context. Optional `dry_run`, `allow_destructive`, `approval_envelope_uuid`. |
| `staff.cockpit-apply-status` | Required `apply_run_uuid`. |

Assisted: `staff.actor-builder-discover` (read-only), `staff.actor-builder-turn`, `staff.actor-kit-draft`, `staff.capability-recommend`, `staff.tool-scope-plan`, `staff.policy-suggest`, `staff.configure-runtime-baseline`, `staff.apply-baseline` (read-only dry-run). `staff.import-from-filesystem` — platform-admin only.

## RBAC and tokens

| Workflow | Role |
|---|---|
| `staff.grant-role-binding` | Required `role`, `scope`. Principal: `staff_actor_uuid` or `user_uuid`. |
| `staff.revoke-role-binding` | Revoke a binding. |
| `staff.list-role-bindings` | List bindings. |
| `staff.resolve-my-roles` | Caller's own active bindings. |
| `staff.set-actor-rbac-mode` | Required `actor_uuid`, `permission_mode`. Optional `seat_mode`. |
| `staff.mint-actor-token` | Exportable token. Required `actor_uuid`. Treat `token` as secret. |
| `staff.revoke-actor-token` | Revoke exported credentials. |

Seats: `subscription.actor-rbac-seat.status`, `subscription.actor-rbac-seat.resize` (reductions need `confirm_rbac_actor_seat_loss: true`). Deprecated alias: `subscription.actor-rbac-seat.change`. Do not start `subscription.actor-rbac-seat.internal-grant` / `internal-revoke`.

## Operator dashboards (rest)

Primary five are in SKILL.md. Also:

| Workflow | Role |
|---|---|
| `staff.get-actor-journal` | Per-actor audit journal. |
| `staff.get-dependency-graph` | Units, actors, configs, sessions, skills, MCP, envelopes, recent activity. |
| `staff.get-conversation-map` | Actors, sessions, runs, messages, pending envelopes as threads. |
| `staff.get-momentum` | WoW invocations, spend, failures, escalations, PRs, movement by vertical/actor. |
| `staff.get-focus-compass` | Aligned vs attention-consuming actors. |
| `staff.get-substrate-stats` | Runner groups, queues, MCP availability, optional cost rollups. |
| `staff.get-documentation-index` | Docs, runtime evidence, known gaps. |
| `staff.list-audit-events` | AuditLog rows — **AUDITOR** role. |
| `staff.list-dispatch-log` | Dispatch + execution metadata. |

## Coding preflight

| Workflow | Role |
|---|---|
| `staff.coding-run.preflight` | Required `repository_uuid`, `ticket_uuid`, `actor_uuid`, `runner_group_uuid`. Reports `ready` / `blockers` / `warnings` without creating a run. |

## Skip — internals

`staff.internal-workflow-contract-sweep` / `-validate`, `staff.internal-workflow-doc-coverage-sweep` / `-validate`, `staff.internal-workflow-provider-matrix-validate`, `staff.internal-workflow-registry-drift-scan` / `-sweep`, `staff.internal-workflow-secret-boundary-sweep` / `-validate`, `staff.internal-workflow-state-machine-validate`. All `featured: false`.
