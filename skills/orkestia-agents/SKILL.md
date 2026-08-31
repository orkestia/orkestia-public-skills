---
name: orkestia-agents
description: Configure and run Orkestia agents — AgentConfigs with models, budgets, and memory; attach skills, trusted guidance packages, and MCP servers; launch and watch sessions on runner infrastructure; track cost. Use for anything under agents.* or data.agents.*, and as the machinery beneath staff actors.
---

# Orkestia agents

Where Staff is the org chart (**Actors**), agents is the **machinery**: reusable **AgentConfigs**, attached capabilities, and **sessions** that run on runner infrastructure. Hiring (`staff.hire-actor`) binds a config into the org — it does not create one.

Do not pass `organization_uuid` in `initial_data`. Prefer `featured: true`. Do **not** start DAG internals `agents._session-launch.*`, `agents._infra-cost-sync.*`, or `agents._ft-dataset.*` — same rule as the operating loop: skip non-featured sub-steps; start the parent (`agents.session-launch`, `agents.infra-cost-sync`, `agents.ft-dataset.build`).

## When to load

Load this skill when the user wants to:

- Create or clone an AgentConfig (model, budgets, memory, runner group)
- Attach skills, import/trust/sync guidance packages, or register MCP servers
- Launch, watch, stop, or rate a session
- Enable or disable agent support on a runner group
- Inspect session or org cost / `budget_usd` ceilings
- Wire a bounded end-user agent on an identity app
- Understand tool-policy, tool-catalog, or model-capacity

Load `orkestia-staff` when the work is hiring, dispatch, Cockpit, or the founder queue.

## Use cases

1. **Prerequisites and create** — enabled AI provider profile, then `agent-config.create` (fast path: `draft-from-description`).
2. **Capabilities** — attach a skill; import → trust → sync a guidance package; register an MCP server (OAuth discover-auth, test, refresh catalog).
3. **Launch a session** — start `agents.session-launch` (not `_session-launch` internals), then watch / stop / rate.
4. **Runner group** — `agents.runner-group.enable` / `disable` (disable guarded by active sessions).
5. **Cost** — `budget-status`, `session-cost`, `cost-by-config`; what happens at `budget_usd`.
6. **End-user bounded agent** — `identity.app.set-end-user-agent` then `agents.end-user.ask` / `ask-stream`.
7. **Tool surfaces** — `tool-catalog` (what may be called), `tool-policy` (may it run), `model-capacity` (RPM/TPM).

## How to recipes

### 1. Prerequisites, then create an AgentConfig

1. `whoami()`. `list_workflow_types(prefix="agents.")` and `prefix="data.agents."`.
2. Confirm **≥1 enabled AI provider profile**:

```
start_workflow("data.ai-provider.list", { "enabled_only": true })
```

Each row: `ai_provider_config_uuid`, `connection_uuid`, `default_model`, `is_default`, `enabled`. `agents.agent-config.create` has `has_prerequisites: true` (variant `ai-provider-profile`). Call `get_workflow_prerequisites("agents.agent-config.create", variant="ai-provider-profile")` before create. Omit model fields to use the org default enabled profile. Pin with `ai_provider_config_uuid` or `model_profile`; `model_name` must match that profile's `default_model`. Optional `model_connection_uuid` only when pinning by connection.

3. **Fast path** — draft fields from a job description (does not persist; no `agent_config_uuid`):

```
start_workflow("agents.agent-config.draft-from-description", {
  "description": "<job the agent should do>"
})
```

Output: `name`, `system_prompt`, `model_name`, `memory_enabled`, `memory_strategy`, `memory_top_k`, `notes`. Feed those into create.

4. Persist. Required caller field: `name`. Read schema first.

```
start_workflow("agents.agent-config.create", {
  "name": "<from draft or chosen>",
  "description": "<optional>",
  "system_prompt": "<optional>",
  "ai_provider_config_uuid": "<optional pin>",
  "model_name": "<must match profile default_model>",
  "max_steps": 40,
  "max_tokens_per_step": 4096,
  "budget_usd": 5.0,
  "memory_enabled": true,
  "memory_write_enabled": false,
  "memory_strategy": "pack",
  "memory_top_k": 10,
  "runner_group_uuid": "<agent-enabled group>",
  "runtime_profile": "workspace-probe-v1"
})
```

Knobs from schema:

- **Limits:** `max_steps`, `max_tokens_per_step`, `budget_usd` (per-session USD ceiling).
- **Memory:** `memory_enabled` (read); `memory_write_enabled` (distill finished sessions — defaults off; a bad writer pollutes later recall). `memory_strategy`: `last_k` | `importance` | `pack` (ranked against the task, fitted to a token budget). `memory_top_k` typically 5–30.
- **Runtime:** `runner_group_uuid` (agent-eligible group), `runner_image`, `runtime_profile` — `workspace-probe-v1` is the safe default; `software-development-v1` is accepted only by a cloudless DevKit group when org code-execution policy permits.

Also: `agents.agent-config.update`, `clone`, `delete` (soft), `purge` (hard, no sessions). Reads: `data.agents.list-configs`, `data.agents.get-config`.

### 2. Attach skill, guidance package, MCP server

**Skill**

```
start_workflow("agents.skill.create", {
  "name": "<skill name>",
  "kind": "<confirm via schema>"
})
start_workflow("agents.skill.validate", { "skill_uuid": "<from create>" })
start_workflow("agents.agent-config.skill-attach", {
  "agent_config_uuid": "<uuid>",
  "agent_skill_uuid": "<uuid>"
})
```

Detach: `agents.agent-config.skill-detach`. Update/delete: `agents.skill.update` / `delete`. List: `data.agents.list-skills`. Confirm `kind` (and webhook vs `workflow_type` fields) via schema — do not invent kinds.

**Guidance package** (provider-blind, pinned Git object, versions immutable)

```
start_workflow("agents.skill-package.import", {
  "version": 1,
  "package_version": "1.0.0",
  "source_repository_uuid": "<repo uuid>",
  "source_commit_oid": "<full commit OID>",
  "package_name": "<name>",
  "manifest": { },
  "compatibility": { },
  "artifact_uuid": "<artifact uuid>"
})
start_workflow("agents.skill-package.trust", { "package_uuid": "<from import>" })
start_workflow("agents.agent-config.guidance-attach", {
  "agent_config_uuid": "<uuid>",
  "package_uuid": "<trusted version>"
})
```

Sync a **new** revision without mutating old versions: `agents.skill-package.sync` (same pin fields as import, plus required `skill_uuid`). Revoke for new sessions: `agents.skill-package.revoke`. Reads: `data.agents.skill-package.get` / `list`. Detach: `agents.agent-config.guidance-detach`.

**MCP server**

```
start_workflow("agents.mcp-server.register", {
  "name": "<server name>",
  "server_url": "https://example.example/mcp",
  "transport": "streamable_http"
})
```

`transport`: `streamable_http` | `sse` | `legacy_rest` (omit to auto-detect on first refresh). Optional `credential_connection_uuid` — CloudConnection type `mcp`; omit for unauthenticated servers.

OAuth (RFC 9728 / 8414 discovery, RFC 7591 DCR), then consent:

```
start_workflow("agents.mcp-server.discover-auth", {
  "mcp_server_uuid": "<uuid>",
  "redirect_uri": "https://app.example/callback"
})
```

Required: `mcp_server_uuid`, `redirect_uri`. Optional `connection_name` (stable across re-consent — `connection.setup` upserts by org+name), `scopes`. Then:

```
start_workflow("agents.mcp-server.test-connection", { "mcp_server_uuid": "<uuid>" })
start_workflow("agents.mcp-server.refresh", { "mcp_server_uuid": "<uuid>" })
start_workflow("agents.agent-config.mcp-attach", {
  "agent_config_uuid": "<uuid>",
  "agent_mcp_server_uuid": "<uuid>"
})
```

Update: `agents.mcp-server.update`. Ad-hoc: `agents.mcp-server.call-tool`. List: `data.agents.list-mcp-servers`.

### 3. Launch a session

Start **`agents.session-launch`** (featured DAG). Do not start `agents._session-launch.*`.

```
start_workflow("agents.session-launch", {
  "agent_config_uuid": "<uuid>",
  "task": "<what to do>",
  "ticket_uuid": "<optional>",
  "ticket_git_work_uuid": "<optional>",
  "repository_uuid": "<optional>",
  "branch_ref": "<optional>",
  "max_tool_rounds": 20
})
```

Required: `agent_config_uuid`, `task`. Optional git/ticket: `ticket_uuid`, `ticket_git_work_uuid`, `repository_uuid`, `branch_ref` / `target_ref` / `base_oid` / `head_oid`. Optional `actor_uuid` (staff hire), `context`, `attachment_uuids`, `max_tool_rounds`, `max_parallel_tool_calls`, `include_platform_defaults`, `refresh_stale_mcp`. Inspect layers with `get_workflow_dag("agents.session-launch")`:

`reconcile-stale-capacity` → `validate-create` → load-context (`fetch-secrets`, `load-skills`, `load-mcp`) → **`build-tool-catalog`** (`agents.tool-catalog.build`) → `load-memory` → `plan-git-work` (`ticket.git-work.begin`) → `reserve-delivery-cost` (`ticket.software-delivery.cost-reserve-bundle`) → `launch-runner` → `start-watch`.

Then:

```
start_workflow("agents.session-watch", { "session_uuid": "<uuid>" })
start_workflow("agents.session-stop", { "session_uuid": "<uuid>", "reason": "<optional>" })
start_workflow("agents.session-rate", { "session_uuid": "<uuid>", "quality_score": 4 })
```

`session-watch` polls the runner and finalizes (`terminal_session_status`, `total_cost_usd`). `session-stop` is a cancel **signal**. Also featured: `agents.session-restore`, `agents.session-fetch-attachments` (metadata only; presigned URLs redacted), `agents.webhook-trigger`. Reads: `data.agents.list-sessions`, `get-session`, `session-trace`.

### 4. Enable / disable a runner group for agents

Group must exist and be ACTIVE (`data.runner.list-groups` — see `orkestia-runners`). Purpose `agent` is the usual fleet shape.

```
start_workflow("agents.runner-group.enable", {
  "runner_group_uuid": "<uuid>",
  "agent_max_concurrent": 4
})
start_workflow("agents.runner-group.disable", { "runner_group_uuid": "<uuid>" })
```

Disable is **guarded by an active-session check** — stop sessions first if it refuses. Pin the group on the config via `runner_group_uuid` on create/update.

### 5. Cost and `budget_usd`

Per-config ceiling: `budget_usd` on `agents.agent-config.create` / `update`. That is a **per-session** USD cap. When a session hits it, further spend is enforced (runtime `agents.budget-check` is `featured: false` — do not start it; the session path does).

Operator reads:

```
start_workflow("data.agents.budget-status", { "period": "monthly" })
start_workflow("data.agents.session-cost", { "session_uuid": "<uuid>" })
start_workflow("data.agents.cost-by-config", { "date_from": "2026-08-01", "date_to": "2026-08-31" })
```

`period` on budget-status: `daily` | `monthly` | `all` (default `monthly`). Outputs include `budget_usd`, `spent_usd`, `pct_used`, `over_budget`. Session-cost includes `total_cost_usd`, `cache_savings_usd`, `ledger_entries`. Also: `data.agents.cost-by-model`, `cost-period-summary`, `org-summary`.

Featured writers: `agents.infra-cost-sync` (DAG), `agents.session-infra-cost-reconcile` (one terminal session; server-side runner-group billing). Do not start `agents._infra-cost-sync.*`.

### 6. End-user bounded agent

Tools are **exactly the compositions the app exposed** — every call re-authorized. See `orkestia-app-platform` and `orkestia-compositions`.

```
start_workflow("identity.app.set-end-user-agent", {
  "identity_app_uuid": "<app>",
  "end_user_agent_config_uuid": "<org-owned AgentConfig>"
})
start_workflow("agents.end-user.ask", { "question": "<end-user question>" })
```

`ask-stream` is the same bound session, token-by-token; the answer also lands in the terminal state. Required on ask: `question`. This is not `agents.session-launch` — do not mix staff-actor sessions with the end-user surface.

### 7. Tool catalog, tool policy, model capacity

These exist and are **not featured**. Treat them like session-launch internals: inspect with `get_workflow_schema`; do not start them in day-to-day ops. `agents.session-launch` already runs `agents.tool-catalog.build`.

| Surface | Type | What it does | Operator move |
|---|---|---|---|
| Tool catalog | `agents.tool-catalog.build` | Exact OpenAI-compatible tools the session may expose. Required `agent_config_uuid`. | Attach/detach skills, guidance, MCP; plan scope with `staff.tool-scope-plan`. After launch, read the DAG step output `build-tool-catalog`. |
| Tool policy | `agents.tool-policy.evaluate` | Whether a model-requested call may run or needs approval. Required `tool_name`. Outputs `allowed`, `requires_approval`, `risk_level`. | Runtime gate. Shape policy via attachments + `staff.tool-scope-plan` / `staff.policy-suggest`. |
| Tool call | `agents.tool-call.execute` | Execute one model-requested call through the workflow boundary. | Runtime; do not start. |
| Model capacity | `agents.model-capacity.acquire` | Reserve one model call against admitted RPM/TPM. Required `session_uuid`, `turn`, `requested_tokens`. | Runtime. Preflight: `staff.coding-run.preflight` (requires `repository_uuid`, `ticket_uuid`, `actor_uuid`, `runner_group_uuid`). Compare models: `data.agents.model-comparison`. |

Also discovered (not featured): `agents.org-settings.upsert` — read with featured `data.agents.get-org-settings`. `agents.price-config.upsert` / `agents.price-catalog-sync` — read with `data.agents.list-price-configs`. `agents.software-delivery.cleanup-minimize` — leased cleanup task; see `orkestia-tickets` for software-delivery.

## Object model

- **AgentConfig** — reusable brain: model binding, limits, memory, runner group, runtime profile. Hired as a Staff Actor.
- **Skill** — attachable capability (`skill.create` → `skill-attach`).
- **Guidance package** — immutable version pinned to `source_commit_oid` + `artifact_uuid`. Import → trust → attach; sync adds a new version.
- **MCP server** — registered URL + optional `mcp` connection; OAuth via `discover-auth`; tools via `refresh`.
- **Session** — one run of a config (`session-launch`). Optional ticket/git-work context.
- **Runner group** — compute; must be agent-enabled for launches.

## Day-to-day reads

All `data.agents.*` (21 types). Start freely:

- Inventory: `list-configs`, `get-config`, `list-sessions`, `get-session`, `list-skills`, `list-mcp-servers`, `skill-package.list` / `get`
- Cost: `budget-status`, `session-cost`, `cost-by-config`, `cost-by-model`, `cost-period-summary`
- Ops: `org-summary`, `get-org-settings`, `session-trace`, `memory-stats`, `model-comparison`, `tool-leaderboard`, `workflow-trigger-report`, `list-price-configs`

Also `data.ai-provider.list` / `get` / `get-default` for model profiles.

## Gotchas

- **Create needs an enabled AI provider profile.** `draft-from-description` does not skip that for the following `create`.
- **`draft-from-description` does not persist.** It returns fields; `create` writes the row.
- **`memory_write_enabled` defaults off.** Reading (`memory_enabled`) and writing are separate on purpose.
- **Start `session-launch`, not `_session-launch.*`.** Underscore types are DAG children.
- **Disable waits for idle sessions.** `runner-group.disable` fails while sessions are active.
- **`budget_usd` is per session.** Org rollups are `data.agents.budget-status` / `cost-*`, not that field.
- **End-user tools ≠ staff tools.** `end-user.ask` may call only exposed compositions.
- **Tool-policy / catalog / model-capacity are runtime.** Featured entry is still `session-launch`.
- **Hire is staff.** A working config is not on the org chart until `staff.hire-actor`.

## Sibling skills

- `orkestia-mcp-operating-loop` — discovery, schema, watch, remediation; featured vs internals.
- `orkestia-staff` — hire the config as an Actor; Cockpit; founder queue.
- `orkestia-runners` — groups, executions; this skill only toggles agent support.
- `orkestia-tickets` — `ticket.git-work.begin` and `ticket.software-delivery.cost-reserve-bundle` inside session-launch.
- `orkestia-subscription` — billing; staff RBAC seats are not agent session USD.
- `orkestia-app-platform` — `identity.app.set-end-user-agent`, expose compositions.
- `orkestia-github` — repo identity for guidance-package pins and ticket git-work.
- `orkestia-compositions` — only tools an end-user agent may call.

## Additional resources

- Workflow map by job: [reference.md](reference.md)
- Worked `initial_data` scenarios: [examples.md](examples.md)
