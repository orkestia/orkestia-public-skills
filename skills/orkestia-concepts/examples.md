# Worked examples

## 1. "What is an actor?"

An **actor** is an AI principal hired into the organization from an existing **agent config** (`staff.hire-actor`). The config is the machinery (model, budget, memory, skills, MCP servers; `agents.*`); the actor is the org-chart seat with a role, a token, and dispatch rules (`staff.*`). Hiring creates no config. Proof, if wanted:

```
list_workflow_types(prefix="staff.", q="hire")
list_workflow_types(prefix="agents.agent-config.")
```

Owning skills: `orkestia-agents` (configs, sessions), `orkestia-staff` (hiring, dispatch, review queue).

## 2. "Is a user of my app the same as a user of Orkestia?"

No. Two planes:

| | Member | End-user |
|---|---|---|
| Who | The user's teammate | The user's customer |
| Lives in | The organization | An identity app |
| Signs in at | The console | The hosted login (PKCE) |
| Credential | Member API token | End-user JWT |
| May run | Any type the org allows | Only exposed virtual workflows |
| Billed as | Platform user seat | End-user seat pack |

If they are building a product, their customers are end-users. Continue in `orkestia-app-platform`.

## 3. "Describe Orkestia to my CTO in one paragraph."

Read the live shape first:

```
list_workflow_namespaces()
```

Then write from it. A grounded paragraph on 2026-09-03 read:

> Orkestia is a multi-cloud orchestration platform where every capability is a registered, schema-typed workflow. On 2026-09-03 the public catalog listed 4,550 types across 91 namespaces, covering AWS, GCP, Azure and Magalu, Kubernetes and GitOps, GitHub and self-hosted runners, identity for an organization's own app end-users, Stripe-backed billing, an AI workforce (agent configs hired as staff actors), and pure orchestration primitives that users assemble into saved compositions. Provider access goes through organization-owned connections; runs are event-sourced, watchable, and recoverable (retry, remediation gates, forced termination). Agents operate it through a public MCP server; apps build on a TypeScript framework and a typed workflow API. Orkestia orchestrates deployment to targets the customer chooses and hosts static front-ends; it does not create external resources such as IAM roles or DNS records on the customer's behalf.

Every clause above traces to a tool result or a server resource. Replace the counts with today's.

## 4. "How many production workflows do you have?"

Do not answer with the catalog total. Say: the catalog lists N **types** (capabilities). What has actually run in this organization is a different question, answered by `audit.workflow-run.query` (read-only) or `list_workflows` for one type. Offer to run the audit query.

## 5. "Is a composition the same as a DAG?"

Both are multi-step. A **DAG** is a catalog type an author shipped (`workflow_kind: dag`, inspect with `get_workflow_dag`); the org cannot edit it. A **composition** is the org's own assembly of catalog steps and `control.*` primitives, saved and versioned (`composition.save`, `composition.activate`), compiled to a `virtual.<uuid>@<version>` type. Only compositions can be exposed to end-users. Inventory with `data.composition.list`, never with a `prefix="virtual."` browse.

## 6. "Why did my AWS workflow fail on a brand-new org?"

Place the goal in the model: account → organization → **connection** → `aws.*`. A new org has zero connections, so every `aws.*` type stops at prerequisites. Proof: `connection.query` returns `count: 0`. Fix: `orkestia-connections` recipe 1 with `variant="aws"`. This is expected behavior, not an outage.

## 7. "Does Orkestia host my app?"

It **orchestrates deployment** to a target the user chooses (their cloud via a connection, or a host via a token) and it **hosts static front-ends** on AppHost after a site claim. It does not run the user's backend. Say exactly that; do not upgrade it to "Orkestia hosts your app."
