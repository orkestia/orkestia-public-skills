---
name: orkestia-tickets
description: Use the Orkestia ticket ledger (ticket.*, 90 types) — open and manage tickets, ingest external signals, gate agent fix plans, run provider-blind git work and exact-OID delivery, and govern software delivery with budgets, evidence, and recovery. Use for any work-tracking or agent-coding-delivery flow.
---

# Orkestia tickets

Tickets are the canonical work ledger where signals from every domain converge, and where agent coding work is governed end-to-end. Five sub-systems share the namespace.

## 1 · Core ledger

`ticket.open` is **the single ingress** for humans and adapters. Required: `kind` (incident/task/info), `title`, `source_type` (lumen_error_group, actor_finding, alert_rule, audit_finding, tool_request, workflow_run, human, api, linear), `owner_type` (human/actor/agent/platform), `owner_uuid`. A stable `source_fingerprint` collapses repeated opens into one ticket (`occurrence_count`). Priority canon: page/priority/routine/deferred (aliases urgent/high/medium/low accepted).

Then: `ticket.transition` (allowed-transition map), `update`, `assign` (+ optional inbox delivery), `comment`, `link` (suggest, never auto-merge), `events` (immutable keyset-paginated timeline), `search`, `get` (hydrated with live source), `reconcile` (source-domain change → suggested/applied status), `schedule` / `trigger.cancel` (recurring triggers fired under the ticket owner's authority).

## 2 · Ingest adapters & external sync

Inbound `ticket.ingest.*`: `linear-issue`, `lumen-error-group`, `alert-rule`, `audit-finding`, `actor-finding`, `tool-request` (staff capability gaps), `external-work-item`. Outbound: `ticket.external.binding.upsert` (relate a ticket to a provider object) and `ticket.external.sync.dispatch` (push updates to the configured provider workflow).

## 3 · Plans — the human gate on agent fixes

```
ticket.plan.propose → ticket.plan.acknowledge → ticket.plan.apply     (apply REFUSES unacknowledged plans)
ticket.plan.reject   # kills an active plan permanently
```

## 4 · Git work, delivery, artifacts (provider-blind)

The coding actor never holds a Git-provider credential.

- `git-work.begin` binds a ticket to one local worktree + full branch ref; `git-work.observe` appends ordered idempotent local Git observations; `git-work.reconcile` blocks drifted work (local HEAD vs last acknowledged head); `git-work.complete` finalizes with native object IDs. Reads: `git-work.get/list`, `git-work.concurrency`.
- Publication runs through a trusted broker: `git-delivery.publish-request` → `claim-next` (broker lease; pins pre-push work to its owning executor unless a portable artifact exists) → `push-record` (requires the active lease) → `publish-confirm` (advances only when the remote ref OID **exactly equals** the requested local head). `git-delivery.fail` records typed reasons + safe resume points.
- **Coding artifacts** (portable Git bundles): `reserve` → `prepare` (freeze manifest/bundle digests + size) → `upload-start` → `available` (provenance/digest/size/session must match) → `verification-claim` / `verification-complete`. Governance: `legal-hold-set`, `expire`, deletion leases (`deletion-claim/-complete/-fail` with object-count and byte evidence).

## 5 · Software-delivery governance (`ticket.software-delivery.*`, 33 types)

- `begin` creates the delivery lifecycle + immutable policy snapshot; `transition` appends ordered typed transitions with blockers and safe-resume evidence; `evidence-record` appends native Git/test/PR/check/merge/release/build/migration/rollout/deployment/blocker/recovery evidence.
- **Cost**: `cost-reserve` / `cost-reserve-bundle` (USD against the policy budget, concurrency-aware), `cost-record` (immutable spend with attribution), `cost-reservation-release`, `cost-reservations-reconcile`, `cost-get`.
- **Controller**: `controller-list` / `controller-claim-next` / `-renew` / `-release` — oldest-first deterministic action claims with crash-recoverable leases.
- **Recovery**: `recovery-inspect` (digest-bound closed action plan), `recovery-resume` (only at the exact stored safe-resume state), `recovery-abandon`, `recovery-evaluate` + `recovery-objective-configure/list/retire` (RPO/RTO), `recovery-drill-plan`.
- **Controls**: `mutation-control-activate/list/release` — audited provider-blind stops by organization, actor, repository, runner group, or delivery policy. `retention-hold-set`; cleanup pipeline (`cleanup-plan/claim-next/complete/fail/minimize/list`); `slo-scan` (queue-through-deployment objectives, stable alert keys).
