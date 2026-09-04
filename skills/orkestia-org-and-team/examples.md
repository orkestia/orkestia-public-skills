# Worked examples

Placeholder ids are examples. Never pass `organization_uuid`, `actor`, or `user_uuid`; they are injected from the token.

## 1. "Invite Dana as an admin; her email is not arriving."

```
whoami()
start_workflow("identity.user.exists-by-email", { "email": "dana@example.com" })
get_workflow_schema("identity.org-invitation.create")
start_workflow("identity.org-invitation.create", { "email": "dana@example.com", "role": "admin", "expires_in_days": 7 })
```

Read `invitation_uuid` and `email_dispatched`. If `email_dispatched` is false, or the user reports nothing in the inbox:

```
start_workflow("identity.org-invitation.reveal-link", { "invitation_uuid": "<uuid>" })
```

Hand over `invite_url` and `expires_at`. Do not create a second invitation for the same address; use `identity.org-invitation.resend` if a fresh email is wanted.

## 2. "I got an invite link. Join me to the org."

The link carries a one-time token.

```
get_workflow_schema("identity.org-invitation.accept")
start_workflow("identity.org-invitation.accept", { "token": "<token from the link>" })
```

`accepted: true` returns `membership_uuid`, `role`, `organization_uuid`. `accepted: false` with `reason` (used, expired, wrong account) is final. Then confirm with `identity.organization.query` and remind the user to reconnect their MCP client so the token binds the new org.

## 3. "Make Dana an owner and remove Lee."

```
start_workflow("identity.membership.query", {})
```

Pick `membership_uuid` values by `username`. Confirm both actions with the user, then:

```
get_workflow_schema("identity.membership.update-role")
start_workflow("identity.membership.update-role", { "membership_uuid": "<dana>", "role": "owner" })
get_workflow_schema("identity.membership.remove")
start_workflow("identity.membership.remove", { "membership_uuid": "<lee>" })
```

Report `previous_role` → `new_role` for Dana and the removal result for Lee. If either run fails with a last-owner or self-removal reason, stop and say so; do not pass `force` unless the user names the consequence.

## 4. "Give my CI pipeline a token that dies in 90 days."

```
get_workflow_schema("identity.api-token.create")
start_workflow("identity.api-token.create", { "name": "ci-deploy", "ttl_seconds": 7776000 })
```

Return the plaintext `token` from `state_data` in the reply and nothing else about it. The pipeline sends `Authorization: Bearer <token>` to `https://mcp.orkestia.dev/mcp` and calls `whoami` first.

Ninety days later, or on a leak:

```
start_workflow("identity.api-token.query", {})
start_workflow("identity.api-token.rotate", { "token_uuid": "<ci-deploy uuid>", "ttl_seconds": 7776000 })
```

The old token stops working in the same run; the new plaintext is shown once.

## 5. "Are we paying? Add two seats."

```
start_workflow("subscription.billing.summary", {})
```

Read `platform_subscription.status`, `user_seats`, `user_seats_used`, and `actions.buy_platform_user_seats.available`. If the org has no subscription, start `subscription.platform.checkout` with `success_url` and `cancel_url` and hand over `checkout_url`. Otherwise:

```
get_workflow_schema("subscription.billing.platform-user-seat.checkout")
start_workflow("subscription.billing.platform-user-seat.checkout", {
  "add_seats": 2,
  "success_url": "https://app.example.com/billing/ok",
  "cancel_url": "https://app.example.com/billing/cancel"
})
```

Quote `one_time_amount` and `currency` from the run, hand over `checkout_url`, and re-read the summary after the user pays. Prices never come from a document.

## 6. "Nobody here should be able to touch Hostinger."

```
start_workflow("security.org-workflow-policy.query", {})
get_workflow_schema("security.org-workflow-policy.set")
start_workflow("security.org-workflow-policy.set", { "target_kind": "namespace", "target": "hostinger", "disabled": true })
```

State the blast radius before starting: every member and every actor in the org loses every `hostinger.*` type. For one type only, use `target_kind: "workflow_type"` with the exact name. Reverse with `security.org-workflow-policy.clear` using the same `target_kind` and `target`.

## 7. "Change my display name and mute notifications tonight."

```
start_workflow("identity.user.update", { "name": "Dana R." })
start_workflow("identity.notification-pref.query", {})
get_workflow_schema("identity.notification-pref.update")
start_workflow("identity.notification-pref.update", { "preference_uuid": "<uuid>", "muted_until": "2026-09-05T08:00:00-03:00" })
```

If `query` returns nothing, use `identity.notification-pref.create` with the quiet-hours fields instead of `update`.
