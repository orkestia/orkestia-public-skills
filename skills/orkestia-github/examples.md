# GitHub worked examples

Call `whoami()` first. Do not pass `organization_uuid`. Re-read `get_workflow_schema` if a field name here disagrees with the live schema.

## 1. Wire GitHub with a PAT

```
get_workflow_prerequisites("connection.setup", variant="github")
get_workflow_schema("connection.setup")
```

Start:

```json
{
  "workflow_type": "connection.setup",
  "initial_data": {
    "provider_type": "github",
    "connection_name": "company-github",
    "api_token": "<github_pat>"
  }
}
```

For GHCR later, the PAT must include `read:packages` (and `repo` if packages or repos are private). Then use `orkestia-registry-network`.

**App instead of PAT:** same workflow, replace `api_token` with `installation_ref` (integer installation id). After GitHub delivers the signed install webhook, start `github.installation-finalize`. Then check a repo:

```json
{
  "workflow_type": "github.installation.permission_readiness",
  "initial_data": {
    "repository": "acme/api"
  }
}
```

## 2. List repos, read a file, branch, update a file

```json
{
  "workflow_type": "github.repos.list_repos",
  "initial_data": {
    "owner": "acme",
    "is_org": true,
    "repo_type": "all",
    "per_page": 30
  }
}
```

Read `README.md` on `main` (`read_only`; `missing_ok` defaults true):

```json
{
  "workflow_type": "github.code.get_file",
  "initial_data": {
    "owner": "acme",
    "repo": "api",
    "path": "README.md",
    "ref": "main"
  }
}
```

Branch from `main`, then commit a file. Use `sha` from `get_file` when updating an existing blob.

```json
{
  "workflow_type": "github.code.create_branch",
  "initial_data": {
    "owner": "acme",
    "repo": "api",
    "branch_name": "docs/readme-tweak",
    "from_ref": "main"
  }
}
```

```json
{
  "workflow_type": "github.code.update_file",
  "initial_data": {
    "owner": "acme",
    "repo": "api",
    "path": "README.md",
    "content": "# API\n\nUpdated via Orkestia.\n",
    "commit_message": "docs: tweak README",
    "branch": "docs/readme-tweak",
    "sha": "<blob_sha_from_get_file>"
  }
}
```

## 3. Open, review, and merge a PR (governance required)

Open (owner/repo/head/base):

```json
{
  "workflow_type": "github.pulls.create_pr",
  "initial_data": {
    "owner": "acme",
    "repo": "api",
    "title": "docs: tweak README",
    "head": "docs/readme-tweak",
    "base": "main",
    "body": "Small README update."
  }
}
```

Review through the App (`repository` + `pull_number`):

```json
{
  "workflow_type": "github.pulls.review_pr",
  "initial_data": {
    "repository": "acme/api",
    "pull_number": 42,
    "review_event": "COMMENT",
    "review_body": "Looks consistent with the file update.",
    "dry_run": true
  }
}
```

Merge **only** with a real `approval_receipt` from the governing workflow (ticket software-delivery / policy). Do not invent the receipt. `expected_head_sha` must be the PR head:

```json
{
  "workflow_type": "github.pulls.merge_pr",
  "initial_data": {
    "repository": "acme/api",
    "pull_number": 42,
    "expected_head_sha": "<pr_head_sha>",
    "merge_method": "squash",
    "approval_receipt": "<json from the governing approval workflow>",
    "dry_run": true
  }
}
```

**Exact-OID (ticket git-delivery):** after the broker confirms the published ref OID, open with `github.pulls.create_exact_pr` (`repository`, `head_ref`, `base_ref`, `expected_head_sha`, `title`). Snapshot with `github.pulls.get_exact_pr`. See `orkestia-tickets`.

## 4. Dispatch Actions and evaluate checks for a SHA

```json
{
  "workflow_type": "github.refs.resolve",
  "initial_data": {
    "owner": "acme",
    "repo": "api",
    "ref_kind": "branch",
    "ref": "main"
  }
}
```

```json
{
  "workflow_type": "github.actions.trigger_workflow",
  "initial_data": {
    "repository": "acme/api",
    "workflow": "ci.yml",
    "ref": "main",
    "inputs": {},
    "dry_run": true
  }
}
```

Evaluate the exact commit (safe `read_only`):

```json
{
  "workflow_type": "github.checks.evaluate_ref",
  "initial_data": {
    "repository": "acme/api",
    "commit_sha": "<sha_from_refs.resolve>"
  }
}
```

Job logs (numeric GitHub job id):

```json
{
  "workflow_type": "github.actions.get_job_log_tail",
  "initial_data": {
    "repository": "acme/api",
    "github_job_ref": 123456789,
    "max_lines": 200
  }
}
```

## 5. Create a release through the App

```json
{
  "workflow_type": "github.releases.create_release",
  "initial_data": {
    "repository": "acme/api",
    "tag_name": "v1.2.3",
    "target_commitish": "<exact_sha>",
    "name": "v1.2.3",
    "generate_release_notes": true,
    "dry_run": true
  }
}
```

Omit `github_connection_uuid` — the workflow resolves the App installation from the repository owner.

## 6. List a Project, add an item, sync access

```json
{
  "workflow_type": "github.project.list",
  "initial_data": {
    "owner": "acme",
    "owner_type": "ORGANIZATION"
  }
}
```

Ensure the board exists (featured DAG), then add an issue/PR node:

```json
{
  "workflow_type": "github.project.setup",
  "initial_data": {
    "owner": "acme",
    "owner_type": "ORGANIZATION",
    "title": "Delivery",
    "dry_run": true
  }
}
```

```json
{
  "workflow_type": "github.project-item.add",
  "initial_data": {
    "owner": "acme",
    "owner_type": "ORGANIZATION",
    "project_number": 1,
    "content_node_ref": "<issue_or_pr_node_id>",
    "dry_run": true
  }
}
```

Reconcile user/team grants via the access DAG (do not start `github.project-user.link` unless you are doing a single grant). `desired_access` is a list — read the schema and a prior `github.project-access.list` result for item shape; do not invent grant objects.

```json
{
  "workflow_type": "github.project-access.sync",
  "initial_data": {
    "owner": "acme",
    "owner_type": "ORGANIZATION",
    "project_number": 1,
    "dry_run": true
  }
}
```

To sync project configuration (upsert + repo links + access) start `github.project.sync`, not `github.project-repository.sync` or webhook types like `github.projects-v2-item`.
