# App platform — workflow map

Re-list before treating this as complete. Snapshot used while writing: `identity.*` (72), `appdata.*` (2) + `data.appdata.*` (13), `apphost.*` (11), `policy.*` (6), `data.identity.*` (29 persist internals).

```
whoami()
list_workflow_types(prefix="identity.")
list_workflow_types(prefix="appdata.")
list_workflow_types(prefix="apphost.")
list_workflow_types(prefix="policy.")
list_workflow_types(prefix="data.identity.")
list_workflow_types(prefix="data.appdata.")
```

Prefer `featured: true`. Skip `data.identity.*` persist/prune from operator recipes.

## Discover

| Type | Job |
|---|---|
| `identity.app.query` | List org identity apps, or one app's detail |
| `identity.end-user.query` | Paged end-users for an app tenant |
| `identity.seat.status` | Cap / consumed / free / over_cap_pending |
| `apphost.site.list` / `get` | Hosted sites + serving URL |
| `data.appdata.structure.query` | Databases, tables, fields for an app |

## Identity app lifecycle (`identity.app.*`, 13)

| Type | Job |
|---|---|
| `identity.app.provision` | Create tenant + public PKCE client. Caller: `name`; optional `redirect_uris`, `project_uuid`, `mode`, `dev_allowed_emails`, `org_owned_enabled`. Output: `identity_app_uuid`, `client_uuid`, `client_key`, `integration` |
| `identity.app.query` | List / detail |
| `identity.app.configure-client` | OIDC client updates (safe-by-default) |
| `identity.app.allow-dev-origin` | Localhost origin. Caller: `identity_app_uuid`, `origin`; optional `callback_path`, `dry_run` |
| `identity.app.add-federation` | Upstream IdP (SSO) |
| `identity.app.set-email-domains` | Live-mode email-domain allowlist |
| `identity.app.set-mode` | Dev → live, **one-way**. Caller: `identity_app_uuid`, `mode`; optional `redirect_uris`, `client_updates` |
| `identity.app.set-org-owned` | Toggle org-owned appdata flag. Caller: `identity_app_uuid`, `org_owned_enabled` |
| `identity.app.set-end-user-agent` | Point at org-owned AgentConfig. Caller: `identity_app_uuid`; optional `end_user_agent_config_uuid` |
| `identity.app.expose-virtual-workflow` | Eligibility-checked expose. Caller: `identity_app_uuid`, `composition_uuid`, `version` |
| `identity.app.unexpose-virtual-workflow` | Revoke exposure |
| `identity.app.reconcile-catalog` | Backfill capability catalog from exposed compositions |
| `identity.app.deprovision` | Tear down app-owned identity state |

## End-users (`identity.end-user.*`, 18)

| Type | Job |
|---|---|
| `identity.end-user.create` | Register. Caller: `identity_app_uuid`, `email` → `end_user_uuid`, `seated` |
| `identity.end-user.invite` | Mail access. `identity_app_uuid` plus `end_user_uuid` and/or `email`; optional `app_organization_uuid`, `resend`, `expires_in_hours` |
| `identity.end-user.query` | Paged list |
| `identity.end-user.admit` | Login-time seat gate (hosted login) |
| `identity.end-user.disable` / `delete` | Free the seat (disable / soft-delete) |
| `identity.end-user.purge` | Hard-purge after soft-delete |
| `identity.end-user.session.revoke` | Force re-login |
| `identity.end-user.whoami` | Calling end-user (end-user JWT; `requires_organization_uuid: false`) |
| `identity.end-user.audit-query` | Auth audit trail |
| `identity.end-user.assign-group` | One group per user. Caller: `identity_app_uuid`, `end_user_uuid`, `group_slug`; optional `force` |
| `identity.end-user.group.seed-defaults` | Seed default groups |
| `identity.end-user.group.define` | Create/rename. Caller: `identity_app_uuid`, `slug`, `title` |
| `identity.end-user.group.set-capabilities` | Replace capability set. Caller: `identity_app_uuid`, `group_slug`, `capabilities` |
| `identity.end-user.group.list` | List groups + capabilities |
| `identity.end-user.organization.query` / `get` / `switch` | End-user workspaces (end-user JWT) |

## Seats (`identity.seat.*`, 2)

| Type | Job |
|---|---|
| `identity.seat.status` | `cap` / `consumed` / `free` / `over_cap_pending` |
| `identity.seat.grant` | Raise cap. Caller: `identity_app_uuid`, `batch_size`, `source` — confirm `source` on the schema |

Paid packs: `subscription.billing.end-user-seat-pack.checkout` (`identity_app_uuid`, `pack_size`, `success_url`, `cancel_url`) → `checkout_url`. Stub (do not use for checkout): `subscription.end-user-seat-pack.checkout`.

## App-organizations (`identity.app-organization.*`, 5)

| Type | Job |
|---|---|
| `identity.app-organization.create` | Workspace. Caller: `identity_app_uuid`, `name`, `slug`; optional `kind`, `metadata` |
| `identity.app-organization.invite` | Pending membership. Caller: `identity_app_uuid`, `app_organization_uuid`, plus `end_user_uuid` and/or `email`; optional `group_slug` |
| `identity.app-organization.add-member` | Active membership |
| `identity.app-organization.assign-role` | Change workspace role |
| `identity.app-organization.query` | List workspaces for an app |

## Exposed compositions (`identity.composition.*`, 2)

| Type | Job |
|---|---|
| `identity.composition.set-audience` | Who may invoke. Caller: `identity_app_uuid`, `composition_uuid`, `audience`; optional `groups` |
| `identity.composition.audience-query` | Read audience |

End-user agent runtime (not under `identity.`): `agents.end-user.ask`, `agents.end-user.ask-stream`.

## Appdata

**Org publish (`appdata.*`, 2)**

| Type | Job |
|---|---|
| `appdata.publish-as-app` | Org-side rows into an `app`-owned table. Caller: `identity_app_uuid`, `database_slug`, `table_slug`, `payload` **or** `payloads` (max 500). Requires `identity.app.set-org-owned`. Keep `record_uuids` |
| `appdata.retract-as-app` | Retract named rows. Caller: `identity_app_uuid`, `database_slug`, `table_slug`, `record_uuids` (max 500), `reason` (required) |

**Data plane (`data.appdata.*`, 13)**

| Type | Job |
|---|---|
| `data.appdata.structure.apply` | Apply VirtualDataStructure. Caller: `identity_app_uuid`, `structure`; optional `dry_run`, `apply_plan` |
| `data.appdata.structure.query` | List databases / tables / fields |
| `data.appdata.record.write` | Create owner-scoped row. Caller: `database_slug`, `table_slug`, `payload` |
| `data.appdata.record.read` / `query` / `update` / `delete` | Single-record + query policy |
| `data.appdata.transaction.apply` | Ordered atomic batch (`operations`) |
| `data.appdata.document.request-upload` | Pending doc + server-chosen `key`. Caller: `storage_connection_uuid`, `bucket`, `kind` |
| `data.appdata.document.confirm` | Mark active. Caller: `document_uuid`; optional `size`, `checksum` |
| `data.appdata.document.query` / `download-url` / `delete` | List / fetch URL / soft-delete |

## Hosting (`apphost.*`)

Re-list `prefix="apphost."`. Create does **not** transfer bytes — it returns a presigned POST. Publish HEADs `bundle.zip` and fails with `bundle not uploaded` if the client POST never ran.

| Type | Job |
|---|---|
| `apphost.site.claim` | Reserve `<slug>.app.orkestia.dev`. Caller: `identity_app_uuid`; optional `slug`. Live-mode + subscription-gated; slug immutable; idempotent per app. **No release yet** |
| `apphost.site.get` / `list` | Fetch / paginate. `active_release_uuid` null ⇒ URL is `app not found` |
| `apphost.site.release-list` | History; `is_active`, `status`, `bundle_bytes`. `pending_upload` + null bytes = POST skipped |
| `apphost.site.set-mode` | `active` \| `redirect` \| `suspended`. `redirect_target` required iff `redirect` |
| `apphost.site.domain-attach` / `domain-list` / `domain-detach` | Custom hostname (ACM + CDN). Read schemas first |
| `apphost.release.create` | `pending_upload` + ticket. Caller: `site_uuid` → `release_uuid`, `upload_url`, `upload_fields`, `expires_in_seconds`, `max_bundle_bytes`. Runtime must POST `bundle.zip` |
| `apphost.release.publish` | Activate after the POST. Caller: `release_uuid` only |
| `apphost.release.rollback` | Re-point. Caller: `site_uuid`; optional `release_uuid` |

## Policy (`policy.*`, 6)

| Type | Job |
|---|---|
| `policy.feature-flag.apply` | Upsert. Caller: `identity_app_uuid`, `flag_key`, `enabled`; optional `flag_type`, `plan_tier` |
| `policy.feature-flag.query` | Read one or list |
| `policy.feature-flag.delete` | Remove |
| `policy.decision.evaluate` | One capability for one end-user |
| `policy.decision.evaluate-batch` | Many capabilities, one end-user |
| `policy.entitlement.query` | Thin read of plan entitlement over `subscription.*` |

## Org-member identity (shipping; not end-users)

**API tokens (5, featured)** — current org member, not an end-user:

| Type | Job |
|---|---|
| `identity.api-token.create` | Caller: `name`; optional `ttl_seconds`, `expires_at`. Plaintext once |
| `identity.api-token.query` | Metadata only (no secret) |
| `identity.api-token.rotate` / `revoke` / `update` | Replace / hard-delete / rename |

**Org invitations (7):** `identity.org-invitation.create` (`email`; optional `role`, `message`, `expires_in_days`), `query`, `resend`, `reveal-link`, `cancel`, `accept`, `decline`.

**Membership (6):** `identity.membership.get`, `query`, `query-by-org`, `query-by-user`, `update-role`, `remove`.

**Users (8):** `identity.user.whoami`, `get`, `query`, `update`, `exists-by-email`, `validate-token`, `refresh-token`, `delete` (emails ops; does not delete).

**Organization (2):** `identity.organization.get`, `query`.

**Notification prefs (4):** `identity.notification-pref.create` / `get` / `query` / `update` (`create`/`update` are not featured).

## Persistence internals — do not start

`data.identity.*` (29) are persist / soft-delete / prune / update rows (`featured: false`). Operator entry points are the `identity.*` workflows above. Listing the prefix is fine; starting persist workflows is not the public how-to.

## Naming note

No `appfeatures` or `appusers` namespaces. Re-check with `list_workflow_types` if a name is missing.
