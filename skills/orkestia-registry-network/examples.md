# Registry & network — examples

Omit `organization_uuid` (token-injected). Replace placeholders. Do not echo secrets.

## Bind ECR and full-sync

Assume `connection.query` already returned an AWS `connection_uuid`.

```
start_workflow("data.registry.account.persist", {
  "cloud_connection_uuid": "<aws-connection-uuid>",
  "name": "prod-ecr",
  "backend_type": "ecr",
  "region": "us-east-1",
  "project_or_account_ref": "123456789012"
})
# registry_account_uuid

start_workflow("registry.account-sync-all", {
  "registry_account_uuid": "<registry-account-uuid>"
})
watch_workflow(<workflow_id>)
```

One-account repository reconcile only (no fan-out):

```
start_workflow("registry.account-sync", {
  "registry_account_uuid": "<registry-account-uuid>"
})
```

## GHCR (GitHub token or App)

Backing connection: `orkestia-connections` + `orkestia-github` (`read:packages`, plus `repo` if private).

```
get_workflow_prerequisites("registry.github-account-sync", variant="github_ghcr")
start_workflow("data.registry.account.persist", {
  "cloud_connection_uuid": "<github-connection-uuid>",
  "name": "org-ghcr",
  "backend_type": "github_ghcr",
  "namespace": "acme"
})
start_workflow("registry.github-account-sync", {
  "registry_account_uuid": "<ghcr-account-uuid>"
})
```

## Resolve an image, then list catalog

```
start_workflow("data.registry.account.list", { "backend_type": "github_ghcr" })
start_workflow("data.registry.repository.list", {
  "registry_account_uuid": "<uuid>"
})
start_workflow("registry.image.resolve", {
  "repository_full_name": "ghcr.io/acme/api",
  "tag": "latest"
})
# resolved, registry_image_uuid, registry_image_version_uuid

start_workflow("registry.inventory.read", {
  "registry_account_uuid": "<uuid>",
  "include_images": true,
  "include_versions": true
})
```

Digest form:

```
start_workflow("registry.image.resolve", {
  "reference": "ghcr.io/acme/api@sha256:deadbeef"
})
```

## Kubernetes pull Secret (cluster, not runner-group fields)

```
start_workflow("registry.kubernetes-pull-binding.reconcile", {
  "connection_uuid": "<kubernetes-connection-uuid>",
  "namespaces": ["apps", "jobs"],
  "registry_account_uuid": "<ghcr-account-uuid>",
  "secret_name": "ghcr-pull"
})
```

`MASTER` namespace is refused. Defaults: secret `ghcr-pull`; ServiceAccounts `default` and `relay-runtime`.

## Unsync local catalog

```
start_workflow("data.registry.repository.unsync", {
  "registry_repository_uuid": "<repo-uuid>"
})
start_workflow("data.registry.account.unsync", {
  "registry_account_uuid": "<account-uuid>"
})
```

Provider images are untouched.

## Network account, sync, profile, resolve

```
start_workflow("data.network.account.persist", {
  "cloud_connection_uuid": "<aws-connection-uuid>",
  "backend_type": "aws_vpc",
  "name": "prod-aws-net",
  "region": "us-east-1"
})
# network_account_uuid

start_workflow("network.account-sync-all", {
  "network_account_uuid": "<network-account-uuid>"
})
watch_workflow(<workflow_id>)

start_workflow("data.network.scope.query", {
  "network_account_uuid": "<network-account-uuid>"
})
start_workflow("data.network.segment.query", {})
start_workflow("data.network.security_boundary.query", {})
# no rule bodies in output

start_workflow("data.network.profile.persist", {
  "network_account_uuid": "<network-account-uuid>",
  "name": "runner-private",
  "profile_type": "runner_execution",
  "is_default": true,
  "config": {}
})
# network_profile_uuid — put UUID-only keys in config if you bind segments

start_workflow("data.network.profile.update", {
  "network_profile_uuid": "<profile-uuid>",
  "description": "Private subnets for Fargate"
})

start_workflow("network.profile.resolve", {
  "network_profile_uuid": "<profile-uuid>",
  "required_intent": "private"
})
# target, segment_uuids, readiness
```

## Topology + connectivity plan (read-only)

```
start_workflow("network.topology.discover", {
  "provider": "aws",
  "include_profiles": true,
  "include_segments": true,
  "include_security_boundaries": true
})

start_workflow("network.connectivity.plan", {
  "intent_name": "aws-to-gcp",
  "connectivity_type": "private_vpn",
  "source": {
    "provider": "aws",
    "region": "us-east-1",
    "cidr_blocks": ["10.0.0.0/16"]
  },
  "target": {
    "provider": "gcp",
    "region": "us-central1",
    "cidr_blocks": ["10.8.0.0/16"]
  },
  "require_redundancy": true
})
# supported, blockers, route_plan — does not apply
```

## Unsync network inventory

```
start_workflow("network.scope-unsync", {
  "network_scope_uuid": "<scope-uuid>"
})
start_workflow("network.account-unsync", {
  "network_account_uuid": "<account-uuid>"
})
```

## Hand UUIDs to a runner group

After recipes above:

```
start_workflow("data.registry.account.list", {})
start_workflow("data.network.profile.query", { "profile_type": "runner_execution" })
start_workflow("connection.query", { "filters": { "connection_type": "aws" } })
```

Pass `registry_account_uuid`, `network_profile_uuid`, and optionally `image_pull_cloud_connection_uuid` into `runner.group-creation`. Full group recipe: `orkestia-runners`. Do not start group-creation from this skill's examples.
