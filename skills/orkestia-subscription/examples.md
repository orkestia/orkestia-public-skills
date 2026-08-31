# Subscription — examples

Every mutation: `whoami()` already ran, then `get_workflow_schema` for the type, then `start_workflow` → `watch_workflow`. Do not pass `organization_uuid`. Open every `checkout_url` / `portal_url` in a browser — wrapper completion is not payment.

Do not invent Stripe price IDs, `item_code` values, or plan names. Read them from `subscription.billing.summary` / `data.subscription.plan.list` or the schema.

## 1. Start platform checkout

```
start_workflow("subscription.platform.checkout", {
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel",
  "user_seats": 5,
  "idempotency_key": "platform-checkout-2026-08-31"
})
```

Hand the user `checkout_url`. Watch `checkout_workflow_id` until the child run shows payment activated. Then `subscription.billing.summary` to confirm `platform_subscription` and `items`.

## 2. Billing summary + Stripe portal

```
start_workflow("subscription.billing.summary", {})
```

Optional end-user seat slice:

```
start_workflow("subscription.billing.summary", {
  "identity_app_uuid": "<app>"
})
```

Self-service:

```
start_workflow("subscription.billing.portal-session.create", {
  "return_url": "https://console.example.com/billing"
})
```

Open `portal_url`. Keep `item_code` values from summary `items` for later quantity changes.

## 3. Change plan with proration, then an item quantity

Resolve UUIDs first (`data.subscription.list`, `data.subscription.plan.list`). Then:

```
start_workflow("subscription.plan_change", {
  "subscription_uuid": "<from list>",
  "current_plan_uuid": "<current>",
  "new_plan_uuid": "<target>"
})
```

Watch `proration_amount` / `proration_details`. If `require_confirmation` is in play, do not skip the confirmation the workflow asks for.

Quantity (use a real `item_code` from summary — placeholder below is not a catalog name):

```
start_workflow("subscription.billing.item.change", {
  "item_code": "<from billing.summary items>",
  "quantity": 8,
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel"
})
```

If the run returns `checkout_url`, open it (paid increase).

## 4. Preview a platform user-seat downgrade, then schedule or cancel

Buy more:

```
start_workflow("subscription.billing.platform-user-seat.checkout", {
  "add_seats": 3,
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel"
})
```

Downgrade below usage — preview **names** members:

```
start_workflow("subscription.billing.platform-user-seat-downgrade.preview", {
  "quantity": 2
})
```

Read `candidates`, `selected_members`, `default_oldest_members`, `seats_to_remove`. After the user confirms who is unseated:

```
start_workflow("subscription.billing.platform-user-seat-downgrade.schedule", {
  "quantity": 2,
  "selected_membership_uuids": ["<membership-uuid>", "<membership-uuid>"]
})
```

Abort before renewal (optional `seat_downgrade_schedule_uuid` from schedule output, optional `cancel_reason`):

```
start_workflow("subscription.billing.platform-user-seat-downgrade.cancel", {
  "seat_downgrade_schedule_uuid": "<from schedule>"
})
```

## 5. Staff RBAC seats and an end-user pack

Status:

```
start_workflow("subscription.actor-rbac-seat.status", {})
```

Increase (may return `checkout_url`):

```
start_workflow("subscription.actor-rbac-seat.resize", {
  "add_paid_rbac_actor_seats": 2,
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel"
})
```

**Reduction** — show who loses access, then pass the explicit flag (tokens may be revoked immediately):

```
start_workflow("subscription.actor-rbac-seat.resize", {
  "paid_rbac_actor_seats": 1,
  "confirm_rbac_actor_seat_loss": true
})
```

Workforce model: `orkestia-staff`. Dedicated Checkout alternative: `subscription.billing.actor-seat.checkout`.

End-user pack (app customers — `orkestia-app-platform`):

```
start_workflow("subscription.billing.end-user-seat-pack.checkout", {
  "identity_app_uuid": "<app>",
  "pack_size": 25,
  "success_url": "https://portal.example.com/billing/success",
  "cancel_url": "https://portal.example.com/billing/cancel"
})
```

Do **not** use `subscription.end-user-seat-pack.checkout` for payment; that type returns pending-support status.

## 6. Lumen / retention add-on, usage, and a stub

Take `plan` from summary/schema (do not invent tier names):

```
start_workflow("subscription.billing.lumen-plan.checkout", {
  "plan": "<from billing.summary or schema>",
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel"
})
```

Retention:

```
start_workflow("subscription.billing.workflow-retention.checkout", {
  "retention_days": 90,
  "success_url": "https://console.example.com/billing/success",
  "cancel_url": "https://console.example.com/billing/cancel"
})
```

Cancel a scheduled retention downgrade: `subscription.billing.workflow-retention-downgrade.cancel`.

Usage read:

```
start_workflow("subscription.usage.summary", {})
```

If someone starts `subscription.lumen.billing.change` or `subscription.retention.billing.quote`, treat `supported` / `unsupported_reason` as the answer — those stubs do not complete checkout. Observability itself: `list_workflow_types(prefix="lumen.")`.
