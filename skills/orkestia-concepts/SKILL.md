---
name: orkestia-concepts
description: >-
  Explains Orkestia's vocabulary and mental model across every domain: what the
  platform is, catalog types versus runs, the three identity planes (organization
  member, app end-user, agent actor), connections as the root object, compositions
  and virtual workflows, runners, staff and agents, tickets, subscriptions, the
  safety model (read_only, featured, prerequisites, remediation, billable), and
  the two surfaces (MCP and the Builder Framework). Load when the user asks what
  Orkestia is, what a term means, how two ideas differ, or before describing,
  pitching, or documenting the platform so every claim stays grounded in the
  live catalog. Not a how-to; hands off to the domain skill for recipes.
---

# Orkestia concepts

Orkestia is an AI-native, multi-cloud orchestration platform. Every capability is a **workflow**: a registered, schema-typed unit you discover and run through the public MCP server or, for apps built on the Builder Framework, through the typed SDK. This skill gives the shared vocabulary the domain skills assume. It contains no recipes; when a definition raises "how do I", open the skill named beside it.

Two rules from the server govern every description. From `concept://product`: describe Orkestia by what the live catalog and runs show. From `rule://grounding`: a registered type is a capability, the catalog total is a capability count, and architecture, pricing, or maturity you did not read from a tool is not something you may assert.

## When to load

Load this skill when the user asks what Orkestia is or does, what a word means (actor, composition, runner, seat, remediation, featured), how two things differ (member vs end-user, type vs run, connection vs account, staff vs agents, composition vs DAG, MCP vs Builder), or when the agent is about to write copy, a summary, a comparison, or documentation about the platform. Load `orkestia-start-here` for the first session, `orkestia-mcp-operating-loop` for tool mechanics.

## Use cases

1. **Define a term** in one paragraph, with the namespace and skill that owns it.
2. **Contrast two terms** the user is conflating.
3. **Describe the platform** accurately for a reader who has never seen it, grounded in a fresh `list_workflow_namespaces` result.
4. **Check a claim** before making it: is this a capability, a run, an inference, or a number from a stale document?
5. **Place a goal in the model**: which objects it touches, in which order.

## How to

### 1. Define a term

1. Find it in the glossary below. Quote the definition, name the namespace, name the skill.
2. If the user wants proof, run the cheapest read that shows the object: `list_workflow_types(prefix="<ns>.")` for a namespace, a `*.query` type for instances.
3. Stop at the definition. Do not run a mutation to "demonstrate."

### 2. Contrast two terms

Use the distinctions table. Say which side the user's situation is on, and what changes if they are wrong. Example: a "user" of their app is an **end-user** (identity app, seats, PKCE login), not a **member** (org role, console login, API tokens); the two are billed and permissioned differently.

### 3. Describe the platform

1. Read `concept://product` and `knowledge://orkestia/capabilities` from the server when the client exposes resources; otherwise call `list_workflow_namespaces` and `list_workflow_types(limit=0)`.
2. Lead with the mechanism: capabilities are typed workflows, runs are recoverable executions, provider access goes through connections, and business logic for end-users is exposed compositions.
3. Quote live counts only, with the date. Group capabilities by domain (clouds, Kubernetes and deploys, source and CI, data and hosting, AI and agents, orchestration primitives, identity and connections, commerce, messaging, governance).
4. Say what the platform does **not** do from what you read: it orchestrates deployment to targets the customer chooses and hosts static front-ends on AppHost; it does not create external resources such as IAM roles, DNS records, or third-party accounts for the user; it produces paste-ready instructions and waits.
5. Do not use hype words. Direct, technically precise sentences.

### 4. Check a claim

| The claim is about… | Ground it with | Never with |
|---|---|---|
| Whether a capability exists | `list_workflow_types` / `get_workflow_schema` | memory, another skill's table alone |
| What ran | `list_workflows`, `get_workflow_status`, `audit.workflow-run.query` | the catalog |
| How many types / namespaces | `list_workflow_namespaces` today | a number in any document |
| Whether something is safe | `read_only`, `has_prerequisites`, `featured` on the schema | the name alone |
| Price or plan | `subscription.billing.summary`, checkout schemas | remembered figures |
| Whether the org has compositions | `data.composition.list` | `prefix="virtual."` browse (may be empty) |

### 5. Place a goal in the model

Walk the objects in dependency order and stop at the first missing one:

```
account → organization → member token
        → connection (provider credential)
        → domain objects (runner group, registry account, identity app, agent config, …)
        → runs (state machines, DAGs) and compositions (virtual workflows)
        → exposure to end-users, schedules, staff dispatch
        → subscription gates on the paid parts
```

## Glossary

### Platform and catalog

| Term | Meaning | Namespace / skill |
|---|---|---|
| Workflow type | A registered, schema-typed capability. Listed by `list_workflow_types`. | all / `orkestia-mcp-operating-loop` |
| Run | One execution of a type. Has a `workflow_id` (`wf_…`), a state history, terminal status, and `state_data` output. | run tools |
| Kind | `state_machine` (atomic operation; most common), `dag` (layered parallel steps with compensation), `data` (persistence or query). | `workflow_kind` |
| Scope | What a type binds to: `organization`, `library`, `none`, `subscription`, `app`, `actor`, `project`, `system`. | `workflow_scope` |
| Namespace | The dotted prefix (`connection.`, `aws.ec2.`). First level is the domain, second the service or object. | `list_workflow_namespaces` |
| Featured | The library author's hint that a type is a human-runnable entry point. A hint, not a guarantee; some DAG steps are also featured. | `featured` |
| Internal | Sub-steps not meant to be started directly: `-validate`, `.prepare`, `__pre`, `__post`, underscore segments, "DAG step" or "compensation" descriptions. | skip |
| `read_only` | Starting the type has no side effect beyond the run record. Safe without confirmation. | schema |
| `has_prerequisites` | External setup must exist first. `get_workflow_prerequisites` returns a guide with platform identity filled in. | schema |
| Context-sourced field | A schema field with `source.kind: context` (`organization_uuid`, `actor`). The server injects it from the token; the caller omits it. | schema |
| Plugin | An engine provider module (`aws`, `github`, `connection`). Diagnostic, not discovery. | `list_plugins` |

### Identity: three planes

| Term | Meaning | Namespace / skill |
|---|---|---|
| Account | A person who signed up in the web console. | console |
| Organization | The tenant. Every run and object is scoped to one. Created in the console, never over MCP. | `identity.organization.*` (read only) |
| Member | An account holding a role (`owner`, `admin`, `member`) in an organization. Invited by email. Uses the console and API tokens. | `identity.membership.*`, `identity.org-invitation.*` / `orkestia-app-platform` |
| Member token | An API token minted by a member. Scopes MCP and CLI calls to that member's organization. Shown once. | `identity.api-token.*` |
| Identity app | A hosted PKCE login tenant for the organization's **own product**. Has a public `client_key`, redirect URIs, dev or live mode. | `identity.app.*` / `orkestia-app-platform` |
| End-user | A customer of that product. Lives in the identity app, signs in at the hosted login, consumes a **seat**, may run only **exposed** virtual workflows. Not a member. | `identity.end-user.*`, `identity.seat.*` |
| App-organization | A workspace inside the identity app grouping end-users (a customer's team inside the user's product). | `identity.app-organization.*` |
| Actor | An AI principal hired into the organization from an agent config. Runs with its own token, budget, and role. | `staff.*` / `orkestia-staff` |
| Token planes | End-user (browser, PKCE), member (CLI or trusted operator), agent (staff runner). They never share a process. | `orkestia-builder` |

### Providers and infrastructure

| Term | Meaning | Namespace / skill |
|---|---|---|
| Connection | The org-owned, named credential to an external provider. The root object: runner groups, registry and network accounts, GitHub, storage, and AI-model bindings reference it by `connection_uuid`. | `connection.*` / `orkestia-connections` |
| Provider | An external system a connection points at: AWS, GCP, Azure, Magalu, GitHub, Stripe, SQL, DocuSign, Xero, Hostinger, social platforms, and others. Each has a `provider_type` field group on `connection.setup`. | per-provider namespaces |
| Runner group | A compute fleet definition. Orkestia provisions an environment on a cloud backend or registers DevKit hosts, then launches executions. | `runner.*` / `orkestia-runners` |
| Execution | One job on a runner: CI, a command, or an agent session. | `runner.*` |
| Warm pool | Idle instances kept ready so executions skip cold start. Billable. | `runner.*` |
| DevKit | The local CLI and host agent. Registers a developer machine as a runner and drives the attended coding lifecycle. | `orkestia-runners`, `orkestia-tickets` |
| Registry account | A container registry bound to a connection and synced into an inventory of repositories, images, and tags. | `registry.*` / `orkestia-registry-network` |
| Network account | Cloud networking bound to a connection and synced into scopes, segments, and boundaries. | `network.*` |
| Deployment target | A cluster or namespace adopted for releases. | `deploy.*`, `kubernetes.*`, `k8s.*` |
| AppHost | Static hosting for the user's front-end at a claimed site. Needs a live-mode identity app and subscription state. | `apphost.*` / `orkestia-app-platform` |

### Orchestration

| Term | Meaning | Namespace / skill |
|---|---|---|
| DAG | A multi-step type: layers of parallel steps, each a child type, with optional compensation. Inspect with `get_workflow_dag`. | `workflow_kind: dag` |
| Compensation | Deferred undo steps a DAG runs when it fails terminally. | DAG |
| Remediation gate | A DAG parked in `remediation_pending` with a suggested fix instead of compensating. Resolved with `resolve_workflow` (`remediated` or `denied`). | run tools |
| Retry | `retry_workflow` on a terminal failed run after the cause is fixed. | run tools |
| Force terminate | Marking a stale non-terminal run as unrecoverably failed. Last resort. | run tools |
| Control primitive | A pure data or flow step (`filter`, `map`, `template`, `switch`, `guard`, `poll`, `http.request`). Read-only, no org, no prerequisites. | `control.*` / `orkestia-compositions` |
| Composition | A saved, versioned assembly of catalog steps and control primitives. Compiles to a **virtual workflow**. | `composition.*` / `orkestia-compositions` |
| Virtual workflow | The runnable type a composition produces, named `virtual.<uuid>@<version>`. Per organization; inventory lives in `data.composition.list`, not the catalog browse. | `orkestia-compositions` |
| Exposure | Granting an identity app's end-users the right to run one virtual workflow. The only business logic end-users may start. | `identity.app.expose-virtual-workflow` |
| Schedule | A recurring trigger that starts a target type every N minutes. | `schedule.*` |
| Ticket | The work ledger. Humans and adapters open or ingest tickets; agent coding work is governed here from plan gate to exact-object delivery. | `ticket.*` / `orkestia-tickets` |
| Audit | Run-level and health-level records of what actually executed. | `audit.*` |

### AI workforce

| Term | Meaning | Namespace / skill |
|---|---|---|
| Agent config | A reusable definition: model, budget, memory, attached skills, MCP servers. The machinery. | `agents.*` / `orkestia-agents` |
| Session | One agent run on runner infrastructure, with cost tracking. | `agents.*` |
| Staff | The org chart: org units, hired actors, dispatch (schedule, event, manual), RBAC, seats, founder review queue, Cockpit blueprints. | `staff.*` / `orkestia-staff` |
| Founder queue | Human review of actions actors may not take alone. External resource creation, paid or public actuation, and gated mutations land here. | `orkestia-staff` |
| End-user agent | A bounded agent an identity app points at so its end-users can ask questions. | `agents.end-user.*` |

### Commerce

| Term | Meaning | Namespace / skill |
|---|---|---|
| Subscription | The organization's Stripe-backed platform plan and items. Read with `subscription.billing.summary`. | `subscription.*` / `orkestia-subscription` |
| Seat | A billed unit: platform user seats (members), actor or RBAC seats (staff), end-user seat packs (identity apps). | `subscription.billing.*`, `identity.seat.*` |
| Add-on | Lumen (observability) tiers and packs, workflow retention and storage. | `subscription.billing.lumen-*`, `.workflow-retention.*` |
| Checkout | A Stripe Checkout URL returned by a workflow; the user completes payment in the browser. | `subscription.platform.checkout` and siblings |
| Stripe connection | The user's **own** Stripe account wired as a provider, unrelated to paying Orkestia. | `connection.setup` (`stripe`) |

### Surfaces

| Term | Meaning | Skill |
|---|---|---|
| Public MCP server | `mcp.orkestia.dev`. Discovery, schemas, prerequisites, start, watch, history, retry, resolve, terminate, `open_app`. No app repo needed. | `orkestia-mcp-operating-loop` |
| Console | The web app where accounts and organizations are created, connections are authorized via OAuth callbacks, and `open_app` renders fleets and clusters. | — |
| Builder Framework | TypeScript packages (`@orkestia/*`) and the `orkestia` CLI. Desired state in code: identity, data structures, compositions, resources, staff, dashboards, AppHost publish. | `orkestia-builder` and siblings |
| Workflow API and SDK | The typed HTTP surface Builder apps and end-user front-ends call at run time with a token. | `orkestia-builder-workflows` |
| Hosted login | The end-user sign-in page the identity app redirects to (PKCE, RS256 JWT). | `orkestia-app-platform` |

## Distinctions that cause the most mistakes

| This | Not that | Why it matters |
|---|---|---|
| `list_workflow_types` (catalog) | `list_workflows` (runs of one type) | Mixing them is the most common tool error. |
| `workflow_type` (kind) | `workflow_id` (instance, `wf_…`) | Catalog tools take the type; run tools take the id. |
| Member | End-user | Different stores, logins, seats, permissions, billing lines. |
| Connection | Registry or network **account** | The account is a binding of a connection to an inventory; both have UUIDs. |
| Composition (source) | Virtual workflow (compiled type) | Save and activate produce the type; exposure grants end-users the type. |
| DAG (author-defined, catalog) | Composition (user-defined, per org) | Both are multi-step; only compositions are yours to edit. |
| Staff (org chart, actors) | Agents (configs, sessions) | Hiring binds an existing config; it creates nothing. |
| `retry_workflow` | `resolve_workflow` | Terminal failed versus parked in `remediation_pending`. |
| `read_only` type | Read tool | Both are safe; the type still creates a short-lived run. |
| Orkestia orchestrates deployment | Orkestia hosts the runtime | Targets are the customer's cloud or host; AppHost serves static front-ends only. |
| Paste-ready instruction | Created external resource | IAM roles, DNS, third-party accounts stay with the human. |
| Capability count | Production count | "N types" is what the org could run, not what it ran. |

## Day-to-day reads

Server resources when available: `concept://product`, `knowledge://orkestia/capabilities`, `rule://grounding`, `rule://getting-started`, `rule://authenticated-context`, `rule://prerequisites-first`, `rule://orkestia-auth-setup`, `knowledge://mcp/public-boundary`. Tools: `whoami`, `list_workflow_namespaces`, `list_workflow_types`, `get_workflow_schema`, `get_workflow_definition`, `get_workflow_dag`. Read-only types that show instances: `identity.organization.query`, `identity.membership.query-by-org`, `connection.query`, `data.composition.list`, `subscription.billing.summary`, `audit.workflow-run.query`.

This skill starts no mutations.

## Gotchas

- **Do not define from memory when a tool can show it.** A namespace the user names may have been renamed or removed; list it.
- **Counts date fast.** Quote them with the day you read them, or not at all.
- **"Workflow" is overloaded.** Say type, run, DAG, composition, or virtual workflow.
- **"User" is overloaded.** Say member, end-user, or actor.
- **`virtual.` browse returning nothing proves nothing.** Only `data.composition.list` is the inventory.
- **Pricing lives in the billing workflows.** Never quote a figure from a document.
- **The catalog includes internals.** Descriptions that say "DAG step" or "compensation" are not user capabilities.

## Sibling skills

`orkestia-start-here` (first session), `orkestia-mcp-operating-loop` (tool mechanics), and the domain skill named beside each term.

## Additional resources

- Namespace-to-object map and the grounding rules restated: [reference.md](reference.md)
- Worked definitions, contrasts, and a grounded platform description: [examples.md](examples.md)
