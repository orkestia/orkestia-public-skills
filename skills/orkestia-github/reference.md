# GitHub workflow map

Grouped by job. Re-list with `list_workflow_types(prefix="github.")` before relying on a name. Snapshot 2026-08-31.

**Start** = human/agent entry. **Internal** = DAG child or webhook ingest — do not start unless you are debugging a stuck parent.

## Wire credentials

| Type | Role |
|---|---|
| `connection.setup` (`provider_type=github`) | **Start.** PAT `api_token`, OAuth `access_token`, App `installation_ref`. Prerequisites: `get_workflow_prerequisites("connection.setup", variant="github")`. |
| `connection.query` | **Start** (`read_only`). Filter `connection_type: "github"`. |
| `connection.oauth-start` / `connection.oauth-exchange` | **Start** for the OAuth browser path (`provider_type="github"`). See `orkestia-connections`. |
| `connection.validate` / `connection.rotate.credentials` / `connection.disconnect` | Lifecycle. See `orkestia-connections`. |

## Auth and App installation

| Type | Role |
|---|---|
| `github.auth.validate_token` | **Start** (`read_only`). Validate PAT/org token. Schema currently has no inputs — re-read before start. |
| `github.auth.validate_installation` | **Start.** Mint App installation token (`installation_id`). |
| `github.installation.permission_readiness` | **Start.** Refresh/check delivery permissions for `repository`. |
| `github.installation-finalize` | **Start** after the signed install webhook arrived. Links installation → org. |
| `github.installation.parse_webhook` | **Start** (`read_only`). Normalize an installation webhook payload. |
| `github.installation` | **Internal** webhook DAG: validate → sync installation → sync repositories → complete. |
| `github.installation-validate` / `-sync-installation` / `-sync-repositories` / `-complete` | **Internal** DAG steps. |

## Repos, files, refs

| Type | Role |
|---|---|
| `github.repos.list_repos` | **Start** (`read_only`). `owner`, optional `is_org`, `repo_type`, `per_page`. |
| `github.repos.get_repo` | **Start** (`read_only`). `owner`, `repo`. |
| `github.code.get_file` | **Start** (`read_only`). Decoded file; `missing_ok` defaults true. |
| `github.code.get_blob` | **Start** (`read_only`). Decoded blob by SHA (files > 1MB). |
| `github.code.get_tree` | **Start** (`read_only`). Recursive tree at `ref`, optional `path`. |
| `github.code.create_branch` | **Start.** `branch_name` from `from_ref`. |
| `github.code.update_file` | **Start.** Create/update; pass blob `sha` when updating. |
| `github.code.delete_file` | **Start.** Delete a file. |
| `github.code.delete_branch` | **Start.** Delete a branch. |
| `github.refs.resolve` | **Start** (`read_only`). `ref_kind`: `branch` \| `tag` \| `latest_release`. |
| `github.refs.delete_ref` | **Start.** Delete a branch or tag ref. |

## Pull requests

| Type | Role |
|---|---|
| `github.pulls.create_pr` | **Start.** `owner`, `repo`, `title`, `head`, `base`. |
| `github.pulls.get_pr` | **Start** (`read_only`). `owner`, `repo`, `pr_number`. |
| `github.pulls.list_prs` | **Start** (`read_only`). Optional `state`: `open` \| `closed` \| `all`. |
| `github.pulls.list_pr_files` | **Start** (`read_only`). Bounded diffs; honor `complete`. |
| `github.pulls.review_pr` | **Start** (App). `review_event`: `APPROVE` \| `REQUEST_CHANGES` \| `COMMENT`. |
| `github.pulls.merge_pr` | **Start.** Requires `expected_head_sha` + `approval_receipt`. |
| `github.pulls.close_pr` | **Start.** Close without merging. |
| `github.pulls.set_draft` | **Start.** Draft ↔ ready. |
| `github.pulls.create_exact_pr` | **Start.** Exact published-head verification (ticket git-delivery). |
| `github.pulls.get_exact_pr` | **Start.** Normalized snapshot for delivery (not marked `read_only`). |

## Actions and checks

| Type | Role |
|---|---|
| `github.actions.trigger_workflow` | **Start** (App). `workflow` = filename or numeric id. |
| `github.actions.get_job_log_tail` | **Start.** `github_job_ref` integer. |
| `github.checks.evaluate_ref` | **Start** (`read_only`). Checks + statuses for one SHA. |

## Releases

| Type | Role |
|---|---|
| `github.releases.create_release` | **Start** (App). `repository` + `tag_name`. Connection UUID ignored; resolved by owner. |
| `github.releases.previous_compare` | Compare previous release/tag with current. |

## Issues and labels

| Type | Role |
|---|---|
| `github.labels.create` | **Start.** Idempotent label create (`name`, `color` 6-hex). |
| `github.issues.add_labels` | **Start.** Apply labels to issue or PR (`issue_number`). |

Webhook `github.label` / `-validate` / `-sync` / `-complete` are ingestion, not these operations.

## Git broker leases (do not start from chat)

Issued to the trusted publication/cleanup broker used by ticket git-delivery (`orkestia-tickets`):

- `github.git.credential-lease`
- `github.git.cleanup-credential-lease`
- `github.git.repository-credential-lease`

## Projects V2 — start these

Shared envelope: `owner`, `owner_type` (`ORGANIZATION` \| `USER`), `project_number` / `project_node_ref`, optional `github_connection_uuid`, `dry_run`.

| Type | Role |
|---|---|
| `github.project.list` | List projects for an owner. |
| `github.project.get` | Fetch one project. |
| `github.project.setup` | **Featured** DAG: get → upsert (ensure exists). |
| `github.project.sync` | DAG: upsert → repository links → access. Start this to sync a project. |
| `github.project.upsert` | Create or update a project (also a setup/sync step). |
| `github.project.close` / `github.project.delete` | Close or delete. |
| `github.project-item.add` | Add issue/PR (`content_node_ref`). |
| `github.project-item.add-draft` | Add draft issue (`draft_issue`). |
| `github.project-item.list` / `.get` | List or fetch items. |
| `github.project-item.update` / `.update-field` / `.upsert` | Mutate items/fields. |
| `github.project-item.archive` / `.restore` / `.delete` | Archive lifecycle. |
| `github.project-access.list` | List grants. |
| `github.project-access.sync` | DAG: list → `github.project-user.link` → `github.project-team.link`. |
| `github.project-user.link` / `.unlink` | Single user grant. Prefer `.sync` for a desired set. |
| `github.project-team.link` / `.unlink` | Single team grant. |
| `github.project-repository.link` / `.unlink` / `.list` | Repo links. Prefer `github.project.sync` for reconcile. |
| `github.project-field.list` / `.get` / `.create` / `.update` / `.upsert` / `.delete` | Custom fields. |
| `github.project-view.list` / `.get` | Views (read). |

## Projects V2 — do not start as user commands

Webhook / fan-out / teardown internals:

- `github.project.sync-from-webhook`, `github.project-item.sync-from-webhook`, `github.projects-v2-item`
- `github.project.seed`, `github.project.reconcile`, `github.project.teardown`
- `github.project-repository.sync` (child of `github.project.sync`)
- `github.project-view.sync`, `github.project-auto-add.sync`, `github.project-auto-archive.sync`, `github.project-automation.sync`, `github.project-workflow.sync`

## Webhook ingestion (platform-driven)

Do not start. Parent DAG → typical act:

| Parent | Act / downstream |
|---|---|
| `github.push` | `github.push-check-auto-deploy` → `spad.auto-deploy-push`; `github.push-check-gitops`; `staff.dispatch-event-to-actor` |
| `github.pull_request` | `staff.dispatch-event-to-actor` |
| `github.release` | `github.release-check-auto-deploy`; `github.release-check-k8s-targets` → `deploy.release.start`; `github.release-check-gitops`; staff |
| `github.check` | `github.check-sync` |
| `github.create` | `github.create-dispatch-staff-event` |
| `github.delete` | audit sync |
| `github.deployment` | audit sync |
| `github.label` | audit sync |
| `github.repository` | `github.repository-sync`, `github.repository-update-connection` |
| `github.workflow-dispatch` | `github.workflow-dispatch-select-runner`, `github.workflow-dispatch-launch` |
| `github.workflow-job` | `github.workflow-job-handle` → `runner.dispatch-from-job-queued` / claim-watch / `runner.execution-stop-*` |
| `github.workflow-run` | `github.workflow-run-handle-completion` |
| `github.installation` | see Auth section |
| `github.projects-v2-item` | Projects item webhook |

Each parent has `-validate` / `-complete` (and often `-sync`) children — those are DAG steps.

`spad.*` and `deploy.*` are not covered by this pack. Discover with `list_workflow_types(prefix="spad.")` or `prefix="deploy."`. Runners: `orkestia-runners`. Staff: `orkestia-staff`.
