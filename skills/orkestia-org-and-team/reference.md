# Organization and team — workflow map

Grouped by job. Verified against the live catalog on 2026-09-04. Re-list with the prefixes named in `SKILL.md`; verify fields with `get_workflow_schema` before every start. Omit `organization_uuid`, `actor`, `user_uuid` (context-injected).

## Who am I, which orgs

| Workflow | Kind | Inputs (caller) | Output |
|---|---|---|---|
| `whoami` (MCP tool) | read | — | `user_id`, `username`, `organization_uuid`, `token_type`, `principal_type`, `exp` |
| `identity.organization.query` | read-only, featured | optional `limit`, `offset` | `organizations` (`uuid`, `name`, `domain`, `region`, `role`), `count` |
| `identity.organization.get` | read-only, featured | — (org from context) | one organization |
| `identity.user.whoami` | read-only, featured | — | profile + memberships |
| `identity.membership.query-by-user` | read-only, featured | per schema | orgs for a user with role |

## Team

| Workflow | Kind | Inputs (caller) | Output |
|---|---|---|---|
| `identity.membership.query-by-org` | read-only, featured | optional `role`, `limit`, `offset` | `users` (`user_uuid`, `username`, `email`, `name`, `role`, `invited_at`), `count` |
| `identity.membership.query` | read-only, featured | — | `memberships` (`membership_uuid`, `username`, `email`, `role`, `system_role`, `user_uuid`), `count` |
| `identity.membership.get` | read-only, featured | `membership_uuid` | one membership |
| `identity.user.query` | read-only, featured | optional `filters`, `limit`, `offset` | users |
| `identity.user.get` | read-only, featured | `user_uuid` | one user |
| `identity.user.exists-by-email` | read-only, unfeatured, no org | `email` | boolean |
| `identity.membership.update-role` | mutation, featured | `membership_uuid`, `role`, optional `force` | `previous_role`, `new_role`, `updated_at` |
| `identity.membership.remove` | mutation, featured | `membership_uuid`, optional `force` | `removed`, `was_last_owner`, `reason` |

## Invitations

| Workflow | Kind | Inputs (caller) | Output |
|---|---|---|---|
| `identity.org-invitation.create` | mutation, featured | `email`, optional `role`, `message`, `expires_in_days` | `invitation_uuid`, `email_dispatched`, `dispatch_error`, `expires_at` |
| `identity.org-invitation.query` | read-only, featured | — (pending by default) | invitations |
| `identity.org-invitation.reveal-link` | read-only, featured | `invitation_uuid` | `invite_url`, `revealed`, `status`, `expires_at` |
| `identity.org-invitation.resend` | mutation, featured | `invitation_uuid` | dispatch result |
| `identity.org-invitation.cancel` | mutation, featured | `invitation_uuid` | cancel result |
| `identity.org-invitation.accept` | mutation, featured, no org | `token` | `accepted`, `reason`, `membership_uuid`, `role`, `organization_uuid` |
| `identity.org-invitation.decline` | mutation, featured | per schema | decline result |

## API tokens (member credentials)

| Workflow | Kind | Inputs (caller) | Output |
|---|---|---|---|
| `identity.api-token.query` | read-only, featured | — | `tokens` (`token_uuid`, `name`, `expires_at`, `expired`, `last_used_at`), `count` |
| `identity.api-token.create` | mutation, featured | `name`, optional `ttl_seconds`, `expires_at` | `token_uuid`, plaintext `token` (once), `expires_at` |
| `identity.api-token.rotate` | mutation, featured | `token_uuid`, optional `ttl_seconds`, `expires_at` | new `token_uuid`, `old_token_uuid`, plaintext `token` (once), `rotated_at` |
| `identity.api-token.update` | mutation, featured | `token_uuid`, new name (per schema) | renamed row |
| `identity.api-token.revoke` | mutation, featured | `token_uuid` | hard delete |
| `identity.user.refresh-token` | mutation, featured, legacy | `refresh_token`, `token_name` | older rotation path; prefer `api-token.rotate` |
| `identity.user.validate-token` | mutation (not read-only), featured | `token` | profile for a raw token; avoid in normal use |

## Profile and notifications

| Workflow | Kind | Inputs (caller) |
|---|---|---|
| `identity.user.update` | mutation, featured | `name`, `username`, `avatar_url` |
| `identity.user.delete` | request only, unfeatured | `confirm`, `confirmation_phrase`, `reason` — emails ops, deletes nothing |
| `identity.notification-pref.query` | read-only, featured | — |
| `identity.notification-pref.get` | read-only, featured | `preference_uuid` |
| `identity.notification-pref.create` | mutation, unfeatured | `in_app_enabled`, `email_enabled`, `email_digest`, quiet-hours fields |
| `identity.notification-pref.update` | mutation, unfeatured | above plus `preference_uuid`, `muted_until`, `clear_mute` |

## Platform billing and member seats

| Workflow | Kind | Inputs (caller) | Output |
|---|---|---|---|
| `subscription.billing.summary` | read-only, featured | optional `identity_app_uuid` | `platform_subscription`, `entitlements`, `items`, `upcoming_invoice`, `recent_activity`, `catalog`, `actions`, `status` |
| `subscription.platform.checkout` | mutation, featured | `success_url`, `cancel_url`, optional `selected_price_ref`, `user_seats`, `key_seats`, `idempotency_key` | `checkout_url`, `checkout_workflow_id`, `plan_uuid`, `platform_plan_name`, `next_action` |
| `subscription.billing.platform-user-seat.checkout` | mutation, featured | `success_url`, `cancel_url`, `quantity` or `add_seats` | `checkout_url`, `prior_quantity`, `target_quantity`, `available`, `one_time_amount`, `currency` |
| `subscription.billing.platform-user-seat-downgrade.preview` / `.schedule` / `.cancel` | featured | per schema | scheduled downgrade with member unseats |
| `subscription.billing.portal-session.create` | mutation, featured | per schema | Stripe Billing Portal URL |
| `subscription.billing.item.change` | mutation, featured | supported `item_code`s from summary `actions.change_item` | quantity change |
| `data.subscription.list`, `data.subscription.plan.list` | read | — | subscriptions, plan catalog |

Everything else under `subscription.*` (Lumen, retention, actor seats, end-user seat packs, trial conversion, proration DAG) is in `orkestia-subscription`.

## Org-wide guardrail

| Workflow | Kind | Inputs (caller) |
|---|---|---|
| `security.org-workflow-policy.query` | read-only, featured | optional `target_kind` → `policies`, `count` |
| `security.org-workflow-policy.set` | mutation, featured | `target_kind` (`namespace` / `workflow_type`), `target`, optional `disabled` (default true) → `created` |
| `security.org-workflow-policy.clear` | mutation, featured | `target_kind`, `target` |

## Not this skill

`identity.end-user.*`, `identity.seat.*`, `identity.app-organization.*`, `identity.app.*` (app customers: `orkestia-app-platform`); `staff.grant-role-binding` and actor seats (`orkestia-staff`); `agents.tool-policy.*` (`orkestia-agents`); `user.onboarding` (account-side hook, not a user entry point).
