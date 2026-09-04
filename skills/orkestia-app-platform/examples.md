# App platform — examples

Every mutation: `whoami()` already ran, then `get_workflow_schema` for the type, then `start_workflow` → `watch_workflow`. Do not pass `organization_uuid` or `actor`. Replace placeholders with UUIDs from prior terminal output.

## 1. Provision Sign in with Orkestia for a Vite app

```
start_workflow("identity.app.provision", {
  "name": "Northwind Portal",
  "redirect_uris": [
    "http://localhost:5173/callback",
    "https://portal.example.com/callback"
  ]
})
```

From the terminal state, keep `identity_app_uuid`, `client_uuid`, `client_key`, and `integration` (`authorize_url`, `code_exchange_url`, `jwks_url`, `issuer`, `discovery_url`). Put `client_key` in the frontend. Wire `@orkestia/auth` from `github:orkestia/orkestia-auth-sdk` (or the same PKCE steps): redirect to `authorize_url`, POST `{ code, code_verifier }` to `code_exchange_url`, verify the RS256 JWT against `jwks_url`.

Add another localhost origin later:

```
start_workflow("identity.app.allow-dev-origin", {
  "identity_app_uuid": "<from provision>",
  "origin": "http://localhost:3000"
})
```

When ready for hosting, graduate (one-way — confirm `mode` on the schema):

```
start_workflow("identity.app.set-mode", {
  "identity_app_uuid": "<from provision>",
  "mode": "live"
})
```

## 2. Invite an end-user after buying a seat pack

```
start_workflow("identity.seat.status", {
  "identity_app_uuid": "<app>"
})
```

If `free` is 0, open Stripe Checkout (not the pending-support stub `subscription.end-user-seat-pack.checkout`):

```
start_workflow("subscription.billing.end-user-seat-pack.checkout", {
  "identity_app_uuid": "<app>",
  "pack_size": 25,
  "success_url": "https://portal.example.com/billing/success",
  "cancel_url": "https://portal.example.com/billing/cancel"
})
```

Open `checkout_url` in a browser. After payment, re-read `identity.seat.status`, then:

```
start_workflow("identity.end-user.create", {
  "identity_app_uuid": "<app>",
  "email": "ada@customer.example"
})
```

```
start_workflow("identity.end-user.invite", {
  "identity_app_uuid": "<app>",
  "end_user_uuid": "<from create>",
  "email": "ada@customer.example"
})
```

Disable or delete later to free the seat. `identity.end-user.admit` is the login-time gate, not this invite path.

## 3. Workspace + one group per user

```
start_workflow("identity.end-user.group.define", {
  "identity_app_uuid": "<app>",
  "slug": "operators",
  "title": "Operators"
})
```

Confirm capability strings with `get_workflow_schema("identity.end-user.group.set-capabilities")` before replacing the set:

```
start_workflow("identity.end-user.group.set-capabilities", {
  "identity_app_uuid": "<app>",
  "group_slug": "operators",
  "capabilities": []
})
```

(Fill `capabilities` only with values the schema documents.)

```
start_workflow("identity.end-user.assign-group", {
  "identity_app_uuid": "<app>",
  "end_user_uuid": "<user>",
  "group_slug": "operators"
})
```

```
start_workflow("identity.app-organization.create", {
  "identity_app_uuid": "<app>",
  "name": "Acme Fleet",
  "slug": "acme-fleet"
})
```

```
start_workflow("identity.app-organization.invite", {
  "identity_app_uuid": "<app>",
  "app_organization_uuid": "<from create>",
  "end_user_uuid": "<user>",
  "group_slug": "operators"
})
```

## 4. Expose a composition, then a bounded agent

Author the composition first (`orkestia-compositions` → `composition.save`). Then:

```
start_workflow("identity.app.expose-virtual-workflow", {
  "identity_app_uuid": "<app>",
  "composition_uuid": "<from composition.save>",
  "version": 1
})
```

Confirm `audience` on `identity.composition.set-audience` before setting it. The app POSTs `/api/workflows` with the end-user JWT. Orkestia injects the principal; end-users cannot start catalog types you did not expose.

Point the app at an org-owned AgentConfig (`orkestia-agents`):

```
start_workflow("identity.app.set-end-user-agent", {
  "identity_app_uuid": "<app>",
  "end_user_agent_config_uuid": "<agent-config>"
})
```

End-user runtime is `agents.end-user.ask` / `ask-stream` (tools = exposed compositions only).

## 5. Host a Hello World page on AppHost

Requires a **live-mode** identity app + qualifying subscription. Provision + `identity.app.set-mode` first if the app is still `dev` (one-way — confirm `mode` on the schema).

Claim is not enough. Do not call the URL live until step F.

```
start_workflow("apphost.site.claim", {
  "identity_app_uuid": "<app>",
  "slug": "hello-world"
})
```

Keep `site_uuid` and `url` (`https://hello-world.app.orkestia.dev`). GET that URL now will be `app not found`.

```
start_workflow("apphost.release.create", {
  "site_uuid": "<from claim>"
})
```

Keep `release_uuid`, `upload_url`, `upload_fields`, `expires_in_seconds`, `max_bundle_bytes`.

`upload_fields` must include `key`, `policy`, `x-amz-algorithm`, `x-amz-credential`, `x-amz-date`, `x-amz-signature`, `x-amz-security-token`. If any is missing, stop — platform bug; do not decode `policy` or invent fields.

Build a root-level zip (publish rejects a nested `index.html`):

```bash
printf '%s\n' '<h1>Hello world</h1>' > index.html
zip -X bundle.zip index.html
```

POST — every `upload_fields` entry, then the file last. Use the returned names; do not invent fields.

```bash
# UPLOAD_URL and UPLOAD_FIELDS come from apphost.release.create terminal output.
python3 - <<'PY'
import json, os, subprocess, sys
fields = json.loads(os.environ["UPLOAD_FIELDS"])
required = {
    "key", "policy", "x-amz-algorithm", "x-amz-credential",
    "x-amz-date", "x-amz-signature", "x-amz-security-token",
}
missing = sorted(required - fields.keys())
if missing:
    print("incomplete ticket; missing", missing, file=sys.stderr)
    raise SystemExit(2)
cmd = ["curl", "-sS", "-X", "POST", os.environ["UPLOAD_URL"]]
for k, v in fields.items():
    cmd.extend(["-F", f"{k}={v}"])
cmd.extend(["-F", "file=@bundle.zip"])
raise SystemExit(subprocess.call(cmd))
PY
```

If DNS or the POST fails: stop. Report claim + `release_uuid` + `pending_upload` + the failure (cannot reach `upload_url`, incomplete ticket missing SigV4 keys, or S3 status). Do **not** start publish. Do **not** try Hostinger or `storage.object.put`. Do **not** decode `policy`.

Only after HTTP 2xx/204 from the POST:

```
start_workflow("apphost.release.publish", {
  "release_uuid": "<from create>"
})
```

Verify:

```
start_workflow("apphost.site.get", { "site_uuid": "<from claim>" })
start_workflow("apphost.site.release-list", { "site_uuid": "<from claim>" })
```

`active_release_uuid` must match. GET `url` must return `<h1>Hello world</h1>`. If release-list shows `pending_upload` and null `bundle_bytes`, the POST never landed.

Rollback / suspend after a real publish:

```
start_workflow("apphost.release.rollback", { "site_uuid": "<from claim>" })
start_workflow("apphost.site.set-mode", { "site_uuid": "<from claim>", "mode": "suspended" })
```

## 6. Mint an org-member API token while shipping

This is the **current org member's** token, not an end-user credential.

```
start_workflow("identity.api-token.create", {
  "name": "local-dev"
})
```

Copy `token` / `plaintext_token` once. Later metadata:

```
start_workflow("identity.api-token.query", {})
```

Invite a teammate to the Orkestia org (not an app end-user):

```
start_workflow("identity.org-invitation.create", {
  "email": "dev@your-company.example"
})
```
