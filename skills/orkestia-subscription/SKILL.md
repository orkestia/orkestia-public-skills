---
name: orkestia-subscription
description: >-
  Manage how Orkestia customers pay through Stripe-backed subscription workflows
  — platform checkout, billing summary and portal, plan and item changes with
  proration, seats (platform users, staff actor/RBAC, end-user packs), Lumen and
  workflow-retention add-ons, usage metering, trials, and data-governance. Use
  for any billing, checkout, seat, plan, add-on, portal, or metering question.
---

# Orkestia subscription

All customer billing is Stripe-backed and workflow-driven under `subscription.*`. **Checkout** workflows return a URL to open in a browser. **Change** workflows mutate quantities with proration. Scheduled **downgrades** can be previewed and cancelled before renewal.

Do not dump a Stripe product catalog. Read live items from `subscription.billing.summary` (and `data.subscription.list` / `data.subscription.plan.list`). Confirm every caller field with `get_workflow_schema`.

Catalog counts move. Re-list:

```
whoami()
list_workflow_types(prefix="subscription.")
list_workflow_types(prefix="data.subscription.")
```

Do **not** pass `organization_uuid` in `initial_data` unless the schema declares it and it is not context-injected.

## When to load

Load this skill when the user wants to subscribe, open a billing portal, change plan or quantity, add or reduce seats, buy Lumen or workflow-retention add-ons, inspect usage, convert a trial, or configure data-governance retention. Load it when another domain is blocked on a paid precondition (`apphost.site.claim`, hosted runners).

Use `orkestia-mcp-operating-loop` for the run loop. Seat packs for **app customers** continue in `orkestia-app-platform`. Staff actor seats continue in `orkestia-staff`. Observability product (not just billing) is `list_workflow_types(prefix="lumen.")` — there is no dedicated Lumen skill.

## Use cases

1. Start platform checkout and open `checkout_url`.
2. Billing summary + Stripe portal session for self-service.
3. Change plan / item quantity with proration.
4. Platform user seats: buy more; preview / schedule / cancel a downgrade (preview names who would be unseated).
5. Staff actor/RBAC seats — every **reduction** needs explicit destructive-loss confirmation.
6. End-user seat packs (raises `identity.seat.status` cap).
7. Lumen plan/addon and workflow-retention add-ons; cancel a scheduled downgrade.
8. Where usage is metered (hosted runners, agents cost ledger, delivery cost).
9. Newer surfaces: trial, usage summary, data-governance, `subscription.plan.*` — plus status/quote stubs that do **not** complete checkout.

## How to recipes

Assume `whoami()` already ran. Featured checkouts always return a browser URL (`checkout_url` or `portal_url`). Tell the user to open it; do not pretend payment finished because the wrapper workflow completed.

### 1. Start platform checkout

Canonical paid platform subscription (featured):

1. `get_workflow_schema("subscription.platform.checkout")`.
2. `start_workflow("subscription.platform.checkout", { "success_url": "https://<app>/billing/success", "cancel_url": "https://<app>/billing/cancel" })`.
   Optional caller fields: `selected_price_ref` (billing cycle — take from summary/schema, do not invent), `user_seats`, `key_seats`, `idempotency_key`.
3. Watch. Open `checkout_url` in a browser. Keep `checkout_workflow_id` and watch that child (`subscription.checkout`) until payment activates.
4. Output also includes `plan_uuid`, `platform_plan_name`, `pending_subscription_uuid`, `next_action`.

Do not start `subscription.checkout` yourself as the entry point (`featured: false`). The platform wrapper starts it.

### 2. Billing summary and self-service portal

1. `start_workflow("subscription.billing.summary", {})` — optional `identity_app_uuid` for the end-user seat slice. Read `platform_subscription`, `items`, `entitlements`, `upcoming_invoice`, `catalog`, `actions`. Use `items` as the source of `item_code` values for quantity changes. Do not print a guessed Stripe catalog.
2. Portal: `get_workflow_schema("subscription.billing.portal-session.create")` then `start_workflow("subscription.billing.portal-session.create", { "return_url": "https://<app>/billing" })`. Open `portal_url` in a browser.

### 3. Change plan or item quantity (proration)

**Plan (featured v2):**

1. Resolve the row: `data.subscription.list` (UUID-only) and current/new plan UUIDs from `data.subscription.plan.list` or summary — do not invent plan names.
2. `get_workflow_schema("subscription.plan_change")`.
3. `start_workflow("subscription.plan_change", { "subscription_uuid": "<uuid>", "current_plan_uuid": "<uuid>", "new_plan_uuid": "<uuid>" })`. Optional: `proration_behavior` (`create_prorations` | `none` | `always_invoice`), `require_confirmation` (schema default true). Watch for `proration_amount` / `proration_details` and confirmation fields.

**Item quantity:**

```
start_workflow("subscription.billing.item.change", {
  "item_code": "<from billing.summary items>",
  "quantity": <absolute integer>
})
```

Optional: `subscription_uuid`, `proration_behavior`, `success_url` / `cancel_url` (required for paid increases — open any returned `checkout_url`), `selected_membership_uuids` / `use_oldest_fallback` for user-seat downgrades.

DAG alternative (not featured): `subscription.plan.change-with-proration` (`subscription_uuid`, `target_plan`; optional `billing_cycle`, `confirm`, `dry_run`, `idempotency_key`). Prefer featured `subscription.plan_change` unless the schema on the DAG is what you need.

### 4. Platform user seats

**Buy more:**

```
start_workflow("subscription.billing.platform-user-seat.checkout", {
  "success_url": "https://<app>/billing/success",
  "cancel_url": "https://<app>/billing/cancel"
})
```

Optional `quantity` (absolute) or `add_seats` (delta), `subscription_uuid`. Open `checkout_url`.

**Downgrade below active usage** — preview names who would be unseated:

1. `subscription.billing.platform-user-seat-downgrade.preview` (`quantity`; optional `selected_membership_uuids`, `use_oldest_fallback`). Read `candidates`, `selected_members`, `default_oldest_members`, `seats_to_remove`, `requires_confirmation`.
2. Confirm the named members with the user.
3. `subscription.billing.platform-user-seat-downgrade.schedule` with the same `quantity` and the chosen `selected_membership_uuids`. Applies at renewal (`effective_at`).
4. Abort before renewal: `subscription.billing.platform-user-seat-downgrade.cancel` (optional `seat_downgrade_schedule_uuid`, `cancel_reason`).

Do not start `…downgrade.apply` (`featured: false`) as an operator shortcut.

### 5. Staff actor / RBAC seats

Every **reduction** requires explicit destructive-loss confirmation (`confirm_rbac_actor_seat_loss: true`). Reductions may immediately revoke Staff actor RBAC tokens. Full workforce model: `orkestia-staff`.

- Status: `subscription.actor-rbac-seat.status`.
- Resize: `subscription.actor-rbac-seat.resize` with `paid_rbac_actor_seats` (absolute) or `add_paid_rbac_actor_seats` (delta). Increases may return `checkout_url` / `portal_url` — open it. For a reduction you **must** pass `confirm_rbac_actor_seat_loss: true` after showing `rbac_actor_seats_to_revoke` / confirmation from a prior read or dry schema check.
- Dedicated checkout for additional actor seats: `subscription.billing.actor-seat.checkout` (`success_url`, `cancel_url`; optional `quantity` / `add_seats`).
- `subscription.actor-rbac-seat.change` is a deprecated alias of `resize` with the same confirmation rule.

### 6. End-user seat packs

Raises the app-platform cap that `identity.seat.status` reads. Point to `orkestia-app-platform` for invite/create/disable.

```
start_workflow("subscription.billing.end-user-seat-pack.checkout", {
  "identity_app_uuid": "<app>",
  "pack_size": <integer>,
  "success_url": "https://<app>/billing/success",
  "cancel_url": "https://<app>/billing/cancel"
})
```

Open `checkout_url`. **Stub:** `subscription.end-user-seat-pack.checkout` is read-only pending-support (`supported` / `unsupported_reason`). It does not complete checkout.

### 7. Lumen and workflow-retention add-ons

Do not invent plan codes. Take `plan` / quantities from `subscription.billing.summary` or the schema.

**Lumen billing** (observability product is `lumen.*` — `list_workflow_types(prefix="lumen.")`):

- Plan: `subscription.billing.lumen-plan.checkout` (`plan`, `success_url`, `cancel_url`; optional `retention_days`) → open `checkout_url`. Change: `subscription.billing.lumen-plan.change`. Cancel a scheduled plan downgrade: `subscription.billing.lumen-plan-downgrade.cancel`.
- Add-ons (entry packs of 1M entries/month each, and storage GB): `subscription.billing.lumen-addon.checkout` / `change`. Cancel scheduled addon downgrade: `subscription.billing.lumen-addon-downgrade.cancel`.

**Workflow retention:**

- `subscription.billing.workflow-retention.checkout` (`retention_days`, `success_url`, `cancel_url`; optional `storage_gb`, `max_retained_workflow_storage_bytes`).
- Change: `subscription.billing.workflow-retention.change`. Cancel scheduled downgrade: `subscription.billing.workflow-retention-downgrade.cancel`.

**Stubs (do not pretend they bill):** `subscription.lumen.billing.change`, `subscription.retention.billing.change`, `subscription.retention.billing.quote` — read-only pending-support / pending price-model. Use the `subscription.billing.*` featured checkouts instead.

### 8. Where usage is metered

Consumption is written by other domains, not a hidden Stripe meter:

| Source | What it does |
|---|---|
| `runner.hosted-usage-reconcile` | One **BillableEvent** per newly-terminal Orkestia-hosted execution (duration); enforces org `max_session_duration_s`. See `orkestia-runners`. |
| `data.agents.budget-status`, `data.agents.cost-by-config` / `cost-by-model` / `cost-period-summary` | Agent session cost ledger. See `orkestia-agents`. |
| `ticket.software-delivery.cost-reserve` / `cost-reserve-bundle` / `cost-record` / `cost-get` / `cost-reservation-release` / `cost-reservations-reconcile` | Delivery USD against policy budgets. See `orkestia-tickets`. |

Subscription state is a **precondition** for `apphost.site.claim` and hosted runner provisioning. If those fail, start here with `subscription.billing.summary` and recipe 1.

Org usage read (featured): `subscription.usage.summary` (optional `period_start`, `period_end`, `include_daily`).

### 9. Trial, usage, data-governance, plan DAG, stubs

Present after listing — do not skip, and do not oversell.

- **Trial (DAG, not featured):** `subscription.trial.convert-and-provision` — `trial_subscription_uuid`, `target_plan`; optional `payment_method_ref`, `seat_count`, `dry_run`, `idempotency_key`. Confirm `target_plan` on the schema. New paid orgs still start at `subscription.platform.checkout`.
- **Usage:** featured read `subscription.usage.summary`. Writer `subscription.usage.consolidate` is `featured: false` (snapshot).
- **Data-governance:** `subscription.data-governance.configure` (`featured: false`) sets org audit/retention policy flags and day counts — not a Stripe Checkout. Pair paid retention storage with recipe 7.
- **Plan DAG:** `subscription.plan.change-with-proration` — see recipe 3.
- **Stubs:** `subscription.end-user-seat-pack.checkout`, `subscription.lumen.billing.change`, `subscription.retention.billing.change`, `subscription.retention.billing.quote`. Outputs include `supported`, `status`, `unsupported_reason`. Say so; do not open a missing `checkout_url` as if payment started.

## Object model

| Object | What it is | Handle |
|---|---|---|
| Platform subscription | Canonical Orkestia paid plan | `subscription_uuid` from `data.subscription.list` / summary |
| Checkout session | Stripe-hosted payment | `checkout_url`, `checkout_workflow_id` |
| Portal session | Stripe self-service | `portal_url` |
| Billing item | Stripe-managed quantity | `item_code` from summary `items` |
| Platform user seats | Org-member seats | checkout + downgrade preview/schedule/cancel |
| Actor/RBAC seats | Paid Staff actor pool | `subscription.actor-rbac-seat.*` |
| End-user seat pack | Raises app `identity.seat.status` cap | `identity_app_uuid` + `pack_size` |
| Lumen / retention add-ons | Observability tier + state retention | `subscription.billing.lumen-*`, `workflow-retention.*` |

## Day-to-day reads

- `subscription.billing.summary` — customer billing state + Stripe-managed items
- `data.subscription.list` — OrganizationSubscription rows (UUID-only)
- `data.subscription.plan.list` — active plan catalog (UUID-only)
- `subscription.actor-rbac-seat.status` — paid RBAC availability + consumers
- `subscription.usage.summary` — period usage + cost from the local catalog
- `identity.seat.status` — app end-user cap (after packs)

## Gotchas

- Checkout **always** means open a URL in a browser. Wrapper completion ≠ paid.
- Never invent `item_code`, `plan`, `selected_price_ref`, or Stripe price IDs — read summary/schema.
- `subscription.end-user-seat-pack.checkout` (no `.billing.`) is a stub. Packs: `subscription.billing.end-user-seat-pack.checkout`.
- Staff seat **reductions** without `confirm_rbac_actor_seat_loss: true` are refused. Tokens may vanish on a confirmed reduction.
- Platform user-seat downgrade **preview** is how you name who would be unseated; schedule is at renewal; cancel is featured.
- `subscription.checkout`, `renewal`, `cancellation`, `payment_recovery`, `sync`, `seat_change`, `key_provision` / `key_revoke`, and `*.apply-downgrade` are not featured operator entry points.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, schema, start, watch, recovery
- `orkestia-app-platform` — end-user seats, `identity.seat.status`, `apphost.site.claim` preconditions
- `orkestia-staff` — actors that consume RBAC seats
- `orkestia-agents` — cost ledger reads
- `orkestia-runners` — `runner.hosted-usage-reconcile` BillableEvents; hosted pools
- `orkestia-tickets` — `ticket.software-delivery.cost-*`
- `orkestia-compositions` — not billing; listed because exposed apps still need a paid org

No dedicated Lumen skill: discover `prefix="lumen."` when the user needs observability, not just the invoice line.

## Additional resources

- Workflow map: [reference.md](reference.md)
- Worked scenarios: [examples.md](examples.md)
