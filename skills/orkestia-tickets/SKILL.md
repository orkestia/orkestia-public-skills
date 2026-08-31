---
name: orkestia-tickets
description: Operate the Orkestia work ledger (ticket.*) — open tickets, ingest external signals, gate agent fix plans, run provider-blind git work, and publish exact-OID software delivery. Load whenever tracking work or driving an agent coding-delivery flow through the public MCP.
---

# Orkestia tickets

Tickets are the shared work ledger. Humans and adapters open or ingest into a ticket; agent coding work is governed here from plan gate through git-work, exact-OID publication, and software-delivery policy.

Catalog snapshot 2026-08-31: 107 `ticket.*` types. Re-verify with `list_workflow_types(prefix="ticket.")`. Do not start `ticket._scheduler.poll`.

Every mutation below: `whoami()` first, then `get_workflow_schema` for that type, then `start_workflow` + `watch_workflow`. Do **not** pass `organization_uuid` in `initial_data` — it is injected from the Bearer token.

## When to load

Load this skill when any of these is true:

- The user wants to open, search, comment, assign, or transition a ticket.
- A Linear issue, Lumen error group, alert, audit finding, or actor finding should become a ticket.
- An agent proposed a fix and a human must acknowledge before apply.
- Coding work must bind a worktree/branch without giving the actor a Git-provider credential.
- A clean local head must be published through the trusted broker (exact OID), then opened as a PR.
- Delivery needs an immutable policy snapshot, cost, evidence, controller claims, or safe resume.
- An org wants delivery/git policy bound to a repository (`ticket.repository-policy.*`).

Assume `orkestia-mcp-operating-loop`. Prefer `featured: true` rows; skip internal `*-prepare` / `*-finalize` / `*-commit` / `*-plan` DAG children unless a schema you just read names them as the entry point.

## Use cases

1. **Open a human ticket** — `kind` / `title` / `source_type` / `owner_type` / `owner_uuid`; collapse duplicates with `source_fingerprint`; then comment, assign, transition, search, get.
2. **Ingest a signal** — `ticket.ingest.*` vs `ticket.open`; outbound `ticket.external.binding.upsert` + `ticket.external.sync.dispatch`. Details: [examples.md](examples.md).
3. **Agent-fix plan gate** — propose → human acknowledge → apply. Apply refuses unacknowledged plans; reject kills the plan.
4. **Provider-blind git work** — begin → observe → reconcile → complete. The coding actor never holds a Git-provider credential.
5. **Exact-OID delivery** — publish-request → claim-next → push-record (needs lease) → publish-confirm (remote OID **exactly equals** requested local head). Fail + typed resume. Then `github.pulls.create_exact_pr` ([orkestia-github](../orkestia-github/SKILL.md)).
6. **Coding artifacts** — portable Git bundles: reserve → prepare → upload-start → available → verification. Legal-hold, expire, deletion leases. Details: [examples.md](examples.md).
7. **Software-delivery governance** — begin (immutable policy snapshot) → evidence-record → cost-reserve/record → controller-claim-next. recovery-inspect/resume (exact stored safe-resume only). mutation-control. slo-scan.
8. **Repository policy** — bind delivery/git policy to a repo with `ticket.repository-policy.*`. Details: [reference.md](reference.md).

## How to

### 1 · Open a human ticket, then operate it

1. `whoami()` — use `user_id` as `owner_uuid` when `owner_type` is `human`.
2. `get_workflow_schema("ticket.open")`.
3. `start_workflow("ticket.open", initial_data={...})` with **required**: `kind` (`incident` | `task` | `info`), `title`, `source_type` (`human` for a person; also `lumen_error_group`, `actor_finding`, `alert_rule`, `audit_finding`, `tool_request`, `workflow_run`, `api`, `linear`), `owner_type` (`human` | `actor` | `agent` | `platform`), `owner_uuid`.

```
start_workflow("ticket.open", initial_data={
  "kind": "task",
  "title": "Fix checkout timeout",
  "source_type": "human",
  "owner_type": "human",
  "owner_uuid": "<whoami.user_id>",
  "body": "p95 checkout exceeds 5s on prod",
  "priority": "priority",
  "source_fingerprint": "human:checkout-timeout"
})
```

4. Optional: `body`, `priority`, `severity`, `labels`, `subject_type`/`subject_uuid`, `source_uuid`, `source_fingerprint`, `assignee_type`/`assignee_uuid`, `dispatch`, `extra`, `evidence_refs`.
5. Watch the run. Outputs: `ticket_uuid`, `created` (true = new row; false = collapsed), `status`, `occurrence_count`.

**`source_fingerprint`:** a stable dedupe key. Repeated opens with the same fingerprint collapse into one ticket and bump `occurrence_count` instead of creating a second ledger row. Omit it only when every open must be a distinct ticket.

**Priority canon:** `page` / `priority` / `routine` / `deferred`. Aliases: `urgent`→`page`, `high`→`priority`, `medium`→`routine`, `low`→`deferred`.

Then, always passing `ticket_uuid` (and never `organization_uuid`):

| Job | Workflow | Required inputs | Notes |
|---|---|---|---|
| Comment | `ticket.comment` | `ticket_uuid`, `body` | Optional `actor_type` / `actor_uuid`. Returns `event_uuid`. |
| Assign | `ticket.assign` | `ticket_uuid`, `assignee_type`, `assignee_uuid` | Optional `dispatch` (inbox delivery), `note`. |
| Transition | `ticket.transition` | `ticket_uuid` plus `to_status` **or** `intent` | `intent` aliases: `start` \| `resolve` \| `close` \| `ignore` \| `reopen`. Optional `resolution`, `comment`. Discover allowed next statuses from `lifecycle` on `ticket.search` / `ticket.get` — there is **no** `ticket.allowed_transitions` type. |
| Search | `ticket.search` | none besides context | Filters: `status`, `priority`, `kind`, `source_type`, `q`, `unassigned`, labels, time bounds, `hydrate`. Status values: `open`, `triaged`, `in_progress`, `blocked`, `resolved`, `closed`, `ignored`. |
| Hydrated get | `ticket.get` | `ticket_uuid` | Optional `include`: `triggers`, `links`, `events`, `plans`. Returns `ticket`, `lifecycle`, `live`. |

Edit mutable fields with `ticket.update` (`priority`, `severity`, `title`, `body`, `labels`, subject). Relate tickets with `ticket.link` (`link_kind`, `target_type`, `target_uuid`) — **suggest, never auto-merge**. Canonical `link_kind`: `relates_to`, `duplicate_of`, `blocks`, `blocked_by`, `caused_by`, `parent_of`, `child_of`, `source_ref`, `subject_ref` (alias `splits_from`→`child_of`).

Schedule a one-shot or recurring action with `ticket.schedule` (`ticket_uuid`, `kind`, `action_workflow_type`; optional `run_at` / `starts_at` / `interval_seconds`). Fires **under the ticket owner's authority**. Pause/cancel with `ticket.trigger.cancel` (`trigger_uuid`).

When the **source domain** itself changed (not a human status click), `ticket.reconcile` with `source_state` (and `ticket_uuid` or `source_fingerprint`) suggests a status and, when authoritative, applies it.

### 3 · Agent-fix plan gate

```
ticket.plan.propose → ticket.plan.acknowledge → ticket.plan.apply
ticket.plan.reject   # kills an active (proposed or acknowledged) plan permanently
```

1. Agent: `get_workflow_schema("ticket.plan.propose")` then start with required `ticket_uuid`. Optional `summary`, `body`, `steps`, `proposed_by_type` / `proposed_by_uuid`, `source_workflow_run_uuid`. Output: `plan_uuid`, `status`, `superseded` (prior active plans this replace).
2. Human: `get_workflow_schema("ticket.plan.acknowledge")` then start with `plan_uuid` and/or `ticket_uuid`. Optional `comment`, `actor_type` / `actor_uuid`. This is the **required gate**.
3. Apply: `ticket.plan.apply` with the same identity fields. **Refuses a plan that has not been acknowledged.**
4. Kill: `ticket.plan.reject` (`reason` optional) so the plan can never be applied.

Read plans via `ticket.get` with `include=["plans"]`. Do not skip acknowledge.

### 4 · Provider-blind git work

The coding actor never holds a Git-provider credential. Git identity is native OIDs and full refs.

1. Optional concurrency peek (read-only): `ticket.git-work.concurrency` with `repository_uuid`, `branch_ref` (optional `target_ref`, `ticket_uuid`). Returns `conflict`, `blocker_code`, `active_count` without claiming.
2. `get_workflow_schema("ticket.git-work.begin")`. Start with required `ticket_uuid`, `repository_uuid`. Optional: `executor_uuid` + `worktree_uuid` (pre-bound work), `runner_group_uuid` (cloudless DevKit group that claims ownerless planned work), `branch_ref` (full `refs/heads/*`; omit to derive a collision-proof ref), `target_ref`, `base_oid`, `head_oid` (resume only; not derived). Output: `work` (dict) and `created`. Copy the work identity from `work` into later `work_uuid` fields after you read the actual keys.
3. As the local repo changes: `ticket.git-work.observe` with `work_uuid`, `sequence`, `idempotency_key`, `ref_name`. Optional `head_oid`, `base_oid`, `dirty`, `ahead_count` / `behind_count`. Observations are ordered and idempotent.
4. Before treating the tree as the acknowledged head: `ticket.git-work.reconcile` with `work_uuid` (optional `local_head_oid`). Compares local HEAD to the last acknowledged HEAD and **blocks drifted work**. Output includes `matches`.
5. Finalize: `ticket.git-work.complete` with `work_uuid` and `outcome` (`merged` | `completed` | `abandoned`), plus native OIDs (`head_oid`, `published_oid`, `merge_oid`) — not a hosting-provider API.

Reads: `ticket.git-work.get` (`work_uuid`, optional `include_observations`), `ticket.git-work.list` (`ticket_uuid`).

### 5 · Exact-OID delivery via trusted broker

Publication is a broker path. The coding actor requests; a trusted operator-side broker claims a lease, pushes, and records. Confirm advances **only** when the independent remote-ref OID **exactly equals** the requested local head.

1. A software-delivery lifecycle must already exist (`ticket.software-delivery.begin` — recipe 7). Copy `delivery_uuid` and `policy_digest` from that run's `delivery` object (or from a later `ticket.software-delivery.get`) after you read the actual keys.
2. `get_workflow_schema("ticket.git-delivery.publish-request")`. Start with required `delivery_uuid`, `sequence`, `idempotency_key`, `requested_head_oid`, `destination_ref`, `policy_digest`. Optional `binding_uuid`, `artifact_uuid` (portable bundle — use case 6), `expected_remote_oid`. Output includes `attempt`.
3. **Trusted broker** (not the coding actor): `ticket.git-delivery.claim-next` with required `broker_uuid`, `lease_uuid` (optional `lease_seconds`, `attempt_uuid`). Atomically leases one attempt, pins pre-push work to its owning executor **unless** an exact portable artifact is available, returns the immutable broker binding.
4. After the push: `ticket.git-delivery.push-record` with required `attempt_uuid`, `broker_uuid`, `lease_uuid`, `outcome`. **Requires the active lease.** Optional `native_push_ref`, `provider_request_ref`, `evidence`.
5. Independent readback: `ticket.git-delivery.publish-confirm` with `attempt_uuid`, `observed_remote_oid`, `verifier_type`, `verifier_uuid`. Advances only when `observed_remote_oid` **exactly equals** `requested_head_oid`.
6. On failure: `ticket.git-delivery.fail` with `attempt_uuid`, `actor_uuid`, `failure_class`, `retryable`, `failure_reason`, `required_action` (json). Records a typed reason and a concrete required action / safe resume point. Resume by satisfying `required_action` and starting a new publish-request sequence — do not invent a resume workflow name.

Reads: `ticket.git-delivery.get` (`attempt_uuid`), `ticket.git-delivery.list` (`delivery_uuid`).

**PR handoff:** after confirm, open the PR with `github.pulls.create_exact_pr` (`repository`, `head_ref`, `base_ref`, `expected_head_sha` = the published OID, `title`). That type opens **only after** exact published-head verification. Full GitHub wiring: [orkestia-github](../orkestia-github/SKILL.md).

### 7 · Software-delivery governance

1. `get_workflow_schema("ticket.software-delivery.begin")`. Start with required `work_uuid`, `idempotency_key`. Optional `policy_uuid` (from `ticket.repository-policy.*`) or `policy_snapshot` (json). Creates the **idempotent** delivery lifecycle and an **immutable** policy snapshot. Output: `delivery`, `created`. Copy `delivery_uuid` from `delivery` after you read the keys.
2. Record native evidence: `ticket.software-delivery.evidence-record` with `delivery_uuid`, `sequence`, `idempotency_key`, `kind`, `source_type`. Description enumerates Git, test, PR, check, merge, release, build, migration, rollout, deployment, blocker, recovery — confirm allowed `kind` / `source_type` on the schema before sending. Optional `native_ref`, `head_oid`, `merge_oid`, `conclusion`.
3. Cost: `ticket.software-delivery.cost-reserve` (`idempotency_key`, `category`, `amount_usd`, `source_type`, `source_uuid`; identify the delivery with `delivery_uuid` or `work_uuid`) then `ticket.software-delivery.cost-record` (`idempotency_key`, `category`, `pricing_status`, `source_type`, `source_uuid`, `evidence_digest`). Bundle launch reservations with `cost-reserve-bundle`. Release unused holds with `cost-reservation-release`; read `cost-get`.
4. Controller: `ticket.software-delivery.controller-list` (read-only, oldest-first, no provider coordinates) then `controller-claim-next` (`owner_uuid`, `idempotency_key`). Renew with `controller-claim-renew`; release with `controller-claim-release` (stale owners cannot release a replacement claim).
5. Recovery: `ticket.software-delivery.recovery-inspect` (read-only; `delivery_uuid` or `work_uuid`) returns a digest-bound **closed** action plan in `recovery`. Resume **only** with `ticket.software-delivery.recovery-resume`: `delivery_uuid`, `snapshot_digest`, `idempotency_key`, `expected_failure_class` matching the **exact stored safe-resume state**. Do not resume from a guessed state.
6. Stops: `ticket.software-delivery.mutation-control-activate` (`scope`, `reason`; optional `scope_uuid`, `blocked_operations`) — audited provider-blind stop by organization, actor, repository, runner group, or delivery policy. List / release / evaluate (read-only `mutation-control-evaluate`) as needed.
7. SLOs: `ticket.software-delivery.slo-scan` (read-only) evaluates queue-through-deployment objectives and emits stable alert keys without provider coordinates.

Ordered delivery state changes: `ticket.software-delivery.transition` (`delivery_uuid`, `sequence`, `idempotency_key`, `expected_state`, `target_state`; optional `failure_class`, `safe_resume_state`, `required_action`).

## Object model

| Object | Identity you pass around | Created by |
|---|---|---|
| Ticket | `ticket_uuid` | `ticket.open` or `ticket.ingest.*` |
| Plan | `plan_uuid` | `ticket.plan.propose` |
| Git work | `work_uuid` (from `work`) | `ticket.git-work.begin` |
| Software delivery | `delivery_uuid` (from `delivery`) | `ticket.software-delivery.begin` |
| Publish attempt | `attempt_uuid` (from `attempt`) | `ticket.git-delivery.publish-request` |
| Coding artifact | artifact uuid (from `artifact`) | `ticket.coding-artifact.reserve` |
| Repo policy | `policy_uuid` (from `policy`) | `ticket.repository-policy.create` |
| External binding | `binding_uuid` | `ticket.external.binding.upsert` or ingest |
| Trigger | `trigger_uuid` | `ticket.schedule` |

A ticket may have many git-work items; each work item has at most one software-delivery lifecycle (begin is idempotent on `idempotency_key`). Policy on the repo is versioned and activated separately from a delivery's frozen snapshot.

## Day-to-day reads

All `read_only: true`. Start freely after `whoami()`.

- `ticket.search` — queue; set `hydrate=true` for live source; `include_total=true` when you need a count.
- `ticket.get` — one ticket + optional children + `lifecycle` + `live`.
- `ticket.events` — immutable timeline (`ticket_uuid`; keyset `cursor`).
- `ticket.git-work.get` / `list`, `ticket.git-work.concurrency`.
- `ticket.git-delivery.get` / `list`.
- `ticket.software-delivery.get` (`delivery_uuid` or `work_uuid`; `include_transitions` / `include_evidence`).
- `ticket.software-delivery.cost-get`, `controller-list`, `recovery-inspect`, `recovery-evaluate`, `slo-scan`, `mutation-control-list`.
- `ticket.coding-artifact.get` / `list`, `ticket.repository-policy.get` / `list`.
- `ticket.operator.verify` — status, allowed transitions, optional quiescence, best-effort source hydration (featured=false; operator triage).

## Gotchas

- **Never start** `ticket._scheduler.poll` (internal claim of due triggers). Do not start DAG children `ticket.external.sync.prepare` / `finalize` or `ticket.coding-artifact.available-plan` / `available-commit` — start the parent DAG (`sync.dispatch`, `coding-artifact.available`).
- `ticket.plan.apply` refuses unacknowledged plans. `ticket.plan.reject` is permanent.
- `ticket.git-delivery.push-record` requires the **active broker lease**. `publish-confirm` is exact-OID equality, not "close enough".
- `ticket.software-delivery.recovery-resume` requires the exact stored `snapshot_digest` and `expected_failure_class`. Inspect first.
- `ticket.link` never auto-merges duplicates.
- `ticket.schedule` / `ticket.trigger.cancel` run under the **ticket owner's** authority, not the caller's improvisation.
- Nested uuid keys live inside `work` / `delivery` / `attempt` / `policy` / `artifact` / `recovery` dicts — copy them from the run output; do not invent field names.
- Catalog counts drift. `list_workflow_types(prefix="ticket.")` is authoritative.

## Sibling skills

- [orkestia-mcp-operating-loop](../orkestia-mcp-operating-loop/SKILL.md) — whoami, schema, watch, stuck/retry/resolve.
- [orkestia-github](../orkestia-github/SKILL.md) — `github.pulls.create_exact_pr` after publish-confirm.
- [orkestia-agents](../orkestia-agents/SKILL.md) — sessions that may carry `ticket_uuid` / `ticket_git_work_uuid`.
- [orkestia-staff](../orkestia-staff/SKILL.md) — actors that ingest findings / tool-requests into tickets.
- [orkestia-runners](../orkestia-runners/SKILL.md) — DevKit / runner groups referenced by `git-work.begin` (`runner_group_uuid`).

## Additional resources

- [reference.md](reference.md) — workflow map by subsystem (ledger, ingest/external, plans, git-work, git-delivery, artifacts, software-delivery, repository-policy, operator/reconcile/sync).
- [examples.md](examples.md) — ingest, outbound sync, coding artifacts, repository policy, delivery fail/resume.

Re-discover: `list_workflow_types(prefix="ticket.")`. For one type: `get_workflow_schema("<name>")`.
