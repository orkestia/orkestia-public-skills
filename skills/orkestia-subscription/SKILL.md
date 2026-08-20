---
name: orkestia-subscription
description: Manage how Orkestia customers pay (subscription.*, 26 types, Stripe-backed) — platform checkout, billing summary and portal, seats (platform users, staff actor/RBAC, end-user packs), Lumen and retention add-ons, downgrade scheduling, and where usage metering comes from. Use for any billing, checkout, or seat question.
---

# Orkestia subscription

All billing is Stripe-backed and workflow-driven, scope `subscription`. The pattern is consistent: **checkout** workflows return a Stripe Checkout URL to open in a browser; **change** workflows mutate quantities with proration; scheduled **downgrades** can be previewed and cancelled before renewal.

## Core

- `subscription.platform.checkout` — the canonical platform subscription. Inputs: `success_url`, `cancel_url` (required); optional `selected_price_ref` (billing cycle), initial `user_seats`, `key_seats`, `idempotency_key`. Output `checkout_url` is what the customer opens; `checkout_workflow_id` can be watched.
- `subscription.billing.summary` — customer billing state + Stripe-managed items.
- `subscription.billing.portal-session.create` — Stripe Billing Portal URL for self-service.
- `subscription.plan_change` (v2.0) — upgrades/downgrades with Stripe proration.
- `subscription.billing.item.change` — adjust any supported Stripe-managed quantity.

## What is sold, by surface

| Surface | Workflows | Notes |
|---|---|---|
| Platform user seats | `billing.platform-user-seat.checkout`; downgrade `preview` / `schedule` / `cancel` | Downgrading below active usage previews exactly which members would be unseated at renewal |
| Staff actor / RBAC seats | `billing.actor-seat.checkout`; `actor-rbac-seat.resize` / `status` | Every seat **reduction requires explicit destructive-loss confirmation** |
| End-user seat packs | `billing.end-user-seat-pack.checkout` | Raises the app-platform cap read by `identity.seat.status` |
| Lumen observability | `billing.lumen-plan.checkout` / `change`; `billing.lumen-addon.change` / `checkout`; `*-downgrade.cancel` | Tiered plans + add-ons: entry packs (1M entries/month each) and storage GB |
| Workflow retention | `billing.workflow-retention.checkout` / `change`; `downgrade.cancel` | State-retention billing, storage cap, governance policy |

Status/quote stubs (read-only): `subscription.end-user-seat-pack.checkout` (pending-support status), `subscription.lumen.billing.change`, `subscription.retention.billing.change` / `quote`.

## Where usage is metered

Consumption flows in from other domains, not a hidden meter:

- `runner.hosted-usage-reconcile` writes one **BillableEvent** per newly-terminal Orkestia-hosted execution (carrying duration) and enforces the org's `max_session_duration_s`.
- Agent sessions carry a cost ledger with per-config budgets — `data.agents.budget-status`, `cost-*` reads.
- Software deliveries reserve and record USD against policy budgets — `ticket.software-delivery.cost-*`.
- Subscription state gates features: `apphost.site.claim` and hosted runner provisioning check it as a precondition.
