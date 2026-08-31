# ticket.* examples

Placeholders like `<ticket_uuid>` are values copied from a prior run. Never pass `organization_uuid`. Always `whoami()` then `get_workflow_schema` for the type you are about to start.

Nested identities (`work`, `delivery`, `attempt`, `policy`, `artifact`) are dicts in terminal output — copy the uuid field you actually see into the next step's `*_uuid`. Do not invent nested key names.

---

## 1 · Ingest a Linear issue (vs `ticket.open`)

**When:** the work already exists in Linear (or another tracker). Prefer `ticket.ingest.linear-issue` so provenance, binding, and collapse are adapter-owned.

**When not:** a human is composing the ticket themselves → `ticket.open` with `source_type="human"` (SKILL.md recipe 1).

```
whoami()
get_workflow_schema("ticket.ingest.linear-issue")
start_workflow("ticket.ingest.linear-issue", initial_data={
  "issue_ref": "LIN-1842",
  "connection_uuid": "<linear_connection_uuid>",
  "dispatch": false
})
watch_workflow("<workflow_id>")
```

Optional: pass `issue` (json) instead of or besides `issue_ref`; `workspace_ref` / `team_ref`; `owner_type` / `owner_uuid`; `allow_existing_binding`.

Outputs: `ticket_uuid`, `created`, `occurrence_count`, `binding_uuid`, `issue_ref`, `warnings`.

Same Linear issue ingested again collapses (`created=false`, `occurrence_count` increments) rather than opening a duplicate — analogous to `source_fingerprint` on `ticket.open`.

Hydrate: `start_workflow("ticket.get", initial_data={"ticket_uuid": "<ticket_uuid>", "include": ["links"]})`.

---

## 2 · Ingest Lumen / alert / actor finding

These adapters map domain objects into incidents or tasks. Use them instead of hand-building `ticket.open` with a matching `source_type`.

**Lumen error group** (incident; required `error_group_uuid`, `fingerprint`, `title`):

```
start_workflow("ticket.ingest.lumen-error-group", initial_data={
  "error_group_uuid": "<error_group_uuid>",
  "fingerprint": "TypeError:x at y",
  "title": "TypeError in checkout",
  "severity": "high",
  "group_status": "open"
})
```

`group_status="regressed"` vetoes automatic retirement on later reconcile sweeps.

**Alert-rule firing** (incident; required `alert_rule_uuid`, `rule_name`, `condition`):

```
start_workflow("ticket.ingest.alert-rule", initial_data={
  "alert_rule_uuid": "<alert_rule_uuid>",
  "rule_name": "error-rate-p95",
  "condition": "p95 > 5%",
  "title": "Checkout error rate",
  "dedup_key": "checkout-p95"
})
```

Firings that share `dedup_key` append to one ticket (`occurrence_count`). Omit `dedup_key` to default to the fault signature.

**Actor finding** (task; required `finding_type`, `from_actor`, `title`) — Staff actors, see orkestia-staff:

```
start_workflow("ticket.ingest.actor-finding", initial_data={
  "finding_type": "<finding_type>",
  "from_actor": "<actor_uuid>",
  "title": "N+1 in invoice list",
  "severity": "medium"
})
```

Confirm `finding_type` on `get_workflow_schema("ticket.ingest.actor-finding")` — it is a required string, not a closed enum on the schema.

**Tool-request** (capability-gap task): `ticket.ingest.tool-request` with `from_actor`, `requested_capability`.

**Audit finding:** `ticket.ingest.audit-finding` with `finding_uuid`, `finding_type`, `rule_key`, `severity`, `status`, `title`, `content_hash`.

**Generic tracker item:** `ticket.ingest.external-work-item` with `provider`, `provider_item_ref`, `title`.

After ingest, operate the ticket with SKILL.md recipe 1 (`comment` / `assign` / `transition`). Source quieted? `ticket.reconcile` with `source_state` (and `ticket_uuid` or `source_fingerprint`).

---

## 3 · Outbound: bind + sync to the provider

Ingest creates a binding for Linear/external-work-item. For a ticket that originated in Orkestia (`ticket.open`) and must appear in Linear/GitHub/Jira/Asana:

```
get_workflow_schema("ticket.external.binding.upsert")
start_workflow("ticket.external.binding.upsert", initial_data={
  "ticket_uuid": "<ticket_uuid>",
  "provider": "linear",
  "provider_item_type": "<provider_item_type>",
  "provider_item_ref": "LIN-1842",
  "provider_item_key": "LIN-1842"
})
```

Required: `ticket_uuid`, `provider`, `provider_item_type`, `provider_item_ref`. Optional `sync_direction` / `authoritative_side` — confirm allowed values on the schema before sending (`dispatch` DAG steps exist for `linear`, `jira`, `asana`, `github`).

Then dispatch (DAG — start this, not `prepare`/`finalize`):

```
get_workflow_schema("ticket.external.sync.dispatch")
start_workflow("ticket.external.sync.dispatch", initial_data={
  "ticket_uuid": "<ticket_uuid>",
  "provider": "linear",
  "connection_uuid": "<linear_connection_uuid>",
  "dry_run": true
})
```

Optional `mode`, `sync_fields`, `comment`, `idempotency_key`. First run with `dry_run=true`, inspect `warnings` / `provider_result`, then repeat with `dry_run` omitted or false.

Do not start `ticket.external.sync.prepare` or `ticket.external.sync.finalize`.

---

## 4 · Coding artifact (portable Git bundle)

Use when publication must move a frozen bundle across executors (claim-next will not pin pre-push work to the original executor if an exact portable artifact is available).

```
# 1. Reserve identity (copy artifact uuid from output `artifact`)
get_workflow_schema("ticket.coding-artifact.reserve")
start_workflow("ticket.coding-artifact.reserve", initial_data={
  "repository_uuid": "<repository_uuid>",
  "work_uuid": "<work_uuid>",
  "idempotency_key": "artifact-1",
  "object_format": "<object_format>",
  "base_oid": "<base_oid>",
  "head_oid": "<head_oid>",
  "session_uuid": "<session_uuid>",
  "execution_uuid": "<execution_uuid>",
  "workspace_lease_uuid": "<workspace_lease_uuid>",
  "expires_at": "2026-09-07T00:00:00Z",
  "delivery_uuid": "<delivery_uuid>"
})

# 2. Freeze digests + size
start_workflow("ticket.coding-artifact.prepare", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "manifest_sha256": "<manifest_sha256>",
  "artifact_sha256": "<artifact_sha256>",
  "size_bytes": 1048576,
  "object_count": 42,
  "uncompressed_bytes": 4194304
})

# 3. Advance to uploading (no storage URL returned)
start_workflow("ticket.coding-artifact.upload-start", initial_data={
  "artifact_uuid": "<artifact_uuid>"
})

# 4. Parent DAG — not available-plan / available-commit
start_workflow("ticket.coding-artifact.available", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "storage_object_uuid": "<storage_object_uuid>"
})

# 5. Trusted importer verification
start_workflow("ticket.coding-artifact.verification-claim", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "verifier_uuid": "<verifier_uuid>",
  "lease_uuid": "<lease_uuid>",
  "lease_seconds": 300
})
start_workflow("ticket.coding-artifact.verification-complete", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "verifier_uuid": "<verifier_uuid>",
  "lease_uuid": "<lease_uuid>",
  "manifest_sha256": "<manifest_sha256>",
  "artifact_sha256": "<artifact_sha256>",
  "size_bytes": 1048576,
  "object_count": 42,
  "uncompressed_bytes": 4194304,
  "object_format": "<object_format>",
  "base_oid": "<base_oid>",
  "head_oid": "<head_oid>"
})
```

**Legal hold** (before any deletion):

```
start_workflow("ticket.coding-artifact.legal-hold-set", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "enabled": true,
  "reason": "litigation-hold"
})
```

**Expire** elapsed artifacts (`ticket.coding-artifact.expire` with `artifact_uuid`) then deletion lease:

```
start_workflow("ticket.coding-artifact.deletion-claim", initial_data={
  "worker_uuid": "<worker_uuid>",
  "lease_uuid": "<lease_uuid>",
  "lease_seconds": 300,
  "artifact_uuid": "<artifact_uuid>"
})
start_workflow("ticket.coding-artifact.deletion-complete", initial_data={
  "artifact_uuid": "<artifact_uuid>",
  "worker_uuid": "<worker_uuid>",
  "lease_uuid": "<lease_uuid>",
  "deleted_object_count": 3,
  "deleted_bytes": 1048576
})
```

Complete **only** with exact object-count and byte evidence. On failure: `ticket.coding-artifact.deletion-fail` (`retryable`, `failure_reason`). Reads: `ticket.coding-artifact.get` / `list` (`work_uuid`).

Pass `artifact_uuid` into `ticket.git-delivery.publish-request` so claim-next can use the portable bundle.

---

## 5 · Bind repository delivery policy

When an org wants git-work and software-delivery to honor **this repo's** allowed targets, required checks, budgets, and retention — create a version, activate it, then pass `policy_uuid` into `ticket.software-delivery.begin`.

```
whoami()
list_workflow_types(prefix="ticket.repository-policy.")
get_workflow_schema("ticket.repository-policy.create")
```

Fill JSON policy blobs from that schema. Do not invent nested keys. A minimal start (blob shapes must match the live schema):

```
start_workflow("ticket.repository-policy.create", initial_data={
  "repository_uuid": "<repository_uuid>",
  "version": 1,
  "allowed_target_refs": ["refs/heads/main"],
  "work_ref_policy": {},
  "required_commands": [],
  "required_checks": [],
  "approval_policy": {},
  "merge_policy": {},
  "release_policy": {},
  "build_policy": {},
  "deployment_policy": {},
  "evidence_policy": {},
  "retry_budget": {},
  "cost_budget": {}
})
```

Copy `policy_uuid` from output `policy`, then:

```
start_workflow("ticket.repository-policy.activate", initial_data={
  "repository_uuid": "<repository_uuid>",
  "policy_uuid": "<policy_uuid>"
})
```

Reads: `ticket.repository-policy.get` / `list` (`repository_uuid`). Retire a version with `ticket.repository-policy.retire` (same two fields).

Then git-work (SKILL.md recipe 4) and:

```
start_workflow("ticket.software-delivery.begin", initial_data={
  "work_uuid": "<work_uuid>",
  "idempotency_key": "delivery-1",
  "policy_uuid": "<policy_uuid>"
})
```

That begin call freezes an **immutable snapshot**. Later `activate` of a newer policy version does not rewrite in-flight deliveries. `git-work.begin` checks `target_ref` against the **active** policy's `allowed_target_refs`.

---

## 6 · Git-delivery fail and typed resume

Happy path is SKILL.md recipe 5. When the broker push or confirm cannot advance:

```
get_workflow_schema("ticket.git-delivery.fail")
start_workflow("ticket.git-delivery.fail", initial_data={
  "attempt_uuid": "<attempt_uuid>",
  "actor_uuid": "<broker_or_operator_uuid>",
  "lease_uuid": "<lease_uuid>",
  "failure_class": "<failure_class from attempt or inspect>",
  "retryable": true,
  "failure_reason": "<failure_reason>",
  "required_action": {}
})
```

Fill `required_action` and `failure_class` by copying from `ticket.git-delivery.get` / `ticket.software-delivery.recovery-inspect`. They are **not** a closed list on the schema — do not invent class names or action keys.

Then:

1. `ticket.git-delivery.get` (`attempt_uuid`) and/or `ticket.software-delivery.recovery-inspect` (`delivery_uuid`) — inspect the closed plan.
2. Satisfy `required_action` (re-observe local Git, fix lease, produce artifact, …).
3. If the delivery is blocked: `ticket.software-delivery.recovery-resume` with `delivery_uuid`, `snapshot_digest`, `idempotency_key`, `expected_failure_class` **exactly** as stored. Wrong digest/class is refused.
4. New `ticket.git-delivery.publish-request` with a new `sequence` / `idempotency_key` and the current `requested_head_oid`.
5. Broker `claim-next` → `push-record` (lease required) → `publish-confirm` (remote OID **exactly equals** requested head).
6. `github.pulls.create_exact_pr` with `expected_head_sha` equal to that published OID (orkestia-github).
