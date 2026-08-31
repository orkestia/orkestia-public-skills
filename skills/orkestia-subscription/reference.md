# Subscription — workflow map

Re-list before treating this as complete. Snapshot while writing: `subscription.*` (49), `data.subscription.*` (2). Second-level (from listing): billing 24, actor-rbac-seat 5, retention 3, usage 2, data-governance 1, end-user-seat-pack 1, lumen 1, plan 1, platform 1, trial 1, plus unprefixed siblings (`plan_change`, `checkout`, `cancellation`, `renewal`, `payment_recovery`, `sync`, `seat_change`, `key_provision`, `key_revoke`).

```
whoami()
list_workflow_types(prefix="subscription.")
list_workflow_types(prefix="data.subscription.")
```

Prefer `featured: true`. Checkout outputs a browser URL. Do not dump Stripe product IDs.

## Discover / reads

| Type | Job |
|---|---|
| `subscription.billing.summary` | Billing state, items, entitlements, upcoming invoice, catalog, actions. Optional `identity_app_uuid` |
| `data.subscription.list` | OrganizationSubscription rows (UUID-only) |
| `data.subscription.plan.list` | Active SubscriptionPlan catalog (UUID-only) |
| `subscription.actor-rbac-seat.status` | Paid RBAC availability + consumers |
| `subscription.usage.summary` | Period usage + cost. Optional `period_start`, `period_end`, `include_daily` |

## Platform checkout

| Type | Job |
|---|---|
| `subscription.platform.checkout` | **Featured entry.** Caller: `success_url`, `cancel_url`; optional `selected_price_ref`, `user_seats`, `key_seats`, `idempotency_key`. Output: `checkout_url`, `checkout_workflow_id` |
| `subscription.checkout` | Child/end-to-end Stripe session (`featured: false`). Watch via `checkout_workflow_id`; do not start as the human entry |

## Portal and item/plan change

| Type | Job |
|---|---|
| `subscription.billing.portal-session.create` | Stripe Billing Portal. Caller: `return_url` → `portal_url` |
| `subscription.plan_change` | Featured v2 upgrades/downgrades with proration. Caller: `subscription_uuid`, `current_plan_uuid`, `new_plan_uuid`; optional `proration_behavior`, `require_confirmation` |
| `subscription.billing.item.change` | Absolute `item_code` + `quantity`. Paid increases need `success_url` / `cancel_url` and may return `checkout_url` |
| `subscription.plan.change-with-proration` | DAG (`featured: false`). Caller: `subscription_uuid`, `target_plan`; optional `billing_cycle`, `confirm`, `dry_run`, `idempotency_key` |

## Platform user seats

| Type | Job |
|---|---|
| `subscription.billing.platform-user-seat.checkout` | Buy more. Caller: `success_url`, `cancel_url`; optional `quantity` / `add_seats`, `subscription_uuid` |
| `subscription.billing.platform-user-seat-downgrade.preview` | Names who would be unseated. Caller: `quantity`; optional `selected_membership_uuids`, `use_oldest_fallback` |
| `subscription.billing.platform-user-seat-downgrade.schedule` | Schedule unseats at renewal. Same caller shape as preview |
| `subscription.billing.platform-user-seat-downgrade.cancel` | Cancel pending downgrade. Optional `seat_downgrade_schedule_uuid`, `cancel_reason` |
| `subscription.billing.platform-user-seat-downgrade.apply` | Apply at cut window (`featured: false`) |

## Staff actor / RBAC seats

| Type | Job |
|---|---|
| `subscription.actor-rbac-seat.status` | Availability + consumers |
| `subscription.actor-rbac-seat.resize` | Absolute `paid_rbac_actor_seats` or delta `add_paid_rbac_actor_seats`. **Every reduction:** `confirm_rbac_actor_seat_loss: true` |
| `subscription.actor-rbac-seat.change` | Deprecated alias of `resize` (same confirmation rule) |
| `subscription.billing.actor-seat.checkout` | Stripe Checkout for additional actor seats (`success_url`, `cancel_url`; optional `quantity` / `add_seats`) |
| `subscription.actor-rbac-seat.internal-grant` / `internal-revoke` | Non-Stripe internals (`featured: false`) |

## End-user seat packs

| Type | Job |
|---|---|
| `subscription.billing.end-user-seat-pack.checkout` | **Paid pack.** Caller: `identity_app_uuid`, `pack_size`, `success_url`, `cancel_url` → `checkout_url`. Raises `identity.seat.status` cap |
| `subscription.end-user-seat-pack.checkout` | **Stub** (read-only pending-support). Does not complete checkout |

## Lumen add-ons

Observability product lives under `lumen.*` (`list_workflow_types(prefix="lumen.")`). Billing only:

| Type | Job |
|---|---|
| `subscription.billing.lumen-plan.checkout` | Paid plan. Caller: `plan`, `success_url`, `cancel_url`; optional `retention_days` |
| `subscription.billing.lumen-plan.change` | Change tier |
| `subscription.billing.lumen-plan-downgrade.cancel` | Cancel scheduled plan downgrade |
| `subscription.billing.lumen-plan.apply-downgrade` | Apply after cut (`featured: false`) |
| `subscription.billing.lumen-addon.checkout` / `change` | Entry packs (1M entries/month each) + storage GB |
| `subscription.billing.lumen-addon-downgrade.cancel` | Cancel scheduled addon downgrade |
| `subscription.billing.lumen-addon.apply-downgrade` | Apply after cut (`featured: false`) |
| `subscription.billing.lumen-provisioning.reconcile` | Re-run pending Lumen provisioning (`featured: false`) |
| `subscription.lumen.billing.change` | **Stub** pending-support (read-only) |

## Workflow retention

| Type | Job |
|---|---|
| `subscription.billing.workflow-retention.checkout` | Caller: `retention_days`, `success_url`, `cancel_url`; optional `storage_gb`, `max_retained_workflow_storage_bytes` |
| `subscription.billing.workflow-retention.change` | Change retention / storage / policy |
| `subscription.billing.workflow-retention-downgrade.cancel` | Cancel scheduled downgrade |
| `subscription.billing.workflow-retention.apply-downgrade` | Apply after cut (`featured: false`) |
| `subscription.retention.apply` | Apply configured retention, dry-run capable (`featured: false`) |
| `subscription.retention.billing.change` | **Stub** pending-support |
| `subscription.retention.billing.quote` | **Stub** pending price-model |

## Trial, usage, data-governance

| Type | Job |
|---|---|
| `subscription.trial.convert-and-provision` | DAG (`featured: false`). Caller: `trial_subscription_uuid`, `target_plan`; optional `payment_method_ref`, `seat_count`, `dry_run` |
| `subscription.usage.summary` | Featured usage + cost read |
| `subscription.usage.consolidate` | Snapshot retained storage usage (`featured: false`) |
| `subscription.data-governance.configure` | Org audit/retention policy (`featured: false`) — not Checkout |

## Metering in other namespaces

| Type | Job |
|---|---|
| `runner.hosted-usage-reconcile` | BillableEvent per newly-terminal hosted execution; `max_session_duration_s` |
| `data.agents.budget-status` | Agent budget utilisation |
| `data.agents.cost-by-config` / `cost-by-model` / `cost-period-summary` | Agent cost ledger |
| `ticket.software-delivery.cost-get` | Delivery spend + reservations |
| `ticket.software-delivery.cost-reserve` / `cost-reserve-bundle` / `cost-record` | Reserve / record USD |
| `ticket.software-delivery.cost-reservation-release` / `cost-reservations-reconcile` | Release / reconcile reservations |

Hosted runners and `apphost.site.claim` check subscription as a precondition.

## Internals — not operator entry points (`featured: false`)

`subscription.cancellation`, `subscription.renewal`, `subscription.payment_recovery`, `subscription.sync`, `subscription.seat_change`, `subscription.key_provision`, `subscription.key_revoke`, `subscription.billing.governance.backfill`, plus the `*.apply-downgrade` rows above.

## Stubs — pending-support (read-only)

If `supported` is false, report `unsupported_reason` and use the matching `subscription.billing.*` featured checkout instead:

- `subscription.end-user-seat-pack.checkout`
- `subscription.lumen.billing.change`
- `subscription.retention.billing.change`
- `subscription.retention.billing.quote`
