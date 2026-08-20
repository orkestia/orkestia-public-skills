---
name: orkestia-connections
description: Create, validate, rotate, and use Orkestia provider connections (connection.*) — the org-owned credential objects every provider-touching domain references by UUID. Use when wiring any external provider (AWS, GCP, Azure, GitHub, Stripe, SQL, social platforms, ...) or when a workflow needs a cloud_connection_uuid.
---

# Orkestia connections

A **CloudConnection** is an org-owned, named credential to an external provider. It is the root object of the platform: runner groups take `cloud_connection_uuid`, registry accounts, network accounts, storage provisioning, image pulls, GitLab CI bindings, and AI model bindings all resolve to one. 18 workflow types.

## Shape

One workflow serves every provider: `connection.setup`. Its schema exposes `field_groups` — fill **only** the group matching your `provider_type`. 38 groups exist: aws, gcp, azure, cloudflare, github, gitlab, kubernetes, neon, openai, azure_openai, bedrock, stripe, slack, sql, ifood, ifood_app, meta, meta_ads, linkedin, linkedin_ads, linkedin_community, magalucloud, digitalocean, docker_hub, vercel, sentry, wasender, sap, bling, abacatepay, lovable, route53, google_ads, alibaba, x, youtube, deere, common.

Common fields: `provider_type` (required), `connection_name` (recommended), plus the provider's credential shape — e.g. `role_arn` + `external_ref` (AWS AssumeRole; external id auto-generated when missing), `service_account_json` (GCP), `api_token` (token providers), `client_ref`/`client_secret`/`tenant_ref`/`subscription_ref` (Azure), `host`/`port`/`database`/`dialect`/`ssl_mode` (SQL).

## Wiring flow

```
get_workflow_prerequisites("connection.setup", variant="<provider>")   # 20 variants; guide has platform identity pre-filled
→ start_workflow("connection.setup", {...provider group fields...})
    # internally: validate_credentials → test_connection → persist_connection → sync_resources
```

OAuth providers use a dedicated pair:
- `connection.oauth-start` — begins the authorization-code flow, returns authorize URL + state.
- `connection.oauth-exchange` — trades the code for tokens and runs `connection.setup` for you.

## Lifecycle & reads

| Workflow | Purpose |
|---|---|
| `connection.query` / `connection.get` | List org connections / fetch one (read-only) |
| `connection.validate` | Re-test connectivity, update stored status |
| `connection.rotate.credentials` | Validate + test replacement credentials, swap, mark active |
| `connection.disconnect` | Scrub secrets and soft-delete the record |
| `connection.<provider>.sync-assets` | Refresh provider assets: Meta pages + IG accounts, Meta Ads accounts, LinkedIn ACLs, LinkedIn Community, YouTube channels, John Deere orgs |
| `data.connection.sync_dns` / `prune_dns` | Sync DNS zones/records into the platform; prune ones deleted upstream |

## Gotchas

- `connection.query` supports filtering (e.g. `filters: {connection_type: ["gitlab"]}`) — other schemas use it as a picker source.
- GitHub has three credential paths (PAT `api_token`, OAuth `access_token`, App `installation_ref`) — see the `orkestia-github` skill.
- Sub-steps `connection.validate_credentials` / `test_connection` / `persist_connection` / `sync_resources` are DAG internals; start `connection.setup`, not them.
