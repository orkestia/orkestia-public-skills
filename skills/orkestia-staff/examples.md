# Staff examples

`organization_uuid` is injected — omit it. Confirm `mode`, `archetype`, `action`, `decision`, `role`, `scope`, and `permission_mode` with `get_workflow_schema` before substituting the placeholders below.

## 1. Cockpit: plan, validate, dry-run apply

```
whoami()
list_workflow_types(prefix="staff.")
get_workflow_schema("staff.cockpit-session-start")
get_workflow_schema("staff.cockpit-apply-plan")

start_workflow("staff.cockpit-session-start", {
  "mode": "<from schema>",
  "intent": "Stand up a small engineering staff that reviews pull requests and reports failures to the founder queue."
})
# → session_uuid

start_workflow("staff.cockpit-plan", {
  "mode": "<same>",
  "intent": "One reviewer actor under Engineering, scheduled plus on_invoke, founder-queue escalations.",
  "session_uuid": "<session_uuid>",
  "max_actors": 3
})
# → blueprint, maybe blueprint_uuid, validation_preview, recommended_next_workflows

start_workflow("staff.save-blueprint", {
  "name": "engineering-review-staff",
  "mode": "<same>",
  "blueprint": { },
  "session_uuid": "<session_uuid>",
  "status": "draft"
})
# → blueprint_uuid, version

start_workflow("staff.staff-blueprint-validate", {
  "blueprint": { },
  "strict": true
})
# → valid, errors, missing_dependencies, budget_risk

start_workflow("staff.staff-blueprint-diff", {
  "blueprint": { },
  "require_valid": true
})
# → operations, destructive_operations, missing_approvals

start_workflow("staff.cockpit-apply-plan", {
  "blueprint_uuid": "<blueprint_uuid>",
  "dry_run": true
})
# approved_by_user_uuid is context-injected
# → apply_run_uuid, steps, rollback_notes

start_workflow("staff.cockpit-apply-plan", {
  "blueprint_uuid": "<blueprint_uuid>"
})

start_workflow("staff.cockpit-apply-status", {
  "apply_run_uuid": "<apply_run_uuid>",
  "include_step_details": true
})
```

If `missing_dependencies` names a missing AgentConfig or runner group, stop and use `orkestia-agents` / `orkestia-runners` before applying for real. If `destructive_operations` is non-empty, set `allow_destructive` only after the user confirms, and attach `approval_envelope_uuid` when the founder queue minted one.

## 2. Hand-hire into a unit, then pause

Prerequisite: an AgentConfig UUID from `data.agents.list-configs`.

```
start_workflow("staff.create-unit", {
  "type": "BU",
  "name": "engineering",
  "title": "Engineering"
})
# → org_unit_uuid (bu)

start_workflow("staff.create-unit", {
  "type": "Unit",
  "name": "code-review",
  "title": "Code review",
  "parent_org_unit_uuid": "<bu org_unit_uuid>",
  "charter": "Review inbound pull requests and escalate blockers."
})
# → org_unit_uuid (unit)

get_workflow_schema("staff.hire-actor")

start_workflow("staff.hire-actor", {
  "agent_config_uuid": "<uuid from data.agents.list-configs>",
  "name": "pr-reviewer",
  "archetype": "<from schema>",
  "org_unit_uuid": "<unit org_unit_uuid>"
})
# → actor_uuid, status

start_workflow("staff.get-actor-state", {
  "actor_uuid": "<actor_uuid>",
  "include_pending_counts": true,
  "include_recent_activity": true
})

start_workflow("staff.pause-actor", {
  "actor_uuid": "<actor_uuid>",
  "reason": "Freeze dispatch during an incident"
})
# Dispatcher now skips this actor. Reverse with staff.resume-actor.
# Do not archive unless the hire should leave the roster (DEPRECATED).
```

## 3. Event binding + scheduled dispatch + manual invoke

```
get_workflow_schema("staff.event-binding.create")
start_workflow("staff.event-binding.create", {
  "actor_uuid": "<actor_uuid>",
  "source": "<from schema>",
  "event_type": "<from schema>",
  "entrypoint_workflow": { },
  "dedupe_window_seconds": 60
})
# GitHub tag/branch creates are ingested by github.create-dispatch-staff-event
# (do not start). Matching bindings then run via staff.dispatch-event-to-actor.

start_workflow("staff.manage-actor-schedule", {
  "actor_uuid": "<actor_uuid>",
  "action": "<enable|disable|edit|run — confirm schema>",
  "dry_run": true
})

start_workflow("staff.dispatch-due-actors", {
  "actor_uuid": "<actor_uuid>",
  "dry_run": true
})
# → checked, due, dispatched, skipped (PAUSED counts as skipped)

start_workflow("staff.invoke-actor", {
  "actor_uuid": "<actor_uuid>",
  "input_data": { "title": "Review today's open PRs" },
  "report_failures": true
})
# Fires on_invoke. → run_uuid / session_uuid
```

## 4. Founder queue vs actor inbox

```
start_workflow("staff.list-founder-queue", {
  "include_payload": true,
  "limit": 20
})
# Operator surface — org-wide, severity-sorted.

start_workflow("staff.respond-envelope", {
  "actor_uuid": "<from queue item>",
  "envelope_uuid": "<from queue item>",
  "decision": "<from schema>",
  "notes": "Approved; proceed."
})

start_workflow("staff.mark-envelope-done", {
  "actor_uuid": "<same>",
  "envelope_uuid": "<same>",
  "done_reason": "Founder approved"
})

start_workflow("staff.list-actor-inbox", {
  "actor_uuid": "<same>"
})
# Actor surface — prompts, notifications, and the operator response above.

start_workflow("staff.upsert-inbox-connector", {
  "provider": "<slack or telegram — confirm schema>",
  "name": "ops-alerts",
  "connection_ref": "<existing connection handle>",
  "destination": "#staff-alerts",
  "enabled": true
})
```

Use the founder queue when a **human** must review. Use `list-actor-inbox` when inspecting what the **actor** can see. Use connectors to fan envelopes out to Slack/Telegram; they do not replace `respond-envelope`.

## 5. Grant a role, set RBAC mode, mint a token

```
start_workflow("staff.list-role-bindings", {})
start_workflow("subscription.actor-rbac-seat.status", {})

start_workflow("staff.grant-role-binding", {
  "role": "<from schema>",
  "scope": "<from schema>",
  "staff_actor_uuid": "<actor_uuid>",
  "org_unit_uuid": "<optional unit>"
})
# granted_by_user_uuid injected. High-risk: pass approval_envelope_uuid from the founder queue.

start_workflow("staff.set-actor-rbac-mode", {
  "actor_uuid": "<actor_uuid>",
  "permission_mode": "<from schema>",
  "seat_mode": "<from schema>"
})

start_workflow("staff.mint-actor-token", {
  "actor_uuid": "<actor_uuid>",
  "name": "ci-export",
  "expires_at": "2026-12-31T00:00:00Z"
})
# → token (secret — do not log), token_prefix, token_state

# Seat reduction (orkestia-subscription) — never omit confirmation:
start_workflow("subscription.actor-rbac-seat.resize", {
  "paid_rbac_actor_seats": 1,
  "confirm_rbac_actor_seat_loss": true
})
```

## 6. Operator morning checks

```
start_workflow("staff.get-org-chart-health", {})
start_workflow("staff.get-active-pipelines", {})
start_workflow("staff.get-roi-ribbon", {})
start_workflow("staff.list-founder-queue", { "limit": 10 })

# For one noisy actor:
start_workflow("staff.get-actor-state", {
  "actor_uuid": "<uuid>",
  "include_recent_activity": true,
  "include_pending_counts": true
})

start_workflow("staff.coding-run.preflight", {
  "repository_uuid": "<repo>",
  "ticket_uuid": "<ticket>",
  "actor_uuid": "<uuid>",
  "runner_group_uuid": "<group>"
})
# Reports ready / blockers / warnings — does not create a run.
```
