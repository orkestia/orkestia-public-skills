---
name: orkestia-github
description: >-
  Wire GitHub into Orkestia (PAT, OAuth, or GitHub App) and operate repositories,
  files, branches, pull requests, Actions, checks, releases, and GitHub Projects V2.
  Use when setting up a github connection, opening or merging a PR, triggering
  workflow_dispatch, reading job logs, evaluating checks for a SHA, managing
  Projects, or explaining how GitHub webhooks drive runners, deploys, and staff.
---

# GitHub in Orkestia

Operate GitHub through public MCP only. Discover with `list_workflow_types(prefix="github.")` and read `get_workflow_schema` before every start. Catalog rows change; names in this skill are a 2026-08-31 snapshot — re-list if a start fails with "not registered".

## When to load

Load this skill when the user wants to:

- Connect GitHub (PAT, OAuth token, or GitHub App installation)
- List repos, read or write files, create branches
- Open, review, or merge a pull request (including exact-OID delivery)
- Trigger Actions `workflow_dispatch`, tail job logs, or evaluate checks for one SHA
- Create a GitHub release through an App connection
- List, set up, or add items to GitHub Projects V2
- Understand how GitHub webhooks dispatch runners, deploys, or staff actors

Also load `orkestia-mcp-operating-loop` if this is the first Orkestia MCP turn.

## Use cases

1. **Wire GitHub** — choose PAT vs OAuth vs App, then `connection.setup` with `provider_type="github"`.
2. **Repos and code** — list repos, read a file, create a branch, update a file.
3. **Pull requests** — open, review, merge; exact-OID PRs for ticket git-delivery.
4. **Actions and checks** — `workflow_dispatch`, job log tails, checks for an exact SHA.
5. **Releases** — create a release + tag through an App connection.
6. **Projects V2** — list/get/setup a project, add an item, sync access.
7. **Webhook ingestion** — platform-driven pipelines you rarely start (push, PR, release, check, workflow-job, auto-deploy, staff).

## How to

Every recipe: `whoami()` → `list_workflow_types(prefix="github.")` → `get_workflow_schema(<type>)` → `start_workflow` → `watch_workflow`. Do **not** pass `organization_uuid` unless the schema declares it and it matches `whoami` (MCP injects org context).

### 1. Wire GitHub

**Always** go through `connection.setup` with `provider_type="github"`. First:

```
get_workflow_prerequisites("connection.setup", variant="github")
```

Then `get_workflow_schema("connection.setup")` and fill **only** the `github` field group plus `provider_type` and a `connection_name`. GitHub group fields: `api_token`, `access_token`, `installation_ref`, `refresh_token`, `expires_at`, `scope`.

Pick **one** credential path:

| Path | When | `connection.setup` fields |
|---|---|---|
| **PAT** | Metadata, files, PRs, GHCR inventory | `api_token` |
| **OAuth** | User-granted token with refresh | `access_token` (+ optional `refresh_token`, `expires_at`, `scope`). Alternatively `connection.oauth-start` / `connection.oauth-exchange` with `provider_type="github"` — see `orkestia-connections`. |
| **GitHub App** | Actions trigger, PR review, releases, self-hosted runners, webhook ingestion | `installation_ref` (installation id) |

**GHCR:** include `read:packages`, and `repo` when packages or backing repos are private. Registry sync lives in `orkestia-registry-network` (`registry.github-account-sync`).

**App path (after the App is installed on the target account):**

1. `start_workflow("connection.setup", {provider_type: "github", connection_name: "...", installation_ref: <id>})`.
2. GitHub's signed installation webhook runs `github.installation` (DAG: `github.installation-validate` → `github.installation-sync-installation` → `github.installation-sync-repositories` → `github.installation-complete`). Do **not** start that DAG yourself.
3. `github.installation-finalize` links the installation to your org. Optional inputs: `github_installation_ref`, `setup_action`, `state` (SPA nonce), `code` (OAuth-on-install). Outputs include `installation_uuid` and `connection_uuid`.
4. `github.installation.permission_readiness` with `repository` (`owner/name`) — optional `required_permissions` dict. Read `ready` and `missing_permissions`.
5. `github.auth.validate_installation` with `installation_id` mints an installation access token.

Find existing GitHub connections with `connection.query` and `filters: {connection_type: "github"}`. Full connection lifecycle: `orkestia-connections`.

### 2. List repos / read a file / create a branch / update a file

All of these need a working GitHub connection in the org.

1. **List repos** — `github.repos.list_repos` (`read_only`): required `owner`; optional `is_org`, `repo_type` (`all` \| `public` \| `private` \| `forks`), `per_page` (1–100).
2. **One repo** — `github.repos.get_repo`: `owner`, `repo`.
3. **Read a file** — `github.code.get_file` (`read_only`): `owner`, `repo`, `path`; optional `ref`, `missing_ok` (default true), `default_content`. For files > 1MB use `github.code.get_blob`. For a tree listing use `github.code.get_tree` (`owner`, `repo`, `ref`; optional `path`).
4. **Create a branch** — `github.code.create_branch`: `owner`, `repo`, `branch_name`, `from_ref` (SHA or existing branch).
5. **Create or update a file** — `github.code.update_file`: `owner`, `repo`, `path`, `content`, `commit_message`; pass `sha` when updating an existing blob; optional `branch`.

Resolve a branch/tag/`latest_release` to a SHA with `github.refs.resolve` (`read_only`): `owner`, `repo`, `ref_kind`, optional `ref`.

### 3. Open, review, merge a PR

Field names differ by workflow — always read the schema. `create_pr` / `get_pr` use `owner` + `repo`; merge/review/exact-OID use `repository` (`owner/name`) + `pull_number`.

1. **Open** — `github.pulls.create_pr`: `owner`, `repo`, `title`, `head`, `base`; optional `body`, `draft`.
2. **Read** — `github.pulls.get_pr` (`read_only`): `owner`, `repo`, `pr_number`. List: `github.pulls.list_prs` (`owner`, `repo`, optional `state`). Diffs: `github.pulls.list_pr_files` (`repository`, `pull_number`). If `complete` is false, do not treat the patch set as full.
3. **Review** — `github.pulls.review_pr` (App connection): `repository`, `pull_number`, `review_event` (`APPROVE` \| `REQUEST_CHANGES` \| `COMMENT`), `review_body`. Optional `commit_sha`, `policy_receipt`, `dry_run`.
4. **Merge** — `github.pulls.merge_pr`. Required: `repository`, `pull_number`, `expected_head_sha`, **`approval_receipt`** (JSON). Optional `merge_method` (`merge` \| `squash` \| `rebase`), `commit_title`, `commit_message`, `dry_run`. The caller must **prove** policy and approval. Agents cannot skip governance by omitting `approval_receipt` or inventing a receipt.
5. Close without merge: `github.pulls.close_pr`. Draft toggle: `github.pulls.set_draft`.

**Exact-OID delivery** (ticket git-delivery — see `orkestia-tickets`):

- `github.pulls.create_exact_pr` opens only after the published head SHA equals `expected_head_sha`. Required: `repository`, `head_ref`, `base_ref`, `expected_head_sha`, `title`.
- `github.pulls.get_exact_pr` returns a normalized snapshot (`head_sha`, `mergeable`, labels, …). Required: `repository`, `pull_number`.

Do not start `github.git.credential-lease`, `github.git.cleanup-credential-lease`, or `github.git.repository-credential-lease` — those issue one-time credentials to the trusted publication/cleanup broker.

### 4. Trigger Actions and evaluate checks

App connection required for dispatch.

1. `github.actions.trigger_workflow`: `repository`, `workflow` (filename like `ci.yml` or numeric id); optional `ref`, `inputs` (JSON object), `dry_run`.
2. `github.actions.get_job_log_tail`: `repository`, `github_job_ref` (integer job id); optional `max_lines`.
3. `github.checks.evaluate_ref` (`read_only`): `repository`, `commit_sha`; optional `required_check_names`, `allow_no_checks`. Read `green`, `failed_checks`, `pending_checks`, `missing_checks`.

Resolve the SHA first with `github.refs.resolve` when the user named a branch or tag.

### 5. Create a release (App connection)

`github.releases.create_release`: required `repository`, `tag_name`. Optional `target_commitish`, `name`, `body`, `draft`, `prerelease`, `make_latest` (`true` \| `false` \| `legacy`), `generate_release_notes`, `dry_run`. `github_connection_uuid` is ignored — the App installation is resolved from the repository owner.

### 6. GitHub Projects V2

Projects share a large input envelope. Identify a project with `owner` + `owner_type` (`ORGANIZATION` or `USER`) and `project_number` or `project_node_ref`. Optional `github_connection_uuid`. Prefer `dry_run` before writes.

**Start these (human / agent entry points):**

1. **List** — `github.project.list` with `owner` and `owner_type`.
2. **Get** — `github.project.get` with `project_number` or `project_node_ref`.
3. **Ensure exists** (featured DAG) — `github.project.setup`: `github.project.get` then `github.project.upsert`. Pass `owner`, `owner_type`, `title` (and `project_number` if known).
4. **Sync configuration** — `github.project.sync` (DAG: upsert → `github.project-repository.sync` → `github.project-access.sync`). Start this parent, not the child DAGs.
5. **Add an item** — `github.project-item.add` with project identity plus `content_node_ref` (issue/PR). Draft cards: `github.project-item.add-draft` with `draft_issue`. List items: `github.project-item.list`.
6. **Sync access** — `github.project-access.sync` (DAG: list grants → `github.project-user.link` → `github.project-team.link`) with `desired_access`.

**Do not start** webhook/internal sync as if they were user commands: `github.project.sync-from-webhook`, `github.project-item.sync-from-webhook`, `github.projects-v2-item`, `github.project.seed`, `github.project.reconcile`, `github.project.teardown`, `github.project-auto-add.sync`, `github.project-auto-archive.sync`, `github.project-automation.sync`, `github.project-workflow.sync`, `github.project-view.sync`. Discover extras with `list_workflow_types(prefix="github.project")`.

### 7. Webhook pipelines (platform-driven)

These DAGs ingest GitHub App webhooks. You almost never `start_workflow` them. Shape is validate → sync/audit → act → complete.

| Event DAG | What the "act" layer does |
|---|---|
| `github.push` | `github.push-check-auto-deploy` → `spad.auto-deploy-push`; `github.push-check-gitops`; `staff.dispatch-event-to-actor` |
| `github.pull_request` | `staff.dispatch-event-to-actor` |
| `github.release` | `github.release-check-auto-deploy`; `github.release-check-k8s-targets` → `deploy.release.start` per matched target; `github.release-check-gitops`; staff dispatch |
| `github.check` | audit sync only |
| `github.workflow-job` | `github.workflow-job-handle`: `queued` → `runner.dispatch-from-job-queued`; `in_progress` → claim-watch; `completed` → `runner.execution-stop-*` (frees the capacity slot) |
| `github.workflow-dispatch` | `github.workflow-dispatch-select-runner` / `-launch` (ephemeral runners) |
| `github.workflow-run` | `github.workflow-run-handle-completion` (stop ephemeral runner) |
| `github.create` | `github.create-dispatch-staff-event` (tag/branch create → staff bindings) |
| `github.projects-v2-item` | Projects item webhook |

Also present: `github.delete`, `github.deployment`, `github.label`, `github.repository`, `github.installation` (see recipe 1).

Runner dispatch: `orkestia-runners`. Staff event bindings: `orkestia-staff`. `spad.*` and `deploy.*` exist in the catalog but this pack has no dedicated skills — `list_workflow_types(prefix="spad.")` / `prefix="deploy."` if you need them.

## Object model

- **CloudConnection** (`provider_type=github`) — credential root. PAT / OAuth / App.
- **GitHub App installation** — linked by `github.installation-finalize` (`installation_uuid`, `connection_uuid`). There is **no** list workflow for `github_installation_uuid`; runner groups need the caller to supply it from the org's GitHub connection.
- **Repository / ref / file** — `github.repos.*`, `github.code.*`, `github.refs.*`.
- **Pull request** — `github.pulls.*`. Exact-OID variants exist for delivery orchestration.
- **Checks / Actions job** — `github.checks.evaluate_ref`, `github.actions.*`.
- **Release** — `github.releases.create_release` (plus webhook `github.release`).
- **Issue labels** — `github.labels.create` (idempotent); `github.issues.add_labels` (PRs are issues for labeling).
- **Projects V2** — project, items, fields, views, access (user/team), repository links, automation/workflow/auto-add/auto-archive.
- **Git broker lease** — `github.git.*` (trusted publication/cleanup only).
- **Auth helpers** — `github.auth.validate_token` (PAT/org token; `read_only`; schema has no inputs — re-read before start), `github.auth.validate_installation`.

## Day-to-day reads

Safe to start when `read_only: true` (confirm on the list row / schema):

- `github.repos.list_repos`, `github.repos.get_repo`
- `github.code.get_file`, `github.code.get_blob`, `github.code.get_tree`
- `github.pulls.get_pr`, `github.pulls.list_prs`, `github.pulls.list_pr_files`
- `github.checks.evaluate_ref`
- `github.refs.resolve`
- `github.auth.validate_token`
- `github.installation.parse_webhook`

`github.pulls.get_exact_pr`, `github.actions.get_job_log_tail`, and `github.project.list` / `.get` are **not** marked `read_only` — read the schema and confirm intent before starting.

## Gotchas

- `github.pulls.merge_pr` requires `approval_receipt` and `expected_head_sha`. Governance cannot be skipped.
- `github.pulls.list_pr_files` `complete=false` means omitted or truncated patches — do not approve from that snapshot alone.
- `github_installation_uuid` has no list workflow.
- GHCR needs `read:packages` (+ `repo` if private) — `orkestia-registry-network`.
- Webhook DAGs are ingestion internals even when `featured: true`. Prefer direct operations (`github.pulls.*`, `github.actions.*`, `github.project.setup`) over starting `github.push` / `github.workflow-job`.
- `organization_uuid` is injected from `whoami`. Do not ask the user for it.
- Re-read `get_workflow_schema` — `owner`/`repo` vs `repository`, `pr_number` vs `pull_number` are not interchangeable.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, start, watch, recovery
- `orkestia-connections` — `connection.setup` / query / rotate / disconnect
- `orkestia-tickets` — git-work and exact-OID git-delivery (`create_exact_pr` / `get_exact_pr`)
- `orkestia-runners` — `runner.dispatch-from-job-queued`, execution-stop, GitHub runner groups
- `orkestia-staff` — event bindings fed by `github.create-dispatch-staff-event` / staff dispatch steps
- `orkestia-registry-network` — GHCR via `registry.github-account-sync`

## Additional resources

- Job-grouped workflow map: [reference.md](reference.md)
- Worked `initial_data` examples: [examples.md](examples.md)
