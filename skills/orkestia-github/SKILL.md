---
name: orkestia-github
description: Wire GitHub into Orkestia (PAT, OAuth, or GitHub App installation) and operate it — repos, files, branches, pull requests, checks, releases, Actions — plus how GitHub webhooks drive runners, deploys, and staff actors. Use for any github.* workflow or GitHub credential setup.
---

# GitHub in Orkestia

86 workflow types: roughly half are webhook-processing pipelines, half are direct operations you can run.

## Wiring (three credential paths)

All through `connection.setup` with `provider_type="github"` (prerequisites guide: `get_workflow_prerequisites("connection.setup", variant="github")`):

1. **PAT** — pass `api_token`. For GHCR registry workflows include `read:packages` (+ `repo` when packages/repos are private).
2. **OAuth** — pass `access_token` (+ optional `refresh_token`, `expires_at`, `scope`).
3. **GitHub App** — install the Orkestia GitHub App on the target account and pass `installation_ref`. The signed installation webhook runs the `github.installation` DAG; `github.installation-finalize` links the installation to your organization; `github.installation.permission_readiness` refreshes and checks delivery permissions; `github.auth.validate_installation` mints an installation access token.

## Webhook pipelines (platform-driven)

One DAG per event type, each following *validate → sync (audit/DB) → act → complete*: `github.push`, `pull_request`, `release`, `check`, `create`, `delete`, `deployment`, `label`, `repository`, `workflow-dispatch`, `workflow-job`, `workflow-run`. The "act" steps wire GitHub into the platform:

- `github.workflow-job-handle`: `queued` → `runner.dispatch-from-job-queued`; `in_progress` → claim-watch; `completed` → backend `runner.execution-stop-*` (frees the capacity slot).
- `github.workflow-dispatch-select-runner` / `-launch`: route + launch ephemeral runners by rules.
- `github.push-check-auto-deploy` → `spad.auto-deploy-push`; `github.release-check-k8s-targets` → `deploy.release.start` per matched DeploymentTarget.
- `github.create-dispatch-staff-event`: feeds tag/branch creation into Staff event bindings.

These are ingestion internals — you rarely start them yourself.

## Direct operations

| Area | Workflows |
|---|---|
| Repos & code | `repos.list_repos`, `repos.get_repo`, `code.get_file`, `code.update_file`, `code.delete_file`, `code.create_branch`, `code.delete_branch`, `refs.delete_ref` |
| Pull requests | `pulls.create_pr`, `get_pr`, `list_prs`, `list_pr_files` (bounded diffs), `review_pr`, `set_draft`, `close_pr`, `merge_pr` |
| Exact-OID delivery | `pulls.create_exact_pr` (opens only after exact published-head verification), `pulls.get_exact_pr` (normalized snapshot for delivery orchestration) |
| CI & checks | `actions.trigger_workflow` (workflow_dispatch), `actions.get_job_log_tail`, `checks.evaluate_ref` (checks + statuses for one exact SHA) |
| Releases | `releases.create_release` (creates release + tag via App connection) |

## Gotchas

- `merge_pr` requires the caller to **prove** policy and approval requirements — governance cannot be skipped by agents.
- Read-only rows (`get_file`, `get_pr`, `list_*`, `checks.evaluate_ref`) are safe to start directly.
- `github_installation_uuid` (used by runner groups) has no list workflow — the caller must supply it from the org's GitHub connection.
