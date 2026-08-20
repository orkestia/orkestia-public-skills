---
name: orkestia-agents
description: Configure and run Orkestia agents (agents.*, 43 types) — AgentConfigs with models, budgets, memory; attach skills, trusted guidance packages, and MCP servers; launch and watch sessions on runner infrastructure; track cost. Use for anything under agents.* or data.agents.*, and as the machinery beneath staff actors.
---

# Orkestia agents

Where Staff is the org chart, agents is the machinery: reusable **AgentConfigs**, their capabilities, and the **sessions** that run on runner infrastructure. A Staff actor is an AgentConfig hired into the org.

## AgentConfig

`agents.agent-config.create` — prerequisite: **≥1 enabled AI provider profile** (discover with `data.ai-provider.list(enabled_only=true)`; omit model fields to use the org default profile). Knobs:

- Model: `ai_provider_config_uuid` or `model_profile` (stable handle) or `model_connection_uuid`; `model_name` must match the profile's `default_model`.
- Limits: `max_steps`, `max_tokens_per_step`, `budget_usd` (per-session USD ceiling).
- Memory: `memory_enabled`, `memory_strategy` (`last_k` | `importance` | `pack` — ranked against the task, fitted to a token budget), `memory_top_k` (typically 5–30).
- Runtime: `runner_group_uuid` (agent-enabled group), `runner_image`, `runtime_profile` — `workspace-probe-v1` is the safe default; `software-development-v1` is accepted only by a cloudless DevKit group when org code-execution policy permits.

Also: `update`, `clone`, `delete` (soft), `purge` (hard, no sessions), and `draft-from-description` — type a job description, get a complete drafted config (name, system prompt, model, memory).

## Capabilities to attach

| Capability | Workflows | Notes |
|---|---|---|
| Skills | `skill.create/update/delete/validate` · `agent-config.skill-attach/-detach` | `validate` tests backend connectivity |
| Guidance packages | `skill-package.import` → `trust` → `sync`; `revoke`; `agent-config.guidance-attach/-detach` | Provider-blind, pinned to an exact Git object; versions immutable; reads `data.agents.skill-package.get/list` |
| MCP servers | `mcp-server.register`, `discover-auth`, `test-connection`, `refresh` (tool catalog), `update`, `call-tool` | `discover-auth` does full OAuth discovery (RFC 9728/8414/7591) and stages consent |

## Sessions

`agents.session-launch` (DAG) shows the assembly order: *reconcile-stale-capacity → validate-create → fetch-secrets → load-skills → load-mcp → load-memory → build-tool-catalog → launch-runner → start-watch*. Inputs: `agent_config_uuid`, `task` (required); optional ticket context (`ticket_uuid`, `ticket_git_work_uuid`, `repository_uuid`, `branch_ref`/`target_ref`/`base_oid`/`head_oid`), `context`, `attachment_uuids`, `max_tool_rounds`, `max_parallel_tool_calls`.

Then: `session-watch` (polls the runner, finalizes), `session-stop` (cancel signal), `session-restore` (resume context), `session-rate` (quality rating), `session-fetch-attachments` (metadata manifest; presigned URLs redacted), `webhook-trigger` (outbound webhooks on session events).

## Cost & observability

Writers: `infra-cost-sync`, `session-infra-cost-reconcile` (server-side runner-group billing config). Reads in `data.agents.*`: `budget-status`, `cost-by-config`, `cost-by-model`, `cost-period-summary`, `session-cost` (with cache-savings estimate), `model-comparison` (latency, tokens, cache hit rate), `tool-leaderboard`, `memory-stats`, `session-trace` (live timeline), `org-summary`, `list-configs/-sessions/-skills/-mcp-servers/-price-configs`, `get-config/-session/-org-settings`, `workflow-trigger-report`.

Fine-tuning datasets from completed sessions: `ft-dataset.create` → `validate-format` (sample + render check) → `build` (DAG: build + upload); `delete`.

## End-user surface

`agents.end-user.ask` / `ask-stream` run a real session under the **calling end-user's** authority: tools are exactly the compositions the app exposed, every call re-authorized. Wire via `identity.app.set-end-user-agent` (see `orkestia-app-platform`).

## Gotchas

- Agent groups: `agents.runner-group.enable` (group must be ACTIVE) / `disable` (guarded by active-session check).
