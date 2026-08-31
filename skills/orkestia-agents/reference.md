# Agents workflow map

Catalog snapshot 2026-08-31: **90** `agents.*` types + **21** `data.agents.*` reads. Re-verify with `list_workflow_types(prefix="agents.")` and `prefix="data.agents."`.

**Do not start** `agents._session-launch.*`, `agents._infra-cost-sync.*`, `agents._ft-dataset.*`. They are DAG children of featured parents (`agents.session-launch`, `agents.infra-cost-sync`, `agents.ft-dataset.build`). Same rule as operating-loop `featured: true`.

## AgentConfig

| Workflow | Role |
|---|---|
| `agents.agent-config.create` | Persist a config. Prerequisite: ≥1 enabled AI provider profile. Required `name`. |
| `agents.agent-config.draft-from-description` | Draft name / prompt / model / memory from a job description. Does **not** persist. |
| `agents.agent-config.update` | Patch fields. |
| `agents.agent-config.clone` | Clone an existing config. |
| `agents.agent-config.delete` | Soft-delete. |
| `agents.agent-config.purge` | Hard-delete a soft-deleted config with no sessions. |
| `agents.agent-config.skill-attach` / `skill-detach` | Bind a skill. Fields `agent_config_uuid`, `agent_skill_uuid`. |
| `agents.agent-config.guidance-attach` / `guidance-detach` | Pin/unpin an exact trusted package version (`package_uuid`). |
| `agents.agent-config.mcp-attach` / `mcp-detach` | Bind an MCP server (`agent_mcp_server_uuid`). |

## Skills

| Workflow | Role |
|---|---|
| `agents.skill.create` | Required `name`, `kind`. Optional webhook fields or `workflow_type`, `visibility`. |
| `agents.skill.update` | Patch. |
| `agents.skill.delete` | Soft-delete. |
| `agents.skill.validate` | Required `skill_uuid`. Test backend connectivity; sets `last_validated_at`. |

## Guidance packages

Pinned to an exact Git object; versions immutable.

| Workflow | Role |
|---|---|
| `agents.skill-package.import` | Required `version`, `package_version`, `source_repository_uuid`, `source_commit_oid`, `package_name`, `manifest`, `compatibility`, `artifact_uuid`. |
| `agents.skill-package.trust` | Trust a validated, artifact-backed package. Required `package_uuid`. |
| `agents.skill-package.sync` | New revision without mutating old versions. Same pins as import plus required `skill_uuid`. |
| `agents.skill-package.revoke` | Stop new sessions from using a version; history kept. |

## MCP servers

| Workflow | Role |
|---|---|
| `agents.mcp-server.register` | Required `name`, `server_url`. Optional `credential_connection_uuid` (connection type `mcp`), `transport` (`streamable_http` \| `sse` \| `legacy_rest`). |
| `agents.mcp-server.discover-auth` | OAuth RFC 9728/8414 + DCR RFC 7591. Required `mcp_server_uuid`, `redirect_uri`. |
| `agents.mcp-server.test-connection` | Reachability + credentials. |
| `agents.mcp-server.refresh` | Refresh the server's tool catalog. |
| `agents.mcp-server.update` | URL, description, transport, credential link. |
| `agents.mcp-server.call-tool` | Execute a tool through a registered server. |

## Sessions (operator entry)

| Workflow | Role |
|---|---|
| `agents.session-launch` | **The** launch DAG. Required `agent_config_uuid`, `task`. |
| `agents.session-watch` | Poll runner; finalize. Required `session_uuid`. |
| `agents.session-stop` | Cancel signal. Optional `reason`. |
| `agents.session-restore` | Resume context from an existing session. |
| `agents.session-rate` | Quality rating. Required `session_uuid`, `quality_score`. |
| `agents.session-fetch-attachments` | Metadata manifest; presigned URLs redacted. |
| `agents.webhook-trigger` | Outbound webhooks on session events. |

`get_workflow_dag("agents.session-launch")` layers: `reconcile-stale-capacity` (`runner.execution-reconcile-stale-claims`) → `validate-create` → load-context (`fetch-secrets`, `load-skills`, `load-mcp`) → `build-tool-catalog` (`agents.tool-catalog.build`) → `load-memory` → `plan-git-work` (`ticket.git-work.begin`) → `reserve-delivery-cost` (`ticket.software-delivery.cost-reserve-bundle`) → `launch-runner` → `start-watch`. Compensate: `agents._session-launch.mark-failed`.

## Runner groups

| Workflow | Role |
|---|---|
| `agents.runner-group.enable` | Group must be ACTIVE. Optional `agent_max_concurrent`. |
| `agents.runner-group.disable` | Guarded by an active-session check. |

## Cost (featured writers)

| Workflow | Role |
|---|---|
| `agents.infra-cost-sync` | DAG: fetch + persist infra cost for billable sessions. |
| `agents.session-infra-cost-reconcile` | Re-observe one terminal session using server-side runner-group billing config. |

## Fine-tuning datasets

| Workflow | Role |
|---|---|
| `agents.ft-dataset.create` | Export definition. |
| `agents.ft-dataset.validate-format` | Sample completed sessions + render check. |
| `agents.ft-dataset.build` | DAG: build + upload. |
| `agents.ft-dataset.delete` | Soft-delete. |

## End-user surface

| Workflow | Role |
|---|---|
| `agents.end-user.ask` | Required `question`. Tools = exposed compositions only. |
| `agents.end-user.ask-stream` | Same bound session; streamed tokens + terminal answer. |

Wire with `identity.app.set-end-user-agent` (`identity_app_uuid`, optional `end_user_agent_config_uuid`).

## New / runtime surfaces (`featured: false`)

Inspect with `get_workflow_schema`. Do not start in day-to-day ops unless debugging a parent.

| Workflow | Role |
|---|---|
| `agents.tool-catalog.build` | OpenAI-compatible catalog a session may expose. Required `agent_config_uuid`. Session-launch step. |
| `agents.tool-policy.evaluate` | Allow / deny / require approval for one `tool_name`. |
| `agents.tool-call.execute` | Run one model-requested tool through the workflow boundary. |
| `agents.model-capacity.acquire` | Reserve one call against RPM/TPM. Required `session_uuid`, `turn`, `requested_tokens`. |
| `agents.org-settings.upsert` | Create/update org agent settings. Read: `data.agents.get-org-settings`. |
| `agents.price-config.upsert` | Org-specific model price override. |
| `agents.price-catalog-sync` | Sync built-in pricing into `AgentPriceConfig`. Read: `data.agents.list-price-configs`. |
| `agents.software-delivery.cleanup-minimize` | Minimize prompt/tool metadata under one leased software-delivery cleanup task. |

## Skip — other non-featured runtime

`agents.budget-check`, `agents.cost-entry-record`, `agents.memory-distill` / `memory-load` / `memory-prune` / `memory-save`, `agents.metrics-event-record` / `metrics-memory-record` / `metrics-step-open` / `metrics-step-close` / `metrics-tool-record`, `agents.session-create`, `agents.session-cancel-record`, `agents.session-finalize` / `session-finalize-cancel` / `session-finalize-failure`, `agents.session-heartbeat` / `session-heartbeat-rate`, `agents.session-infra-cost-fetch`, `agents.session-notify`.

## Underscore internals (never start)

**Session launch:** `agents._session-launch.fetch-secrets`, `launch-runner`, `load-mcp`, `load-memory`, `load-skills`, `mark-failed`, `start-watch`, `validate-create`.

**Infra cost:** `agents._infra-cost-sync.fetch-aws`, `fetch-do`, `fetch-gcp`, `noop`, `persist`, `resolve-sessions`.

**FT dataset:** `agents._ft-dataset.build-examples`, `finalize`, `mark-failed`, `upload`, `validate`.

## `data.agents.*` (21)

| Workflow | Role |
|---|---|
| `data.agents.list-configs` | Paginated configs. |
| `data.agents.get-config` | Config + skills + MCP lists. |
| `data.agents.list-sessions` | Paginated; optional status/config filter. |
| `data.agents.get-session` | One session. |
| `data.agents.list-skills` | Paginated skills. |
| `data.agents.list-mcp-servers` | Paginated MCP servers. |
| `data.agents.skill-package.list` | Immutable versions, newest first. |
| `data.agents.skill-package.get` | One exact version. |
| `data.agents.budget-status` | Utilisation. `period`: `daily` \| `monthly` \| `all`. |
| `data.agents.session-cost` | One session ledger + cache-savings estimate. |
| `data.agents.cost-by-config` | Optional `date_from` / `date_to`. |
| `data.agents.cost-by-model` | LLM cost and tokens by model. |
| `data.agents.cost-period-summary` | Ledger grouped by day. |
| `data.agents.org-summary` | High-level dashboard. |
| `data.agents.get-org-settings` | Org agent settings. |
| `data.agents.session-trace` | Live timeline: steps, tools, memory, events. |
| `data.agents.memory-stats` | Memory usage; optional single config. |
| `data.agents.model-comparison` | Latency, tokens, cache hit rate. |
| `data.agents.tool-leaderboard` | Usage, success, latency, context consumed. |
| `data.agents.workflow-trigger-report` | Sessions by `caller_ref` prefix. |
| `data.agents.list-price-configs` | Active prices + override indicators. |

Related (not under `data.agents`): `data.ai-provider.list` (`enabled_only=true`), `data.ai-provider.get`, `data.ai-provider.get-default`.
