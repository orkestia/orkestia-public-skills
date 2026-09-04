---
name: orkestia-org-and-team
description: >-
  Administers an Orkestia organization's members and their access: inviting
  teammates by email, revealing or resending invite links, accepting invitations,
  changing roles, removing members, minting, rotating, and revoking member API
  tokens for agents and CI, updating the caller's profile and notification
  preferences, reading and paying the platform subscription and user seats, and
  disabling namespaces or types org-wide. Use when the user says invite, teammate,
  role, owner, admin, remove member, API token, seat, plan, checkout, billing
  portal, or wants to block a workflow for everyone in the org. Not for app
  end-users (that is orkestia-app-platform) or staff actors (orkestia-staff).
---

# Organization and team

An **organization** is the tenant every run is scoped to. **Members** are accounts holding a role in it (`owner`, `admin`, `member`), invited by email. Each member can mint **API tokens** that carry the member's identity and the org into MCP and CLI calls. The org's **platform subscription** pays for member seats and gates paid surfaces. This skill covers that administrative surface. It does not cover an app's own customers (end-users, seats packs, identity apps: `orkestia-app-platform`) or hired AI actors (`orkestia-staff`).

Live types: `list_workflow_types(prefix="identity.membership.")`, `prefix="identity.org-invitation."`, `prefix="identity.api-token."`, `prefix="identity.user."`, `prefix="identity.notification-pref."`, `prefix="security.org-workflow-policy."`, `prefix="subscription.billing."`, `prefix="subscription.platform."`. Counts in this file are from 2026-09-04; re-list before claiming a type exists.

Every mutation below: `whoami()` once per session, `get_workflow_schema` for the type, then `start_workflow` and read the terminal `state_data`. Omit `organization_uuid`, `actor`, and `user_uuid`; they are `source.kind: context` and the server injects them. Confirm intent before any mutation, twice before anything that bills.

## When to load

Load this skill when the user wants to bring a teammate in or take one out, change who is admin, hand an agent or CI job a credential, rotate a leaked token, see or pay the platform bill, add user seats, fix their display name, quiet notifications, or block a namespace for the whole org. Load `orkestia-start-here` if the user has no organization yet: creation happens in the web console, not here. Load `orkestia-subscription` for add-ons, Lumen tiers, retention, proration, and end-user seat packs. Load `orkestia-app-platform` for anything about the user's own app customers.

## Use cases

1. **Invite a teammate.** Email invitation with a role; reveal the link when email does not arrive; resend or cancel.
2. **Join an org.** Accept an invitation by token; confirm which orgs the caller belongs to.
3. **Change roles or remove a member.** Promote to admin, demote, or remove, with the membership UUID.
4. **Credential for an agent or CI.** Mint a named, expiring API token; rotate it; revoke it; list what exists.
5. **Profile and notifications.** Update name, username, avatar; quiet hours, digest, mute.
6. **Pay and seat the org.** Read the billing summary; start platform checkout; add user seats; open the Stripe portal.
7. **Org-wide guardrail.** Disable a namespace or type for every member; list and clear the denylist.

## How to

### 1. Invite a teammate

1. Optional pre-check: `identity.user.exists-by-email` (`read_only: true`, no org needed) with `email`. Tells you whether the invitee already has a platform account. Invite either way.
2. `get_workflow_schema("identity.org-invitation.create")`. Caller fields: `email` (required), optional `role`, `message`, `expires_in_days`.
3. Confirm email and role with the user. Then `start_workflow("identity.org-invitation.create", { "email": "…", "role": "member" })`.
4. Read `state_data`: `invitation_uuid`, `email_dispatched`, `dispatch_error`. If `email_dispatched` is false, go to step 5 instead of retrying the create.
5. **Reveal the link** when email is delayed or blocked: `identity.org-invitation.reveal-link` (`read_only: true`) with `invitation_uuid` → `invite_url`, `status`, `expires_at`. Hand the URL to the user to pass along out of band.
6. Pending invitations: `identity.org-invitation.query` (`read_only: true`). Re-send: `identity.org-invitation.resend`. Withdraw: `identity.org-invitation.cancel`. All take `invitation_uuid`.

### 2. Join an organization

1. The invitee signs in to the web console; a pending invitation is applied automatically on first login.
2. Over MCP, `identity.org-invitation.accept` takes `token` (the one-time token in the invite link) and returns `accepted`, `reason`, `membership_uuid`, `role`, `organization_uuid`. `accepted: false` with a `reason` is an idempotent or rejected outcome, not an error to retry. `identity.org-invitation.decline` is the opposite path.
3. Confirm: `identity.organization.query` (`read_only: true`) lists the caller's organizations with `role`; `identity.user.whoami` (`read_only: true`) resolves the caller to profile plus memberships. The MCP tool `whoami` remains the identity source for the current token.

### 3. Change a role or remove a member

1. Find the membership: `identity.membership.query` (`read_only: true`) returns `memberships` with `membership_uuid`, `username`, `email`, `role`, `user_uuid`; `identity.membership.query-by-org` returns `users` with `user_uuid`, `email`, `role`. Optional `role` filter on the second.
2. `get_workflow_schema("identity.membership.update-role")`. Caller fields: `membership_uuid`, `role` (`member`, `admin`, `owner`), optional `force`.
3. Confirm the target person and new role, then start. Output: `previous_role`, `new_role`, `updated_at`.
4. Remove: `get_workflow_schema("identity.membership.remove")` (`membership_uuid`, optional `force`), confirm, start. Output: `removed`, `was_last_owner`, `reason`. Removing frees a platform user seat; it does not delete the account.
5. Do not demote or remove the last owner. If the run refuses, read `failure_reason` and stop; `force` exists on the schema, but use it only when the user names the consequence.
6. Account deletion is a **request**: `identity.user.delete` (unfeatured) requires `confirm` and a `confirmation_phrase`, emails operations, and deletes nothing itself.

### 4. API tokens for agents, CI, and other clients

1. List: `identity.api-token.query` (`read_only: true`) → `tokens` with `token_uuid`, `name`, `expires_at`, `expired`, `last_used_at`. Tokens with `expires_at: null` never expire; flag them.
2. Mint: `get_workflow_schema("identity.api-token.create")`. Caller fields: `name` (required), optional `ttl_seconds` or `expires_at`. Always set one of the two for a machine credential. Confirm name and lifetime, then start.
3. The plaintext token is in the terminal `state_data` (`token`, also `plaintext_token`) **once**. Hand it to the user in the reply. Never write it to a file, a config, or a log the user did not ask for; never echo it back later.
4. The client sends `Authorization: Bearer <token>` to `https://mcp.orkestia.dev/mcp`. Its first call must be `whoami`, which will show `token_type` and the org.
5. Rotate: `identity.api-token.rotate` with `token_uuid` (optional new `ttl_seconds` / `expires_at`) → new `token_uuid`, `old_token_uuid`, new plaintext `token`. The old token is revoked in the same run. Use this for a leaked or expiring credential.
6. Rename: `identity.api-token.update`. Kill: `identity.api-token.revoke` (hard delete). The unfeatured `identity.user.refresh-token` is an older rotation path; prefer `identity.api-token.rotate`.

Tokens minted here are **member** credentials. They must not be shipped to a browser or an app end-user; those get PKCE sessions from an identity app (`orkestia-app-platform`).

### 5. Profile and notification preferences

1. `identity.user.update`: caller fields `name`, `username`, `avatar_url`, all optional. Applies to the calling member only.
2. `identity.notification-pref.query` (`read_only: true`) lists the caller's preferences for this org. `identity.notification-pref.get` fetches one by `preference_uuid`.
3. Create or update (both unfeatured, member-scoped): `in_app_enabled`, `email_enabled`, `email_digest`, `quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`, `quiet_hours_timezone`; update also takes `muted_until` and `clear_mute`. Read the schema for exact types before starting.

### 6. Pay for the platform and add member seats

1. `start_workflow("subscription.billing.summary", {})` (`read_only: true`). Read `platform_subscription` (`plan_name`, `status`, `user_seats`, `user_seats_used`, period dates), `items`, `upcoming_invoice`, and **`actions`**: for every purchasable thing it names the workflow and whether it is `available` right now. Quote that object instead of guessing. `catalog.plans` lists plan names and descriptions; prices come from the checkout runs, not from documents.
2. **No subscription yet:** `get_workflow_schema("subscription.platform.checkout")`. Caller fields: `success_url` and `cancel_url` (required), optional `selected_price_ref`, `user_seats`, `key_seats`, `idempotency_key`. Confirm, start, then hand the user `checkout_url`. `checkout_workflow_id` is the child run to watch for completion; `next_action` tells the UI or agent what to do next.
3. **More member seats:** `subscription.billing.platform-user-seat.checkout` with `success_url`, `cancel_url`, and either `quantity` (target) or `add_seats` (delta). Output includes `prior_quantity`, `target_quantity`, `available`, `one_time_amount`, `currency`, `checkout_url`. Fewer seats is a scheduled downgrade: `subscription.billing.platform-user-seat-downgrade.preview` → `.schedule` → `.cancel` (see `orkestia-subscription`).
4. **Self-service:** `subscription.billing.portal-session.create` returns a Stripe Billing Portal URL for invoices, payment methods, and cancellation.
5. A member who cannot sign in after an invite while `user_seats_used` equals `user_seats` needs step 3 first.

### 7. Org-wide workflow denylist

1. `security.org-workflow-policy.query` (`read_only: true`, optional `target_kind`) → `policies`, `count`.
2. `security.org-workflow-policy.set` with `target_kind` (`"namespace"` or `"workflow_type"`), `target` (a first-level namespace such as `bling`, or an exact type such as `bling.fetch-dre`), optional `disabled` (defaults to true; presence means off). Output: `created`. Confirm the blast radius: a namespace entry blocks every type under it for every member and actor.
3. `security.org-workflow-policy.clear` with `target_kind` and `target` removes the row.

Use this for guardrails such as "nobody in this org may start `aws.ec2.*`". It is not a per-member permission; roles are.

## Object model

| Idea | Meaning |
|---|---|
| Organization | Tenant. Created in the console. `identity.organization.query` lists the caller's orgs with role. |
| Membership | One account's seat in one org: `membership_uuid`, `role`. The unit `update-role` and `remove` act on. |
| Role | `owner`, `admin`, `member`. Org-level; not a workflow-by-workflow permission. |
| Invitation | Email plus role plus expiry. `invitation_uuid` for resend, cancel, reveal; one-time `token` in the link for accept. |
| API token | A member credential: `token_uuid`, `name`, expiry. Plaintext shown once at create and rotate. |
| Platform subscription | Stripe-backed plan for the org: user seats, key or agent seats. `subscription.billing.summary` is the read. |
| User seat | Capacity for members. `user_seats` vs `user_seats_used`. |
| Denylist row | `target_kind` + `target` + `disabled` for the whole org. |

## Day-to-day reads

`whoami`, `identity.organization.query`, `identity.organization.get`, `identity.user.whoami`, `identity.user.query`, `identity.user.get`, `identity.user.exists-by-email`, `identity.membership.query`, `identity.membership.query-by-org`, `identity.membership.query-by-user`, `identity.membership.get`, `identity.org-invitation.query`, `identity.org-invitation.reveal-link`, `identity.api-token.query`, `identity.notification-pref.query`, `identity.notification-pref.get`, `security.org-workflow-policy.query`, `subscription.billing.summary`, `data.subscription.list`, `data.subscription.plan.list`.

Mutations, each behind confirmation: `identity.org-invitation.create` / `resend` / `cancel` / `accept` / `decline`, `identity.membership.update-role` / `remove`, `identity.api-token.create` / `rotate` / `revoke` / `update`, `identity.user.update`, `identity.notification-pref.create` / `update`, `security.org-workflow-policy.set` / `clear`, and the billing checkouts (`subscription.platform.checkout`, `subscription.billing.platform-user-seat.checkout`, `subscription.billing.portal-session.create`).

## Gotchas

- **Org creation is not here.** `identity.organization.*` has only `get` and `query`. Console `/onboarding` creates the org.
- **Three kinds of "user."** Members (this skill), app end-users (`identity.end-user.*`, seats packs), and staff actors (`staff.*`). Do not invite a customer of the user's app as a member.
- **Membership UUID, not user UUID.** `update-role` and `remove` take `membership_uuid` from `identity.membership.query`; `query-by-org` returns `user_uuid`, which is a different id.
- **`email_dispatched: false` is not a failed invite.** The row exists; reveal the link.
- **`accepted: false` with a `reason` is final.** The token was used, expired, or belongs to another account. Do not loop on accept.
- **Tokens are shown once.** Create and rotate return plaintext in the terminal run only. `identity.api-token.query` never does.
- **Seat math gates sign-in.** An invite can be accepted while the org is over its user seats; the member still cannot use the org until seats are bought.
- **Checkout URLs are for a browser.** Do not try to "complete" a checkout over MCP; hand over `checkout_url` and later re-read `subscription.billing.summary`.
- **The denylist is org-wide.** It is a guardrail, not RBAC. Per-actor tool policy lives in `agents.tool-policy.*` and staff role bindings.
- **Never quote a price from memory.** Read `one_time_amount` and `currency` from the checkout run or the `upcoming_invoice` in the summary.

## Sibling skills

`orkestia-start-here` (day zero, console sign-up), `orkestia-subscription` (add-ons, downgrades, proration, end-user seat packs), `orkestia-app-platform` (end-users, identity apps), `orkestia-staff` (actors, RBAC seats), `orkestia-agents` (agent tokens and tool policy).

## Additional resources

- Workflow map by job: [reference.md](reference.md)
- Worked invite, token, role, and billing scenarios: [examples.md](examples.md)
