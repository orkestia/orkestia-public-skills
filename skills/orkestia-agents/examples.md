# Agents examples

`organization_uuid` is injected — omit it. Confirm `kind` and other unconstrained strings with `get_workflow_schema` before substituting placeholders.

## 1. Draft, then create a config

```
whoami()
list_workflow_types(prefix="agents.")
list_workflow_types(prefix="data.agents.")

start_workflow("data.ai-provider.list", { "enabled_only": true })
# Need count ≥ 1. Pin ai_provider_config_uuid / default_model from a row, or omit to use org default.

get_workflow_prerequisites("agents.agent-config.create", variant="ai-provider-profile")
get_workflow_schema("agents.agent-config.create")

start_workflow("agents.agent-config.draft-from-description", {
  "description": "Reviews pull-request diffs, cites failing checks, and writes a short risk summary. Does not merge."
})
# → name, system_prompt, model_name, memory_*  (not persisted)

start_workflow("data.runner.list-groups", {})
# Pick an ACTIVE, agent-eligible group. Enable with agents.runner-group.enable if needed.

start_workflow("agents.agent-config.create", {
  "name": "<from draft>",
  "description": "<from draft>",
  "system_prompt": "<from draft>",
  "ai_provider_config_uuid": "<optional pin>",
  "model_name": "<must match profile default_model>",
  "max_steps": 40,
  "budget_usd": 5.0,
  "memory_enabled": true,
  "memory_write_enabled": false,
  "memory_strategy": "pack",
  "memory_top_k": 10,
  "runner_group_uuid": "<agent-enabled group>",
  "runtime_profile": "workspace-probe-v1"
})
# → agent_config_uuid

start_workflow("data.agents.get-config", { "agent_config_uuid": "<uuid>" })
```

Hire into the org chart only after this: `staff.hire-actor` with this `agent_config_uuid` (`orkestia-staff`).

## 2. Attach a skill, trust a package, register MCP

```
start_workflow("agents.skill.create", {
  "name": "lookup-ticket",
  "kind": "<from schema>",
  "workflow_type": "<catalog type this skill should invoke>",
  "description": "Read one ticket by uuid"
})
start_workflow("agents.skill.validate", { "skill_uuid": "<from create>" })
start_workflow("agents.agent-config.skill-attach", {
  "agent_config_uuid": "<uuid>",
  "agent_skill_uuid": "<uuid>"
})

start_workflow("agents.skill-package.import", {
  "version": 1,
  "package_version": "1.0.0",
  "source_repository_uuid": "<repo uuid>",
  "source_commit_oid": "<full commit OID>",
  "package_name": "review-guidance",
  "manifest": { },
  "compatibility": { },
  "artifact_uuid": "<artifact uuid>"
})
start_workflow("agents.skill-package.trust", { "package_uuid": "<from import>" })
start_workflow("agents.agent-config.guidance-attach", {
  "agent_config_uuid": "<uuid>",
  "package_uuid": "<trusted>"
})
# Later revision: agents.skill-package.sync with a new source_commit_oid — old versions stay immutable.

start_workflow("agents.mcp-server.register", {
  "name": "docs-mcp",
  "server_url": "https://mcp.example/docs",
  "transport": "streamable_http"
})
start_workflow("agents.mcp-server.discover-auth", {
  "mcp_server_uuid": "<uuid>",
  "redirect_uri": "https://app.example/oauth/callback",
  "connection_name": "docs-mcp-oauth"
})
# Complete consent in the browser using authorize_endpoint from the result.

start_workflow("agents.mcp-server.test-connection", { "mcp_server_uuid": "<uuid>" })
start_workflow("agents.mcp-server.refresh", { "mcp_server_uuid": "<uuid>" })
start_workflow("agents.agent-config.mcp-attach", {
  "agent_config_uuid": "<uuid>",
  "agent_mcp_server_uuid": "<uuid>"
})
```

## 3. Launch, watch, stop, rate

```
get_workflow_schema("agents.session-launch")
get_workflow_dag("agents.session-launch")
# Do not start agents._session-launch.* children.

start_workflow("agents.session-launch", {
  "agent_config_uuid": "<uuid>",
  "task": "Summarize open PRs on this ticket and list blockers.",
  "ticket_uuid": "<optional ticket>",
  "ticket_git_work_uuid": "<optional git-work>",
  "repository_uuid": "<optional>",
  "branch_ref": "refs/heads/main",
  "max_tool_rounds": 20
})
# → session_uuid (and DAG step outputs including build-tool-catalog)

start_workflow("data.agents.get-session", { "session_uuid": "<uuid>" })
start_workflow("data.agents.session-trace", { "session_uuid": "<uuid>" })
start_workflow("agents.session-watch", { "session_uuid": "<uuid>" })

# If it must stop:
start_workflow("agents.session-stop", {
  "session_uuid": "<uuid>",
  "reason": "Operator cancelled"
})

start_workflow("agents.session-rate", {
  "session_uuid": "<uuid>",
  "quality_score": 4,
  "notes": "Correct blockers; missed one flaky check."
})
```

## 4. Enable a runner group, then disable after idle

```
start_workflow("data.runner.list-groups", {})

start_workflow("agents.runner-group.enable", {
  "runner_group_uuid": "<ACTIVE group uuid>",
  "agent_max_concurrent": 4
})
# → supports_agents

start_workflow("data.agents.list-sessions", {})
# Wait until none are active on that group.

start_workflow("agents.runner-group.disable", {
  "runner_group_uuid": "<uuid>"
})
# Fails while sessions are active — stop them first.
```

## 5. Cost when a session hits `budget_usd`

Config was created with `"budget_usd": 5.0`. After a run:

```
start_workflow("data.agents.session-cost", { "session_uuid": "<uuid>" })
# → total_cost_usd, cache_savings_usd, ledger_entries

start_workflow("data.agents.budget-status", { "period": "monthly" })
# → budget_usd, spent_usd, pct_used, over_budget

start_workflow("data.agents.cost-by-config", {
  "date_from": "2026-08-01",
  "date_to": "2026-08-31"
})

start_workflow("agents.agent-config.update", {
  "agent_config_uuid": "<uuid>",
  "budget_usd": 8.0
})
```

Do not start `agents.budget-check` — it is a non-featured runtime enforcer. Do not start `agents._infra-cost-sync.*`; use featured `agents.infra-cost-sync` or `agents.session-infra-cost-reconcile` if infra cost must be re-observed.

## 6. End-user agent + what tools it may call

```
start_workflow("identity.app.set-end-user-agent", {
  "identity_app_uuid": "<app>",
  "end_user_agent_config_uuid": "<org-owned AgentConfig>"
})
# Expose compositions first (orkestia-app-platform / orkestia-compositions).
# End-user tools = those compositions only.

start_workflow("agents.end-user.ask", {
  "question": "What is the status of my latest order?"
})
# → answer, session_uuid

# Catalog / policy are session-launch internals — inspect, don't drive ops with them:
get_workflow_schema("agents.tool-catalog.build")
get_workflow_schema("agents.tool-policy.evaluate")
get_workflow_schema("agents.model-capacity.acquire")
start_workflow("data.agents.model-comparison", {})
start_workflow("staff.coding-run.preflight", {
  "repository_uuid": "<repo>",
  "ticket_uuid": "<ticket>",
  "actor_uuid": "<staff actor>",
  "runner_group_uuid": "<group>"
})
```
