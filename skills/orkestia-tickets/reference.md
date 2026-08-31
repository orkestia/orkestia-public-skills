# ticket.* reference

Catalog snapshot 2026-08-31. First-level `ticket`: **107** types. Re-verify with `list_workflow_types(prefix="ticket.")`. `organization_uuid` is context-injected on every type below — omit it from `initial_data`.

Do **not** start: `ticket._scheduler.poll` (internal due-trigger poll). Do **not** start DAG children listed as "internal" — start the parent.

Featured unless noted. `read_only` types are safe to start after `whoami()`.

## Core ledger

Single human/adapter ingress is `ticket.open`. Everything else mutates or reads that row.

| Workflow | Role | Required inputs (besides context) |
|---|---|---|
| `ticket.open` | Create or collapse-into a ticket | `kind`, `title`, `source_type`, `owner_type`, `owner_uuid` |
| `ticket.update` | Edit priority, severity, title, body, labels, subject | `ticket_uuid` |
| `ticket.comment` | Append timeline comment | `ticket_uuid`, `body` |
| `ticket.assign` | Set assignee; optional inbox `dispatch` | `ticket_uuid`, `assignee_type`, `assignee_uuid` |
| `ticket.transition` | Move status along the allowed map | `ticket_uuid` + `to_status` or `intent` |
| `ticket.link` | Relate to another ticket/object — **suggest, never auto-merge** | `ticket_uuid`, `link_kind`, `target_type`, `target_uuid` |
| `ticket.schedule` | One-shot or recurring trigger; fires under **ticket owner** authority | `ticket_uuid`, `kind`, `action_workflow_type` |
| `ticket.trigger.cancel` | Pause or cancel a schedule | `trigger_uuid` |
| `ticket.reconcile` | Source-domain state change → suggested (sometimes applied) status | `source_state` (+ `ticket_uuid` or `source_fingerprint`) |
| `ticket.search` | Filtered paginated list; optional `hydrate` | (filters optional) |
| `ticket.get` | Hydrated ticket + children + live source | `ticket_uuid` |
| `ticket.events` | Immutable keyset-paginated timeline | `ticket_uuid` |

**Enums from schemas (do not invent others):**

- `kind`: `incident`, `task`, `info`
- `source_type`: `lumen_error_group`, `actor_finding`, `alert_rule`, `audit_finding`, `tool_request`, `workflow_run`, `human`, `api`, `linear`
- `owner_type` / `assignee_type`: `human`, `actor`, `agent`, `platform`
- **Priority canon:** `page`, `priority`, `routine`, `deferred` (aliases `urgent`/`high`/`medium`/`low`)
- `severity`: `critical`, `high`, `medium`, `low`, `info`
- `status` (search filter): `open`, `triaged`, `in_progress`, `blocked`, `resolved`, `closed`, `ignored`
- `intent`: `start`, `resolve`, `close`, `ignore`, `reopen`
- `link_kind`: `relates_to`, `duplicate_of`, `blocks`, `blocked_by`, `caused_by`, `parent_of`, `child_of`, `source_ref`, `subject_ref` (alias `splits_from`→`child_of`)

Allowed next statuses come from `lifecycle` on `ticket.search` / `ticket.get`. There is no `ticket.allowed_transitions` workflow type (the transition schema mentions that phrase as a discovery hint, not a catalog name).

`ticket.open` outputs `ticket_uuid`, `created`, `status`, `occurrence_count`. Same fingerprint → collapse (`created=false`, `occurrence_count` increments).

## Ingest adapters and external sync (11 types)

Use **ingest** when the payload is already a provider/domain object (Linear issue, Lumen group, alert firing, …). Use **`ticket.open`** when a human or generic adapter is composing `kind`/`title`/`source_type`/`owner_*` itself.

| Workflow | Maps into | Distinct required fields |
|---|---|---|
| `ticket.ingest.linear-issue` | Canonical ticket + binding | none strictly besides context; pass `issue` json and/or `issue_ref` (schema both optional — confirm one is enough on the live schema). Optional `connection_uuid`, `workspace_ref`, `team_ref`, `owner_type`/`owner_uuid`, `allow_existing_binding`, `dispatch` |
| `ticket.ingest.lumen-error-group` | Incident | `error_group_uuid`, `fingerprint`, `title` |
| `ticket.ingest.alert-rule` | Incident | `alert_rule_uuid`, `rule_name`, `condition` |
| `ticket.ingest.audit-finding` | Task | `finding_uuid`, `finding_type`, `rule_key`, `severity`, `status`, `title`, `content_hash` |
| `ticket.ingest.actor-finding` | Task | `finding_type`, `from_actor`, `title` |
| `ticket.ingest.tool-request` | Capability-gap task | `from_actor`, `requested_capability` |
| `ticket.ingest.external-work-item` | Canonical ticket + binding | `provider`, `provider_item_ref`, `title` |

All ingest types return `ticket_uuid`, `created`, `occurrence_count`. Linear and external-work-item also return `binding_uuid`.

**Outbound**

| Workflow | Role | Required |
|---|---|---|
| `ticket.external.binding.upsert` | Relate ticket ↔ provider object | `ticket_uuid`, `provider`, `provider_item_type`, `provider_item_ref` |
| `ticket.external.sync.dispatch` | DAG: push updates to the configured provider workflow | `ticket_uuid`, `provider` |

Internal DAG steps (do not start): `ticket.external.sync.prepare`, `ticket.external.sync.finalize`.

## Plans (4)

| Workflow | Gate | Required |
|---|---|---|
| `ticket.plan.propose` | Attach agent plan; supersedes prior active | `ticket_uuid` |
| `ticket.plan.acknowledge` | **Required** before apply | `plan_uuid` and/or `ticket_uuid` |
| `ticket.plan.apply` | **Refuses** unacknowledged plans | `plan_uuid` and/or `ticket_uuid` |
| `ticket.plan.reject` | Kills proposed/acknowledged plan permanently | `plan_uuid` and/or `ticket_uuid` |

Outputs include `plan_uuid`, `status`, `changed` (propose also `superseded`). Read via `ticket.get` with `include=["plans"]`.

## Git work (7) — provider-blind

Coding actor never holds a Git-provider credential.

| Workflow | Role | Required |
|---|---|---|
| `ticket.git-work.begin` | Bind ticket to one worktree + full branch ref | `ticket_uuid`, `repository_uuid` |
| `ticket.git-work.observe` | Ordered idempotent local Git observation | `work_uuid`, `sequence`, `idempotency_key`, `ref_name` |
| `ticket.git-work.reconcile` | Block if local HEAD ≠ last acknowledged HEAD | `work_uuid` |
| `ticket.git-work.complete` | Finalize with native OIDs | `work_uuid`, `outcome` (`merged` \| `completed` \| `abandoned`) |
| `ticket.git-work.get` | Read binding + optional observations | `work_uuid` |
| `ticket.git-work.list` | Bindings + leases on a ticket | `ticket_uuid` |
| `ticket.git-work.concurrency` | Peek repo/target concurrency without claiming | `repository_uuid`, `branch_ref` |

`begin` may omit `branch_ref` (derived collision-proof `refs/heads/*`), `target_ref` (repo default vs active policy `allowed_target_refs`), `base_oid` (last recorded head). `head_oid` is resume-only and is **not** derived. Pair `executor_uuid` + `worktree_uuid` for pre-bound work, or `runner_group_uuid` for a cloudless DevKit claim.

## Git delivery (7) — exact-OID broker

| Workflow | Role | Required |
|---|---|---|
| `ticket.git-delivery.publish-request` | Request publish of clean acknowledged head | `delivery_uuid`, `sequence`, `idempotency_key`, `requested_head_oid`, `destination_ref`, `policy_digest` |
| `ticket.git-delivery.claim-next` | Broker lease; pin pre-push work unless portable artifact exists | `broker_uuid`, `lease_uuid` |
| `ticket.git-delivery.push-record` | Record push; **needs active lease** | `attempt_uuid`, `broker_uuid`, `lease_uuid`, `outcome` |
| `ticket.git-delivery.publish-confirm` | Advance iff remote OID **exactly equals** requested local head | `attempt_uuid`, `observed_remote_oid`, `verifier_type`, `verifier_uuid` |
| `ticket.git-delivery.fail` | Typed fail + required action / resume point | `attempt_uuid`, `actor_uuid`, `failure_class`, `retryable`, `failure_reason`, `required_action` |
| `ticket.git-delivery.get` | One attempt | `attempt_uuid` |
| `ticket.git-delivery.list` | Attempts newest first | `delivery_uuid` |

After confirm, open the PR with `github.pulls.create_exact_pr` (`repository`, `head_ref`, `base_ref`, `expected_head_sha`, `title`) — see orkestia-github.

## Coding artifacts (15) — portable Git bundles

Public sequence: **reserve → prepare → upload-start → available → verification-claim / verification-complete**.

| Workflow | Role | Required |
|---|---|---|
| `ticket.coding-artifact.reserve` | Reserve bundle identity bound to work/session/execution/lease/OIDs | `repository_uuid`, `work_uuid`, `idempotency_key`, `object_format`, `base_oid`, `head_oid`, `session_uuid`, `execution_uuid`, `workspace_lease_uuid`, `expires_at` |
| `ticket.coding-artifact.prepare` | Freeze manifest digest, bundle digest, size | `artifact_uuid`, `manifest_sha256`, `artifact_sha256`, `size_bytes`, `object_count`, `uncompressed_bytes` |
| `ticket.coding-artifact.upload-start` | Advance to uploading **without** exposing a storage URL | `artifact_uuid` |
| `ticket.coding-artifact.available` | DAG: mark available only when provenance, digest, size, session match | `artifact_uuid`, `storage_object_uuid` |
| `ticket.coding-artifact.verification-claim` | Claim exact-OID verification for a trusted importer | `artifact_uuid`, `verifier_uuid`, `lease_uuid`, `lease_seconds` |
| `ticket.coding-artifact.verification-complete` | Compare importer observations to frozen digest/size/format/OIDs | `artifact_uuid`, `verifier_uuid`, `lease_uuid`, `manifest_sha256`, `artifact_sha256`, `size_bytes`, `object_count`, `uncompressed_bytes`, `object_format`, `base_oid`, `head_oid` |
| `ticket.coding-artifact.legal-hold-set` | Set/clear hold before physical deletion | `artifact_uuid`, `enabled`, `reason` |
| `ticket.coding-artifact.expire` | Advance elapsed artifact to expired (hold + monotonic rules) | `artifact_uuid` |
| `ticket.coding-artifact.deletion-claim` | Lease physical deletion; skips holds and active janitors | `worker_uuid`, `lease_uuid`, `lease_seconds` |
| `ticket.coding-artifact.deletion-complete` | Deleted only with exact object-count and byte evidence | `artifact_uuid`, `worker_uuid`, `lease_uuid`, `deleted_object_count`, `deleted_bytes` |
| `ticket.coding-artifact.deletion-fail` | Release or terminally fail a deletion lease | `artifact_uuid`, `worker_uuid`, `lease_uuid`, `retryable`, `failure_reason` |
| `ticket.coding-artifact.get` | One artifact | `artifact_uuid` |
| `ticket.coding-artifact.list` | Bounded metadata for one git-work item | `work_uuid` |

Internal DAG children of `available` (do not start): `ticket.coding-artifact.available-plan`, `ticket.coding-artifact.available-commit`.

## Software-delivery governance (40)

Entry: `ticket.software-delivery.begin` (`work_uuid`, `idempotency_key`; optional `policy_uuid` or `policy_snapshot`). Freezes an **immutable** policy snapshot for that work item.

### Lifecycle and evidence

| Workflow | Role | Required |
|---|---|---|
| `ticket.software-delivery.begin` | Idempotent delivery + policy snapshot | `work_uuid`, `idempotency_key` |
| `ticket.software-delivery.transition` | Ordered typed transition + blocker / safe-resume | `delivery_uuid`, `sequence`, `idempotency_key`, `expected_state`, `target_state` |
| `ticket.software-delivery.evidence-record` | Native Git/test/PR/check/merge/release/build/migration/rollout/deployment/blocker/recovery evidence | `delivery_uuid`, `sequence`, `idempotency_key`, `kind`, `source_type` |
| `ticket.software-delivery.get` | Delivery + optional transitions/evidence | `delivery_uuid` or `work_uuid` |

Confirm allowed `kind` / `source_type` / state names on the live schema — they are not enumerated as closed lists on the input fields.

### Cost

| Workflow | Role | Required |
|---|---|---|
| `ticket.software-delivery.cost-reserve` | USD against policy budget (concurrency-aware) | `idempotency_key`, `category`, `amount_usd`, `source_type`, `source_uuid` |
| `ticket.software-delivery.cost-reserve-bundle` | Model + optional compute under one lock | (see schema — do not guess field names) |
| `ticket.software-delivery.cost-record` | Immutable spend with attribution | `idempotency_key`, `category`, `pricing_status`, `source_type`, `source_uuid`, `evidence_digest` |
| `ticket.software-delivery.cost-reservation-release` | Drop an active hold without recording spend | (see schema) |
| `ticket.software-delivery.cost-reservations-reconcile` | Reconcile holds only with a fresh recovery snapshot + terminal owner proof | (see schema) |
| `ticket.software-delivery.cost-get` | Spend, reservations, budget, breakdowns | (read-only; identify delivery on schema) |

Identify the delivery on cost writers with `delivery_uuid` and/or `work_uuid` (both optional on reserve/record — pass at least one).

### Controller

| Workflow | Role | Required |
|---|---|---|
| `ticket.software-delivery.controller-list` | Oldest-first actions; no provider coordinates | (read-only) |
| `ticket.software-delivery.controller-claim-next` | Claim one action; crash-recoverable lease | `owner_uuid`, `idempotency_key` |
| `ticket.software-delivery.controller-claim-renew` | Renew only when owner, state, action still match | (see schema) |
| `ticket.software-delivery.controller-claim-release` | Release after no-op/handoff; stale owners cannot release a replacement | (see schema) |

### Recovery

| Workflow | Role | Required |
|---|---|---|
| `ticket.software-delivery.recovery-inspect` | Digest-bound **closed** action plan | `delivery_uuid` or `work_uuid` |
| `ticket.software-delivery.recovery-resume` | Resume **only** at exact stored safe-resume state | `delivery_uuid`, `snapshot_digest`, `idempotency_key`, `expected_failure_class` |
| `ticket.software-delivery.recovery-abandon` | Abandon with retained evidence + cleanup acknowledgement | (see schema) |
| `ticket.software-delivery.recovery-evaluate` | Current RPO/RTO, retention, restore-drill blockers | (read-only) |
| `ticket.software-delivery.recovery-objective-configure` | Immutable provider-blind RPO/RTO objective | (see schema) |
| `ticket.software-delivery.recovery-objective-list` | List objectives; no physical coordinates | (read-only) |
| `ticket.software-delivery.recovery-objective-retire` | Retire one objective without deleting evidence | (see schema) |
| `ticket.software-delivery.recovery-drill-plan` | Isolated restore drill for one recovery point | (featured) |

Non-featured drill internals (do not start unless a schema you just read names them as the entry): `recovery-drill-start`, `recovery-drill-complete`, `recovery-drill-fail`, `recovery-point-record`.

### Mutation control, retention, cleanup, SLO

| Workflow | Role |
|---|---|
| `ticket.software-delivery.mutation-control-activate` | Audited stop: `scope` + `reason` (optional `scope_uuid`, `blocked_operations`). Scopes described as organization, actor, repository, runner group, or delivery policy |
| `ticket.software-delivery.mutation-control-list` | List controls + audit state |
| `ticket.software-delivery.mutation-control-release` | Release an exact control |
| `ticket.software-delivery.mutation-control-evaluate` | Read-only decision; featured=false |
| `ticket.software-delivery.retention-hold-set` | Set/clear org-scoped delivery retention hold |
| `ticket.software-delivery.cleanup-plan` | Deterministic cleanup tasks for terminal deliveries past retention |
| `ticket.software-delivery.cleanup-claim-next` | Claim one due cleanup task |
| `ticket.software-delivery.cleanup-complete` | Acknowledge absent/deleted/minimized/purged without copying deleted payloads |
| `ticket.software-delivery.cleanup-fail` | Typed cleanup failure for retry |
| `ticket.software-delivery.cleanup-minimize` | Minimize one claim; payload-free tombstone |
| `ticket.software-delivery.cleanup-list` | List cleanup tasks; no credentials or deleted payloads |
| `ticket.software-delivery.slo-scan` | Queue-through-deployment objectives; stable alert keys |

Internal cleanup children (do not start): `cleanup-execution-log-finalize`, `cleanup-execution-log-renew`.

## Repository policy (5)

When an org binds **delivery/git policy to a repository** — allowed target refs, required checks/commands, approval/merge/release/build/deployment/evidence/retention/retry/cost budgets — use this subsystem. `ticket.software-delivery.begin` then snapshots `policy_uuid` (or an inline `policy_snapshot`) immutably onto that delivery.

| Workflow | Role | Required |
|---|---|---|
| `ticket.repository-policy.create` | Create an **immutable** provider-blind policy version | `repository_uuid`, `version`, `allowed_target_refs`, `work_ref_policy`, `required_commands`, `required_checks`, `approval_policy`, `merge_policy`, `release_policy`, `build_policy`, `deployment_policy`, `evidence_policy`, `retry_budget`, `cost_budget` (optional `retention_policy`) |
| `ticket.repository-policy.activate` | Activate one version | `repository_uuid`, `policy_uuid` |
| `ticket.repository-policy.retire` | Retire one version | `repository_uuid`, `policy_uuid` |
| `ticket.repository-policy.get` | One policy (`policy_uuid` optional → current/active) | `repository_uuid` |
| `ticket.repository-policy.list` | Versions newest first; optional `status` | `repository_uuid` |

JSON blobs (`work_ref_policy`, `*_policy`, `retry_budget`, `cost_budget`) are not enumerated on the input schema — `get_workflow_schema("ticket.repository-policy.create")` before filling them. Do not invent nested keys.

`git-work.begin` derives `target_ref` against the active policy's `allowed_target_refs`; a runner refuses an assignment that names no target.

## Operator, reconcile sweeps, sync, scheduler

| Workflow | featured | Role |
|---|---|---|
| `ticket.operator.verify` | false | Status, allowed transitions, optional quiescence, best-effort source hydration |
| `ticket.operator.transition-batch` | false | `ticket.transition` semantics on many tickets; per-item error isolation |
| `ticket.reconcile.orphaned` | false | Sweep non-terminal tickets with a claim label but no pipeline stage; flag; opt-in re-inject |
| `ticket.reconcile.sweep` | false | Sweep source-backed tickets whose fault went quiet; suggest retirement |
| `ticket.sync.software-delivery-slo-finding` | false | Sync a sanitized SLO finding into a stable incident |
| `ticket._scheduler.poll` | false | **Do not start** — claims due triggers under the creator's authority |

## Second-level counts (2026-08-31)

`ticket.coding-artifact` 15 · `ticket.external` 4 · `ticket.git-delivery` 7 · `ticket.git-work` 7 · `ticket.ingest` 7 · `ticket.operator` 2 · `ticket.plan` 4 · `ticket.reconcile` 2 · `ticket.repository-policy` 5 · `ticket.software-delivery` 40 · `ticket.sync` 1 · `ticket.trigger` 1 · `ticket._scheduler` 1. Remaining types sit on `ticket.*` itself (open, get, search, …).
