# Concepts — reference

## Grounding rules (from the server)

| Resource | Rule |
|---|---|
| `concept://product` | Describe Orkestia by what the live catalog and runs show. The catalog is authoritative; documents are not. |
| `rule://grounding` | A type is a capability, not a run. The total is a capability count. Never infer architecture, infrastructure, pricing, or maturity you did not read from a tool. |
| `rule://getting-started` | `whoami` first. Discovery before start. Type tools before a run exists; run tools after. |
| `rule://authenticated-context` | `organization_uuid` and `actor` come from the token. Pass them only when a schema declares them without a context source, and then only the `whoami` value. |
| `rule://prerequisites-first` | `has_prerequisites: true` means call `get_workflow_prerequisites` and satisfy the guide before `start_workflow`. |
| `knowledge://mcp/public-boundary` | The public surface is discovery, schemas, starts, status, history, stuck runs, retry. No private HTTP APIs, no guessing types, no starting with unknown inputs. |

## Namespace → object → skill

First-level namespaces observed on 2026-09-03 (91 total). Re-list with `list_workflow_namespaces`; this table is orientation, not inventory.

| Domain | Namespaces | Root object | Skill |
|---|---|---|---|
| Identity and tenancy | `identity`, `user`, `policy`, `security` | organization, member, identity app, end-user, seat, feature flag, org denylist | `orkestia-org-and-team` (members, tokens), `orkestia-app-platform` (end-users) |
| Provider credentials | `connection` | connection | `orkestia-connections` |
| Clouds | `aws`, `gcp`, `azure`, `mgc` | connection UUID | operating loop by prefix |
| Edge and CDN | `cloudflare`, `bunnycdn`, `netlify`, `vercel` | connection UUID | operating loop by prefix |
| Kubernetes and deploy | `kubernetes`, `k8s`, `cluster`, `deploy`, `gitops`, `argocd`, `net` | deployment target | operating loop by prefix |
| Source and CI | `github`, `gitlab`, `git`, `repligit` | connection, repo, PR | `orkestia-github` |
| Compute fleets | `runner` | runner group, environment, execution | `orkestia-runners` |
| Inventories | `registry`, `network` | registry account, network account | `orkestia-registry-network` |
| Work ledger | `ticket`, `roadmap`, `approval` | ticket | `orkestia-tickets` |
| Orchestration | `composition`, `control`, `schedule`, `queue`, `hook`, `webhook` | composition, virtual workflow, schedule | `orkestia-compositions` |
| AI workforce | `staff`, `agents`, `ai`, `ai-provider`, `aria`, `dgi`, `chat` | actor, agent config, session | `orkestia-staff`, `orkestia-agents` |
| App data and hosting | `appdata`, `apphost`, `storage`, `kv` | virtual table, hosted release, storage object | `orkestia-app-platform`, `orkestia-builder-data` |
| Billing the org | `subscription` | subscription, seat, add-on | `orkestia-subscription` |
| Customer commerce | `stripe`, `abacatepay`, `mercadopago`, `bling`, `xero` | connection UUID | operating loop by prefix |
| Messaging and ops | `slack`, `telegram`, `wasender`, `notification`, `resend`, `sendgrid`, `linear`, `notion`, `sentry` | connection UUID | operating loop by prefix |
| Observability and audit | `lumen`, `audit`, `failguard`, `security` | error group, audit run, org policy | operating loop by prefix |
| Data and hosting providers | `neon`, `sql`, `hostinger`, `firecrawl`, `docusign`, `sap`, `translation` | connection UUID | operating loop by prefix |
| Media and social | `media`, `publisher`, `meta`, `linkedin`, `youtube`, `google`, `canvas`, `realoficial` | connection UUID | operating loop by prefix |
| Vertical packs | `ifood`, `deere`, `agriculture`, `regulado`, `lovable`, `spad` | vertical objects | operating loop by prefix |
| Internal or demo | `demo`, `data` (reads shared by domains) | — | skip `demo.*`; `data.*` reads are safe |

## Kinds, scopes, flags

| Field | Values | Read it as |
|---|---|---|
| `workflow_kind` | `state_machine`, `dag`, `data` | atomic operation, layered multi-step, persistence or query |
| `scope` | `organization`, `library`, `none`, `subscription`, `app`, `actor`, `project`, `system` | what the type binds to |
| `read_only` | true / false | safe to start without confirmation |
| `featured` | true / false | author's entry-point hint |
| `has_prerequisites` | true / false | read the guide before starting |
| `end_user_eligible` | true / false | may be used inside logic exposed to end-users |
| `requires_organization_uuid` | true / false | whether the org must be resolvable; still context-injected |
| `is_terminal` (run) | true / false | the run is finished |
| `terminal_status` (run) | `success`, `failed` | how it finished |
| `state_name` (run) | `completed`, `failed`, `remediation_pending`, … | where it is now |

## Object dependency order

```
account
└─ organization (console-created)
   ├─ member token ─────────────── MCP / CLI calls
   ├─ connection ───────────────── every provider namespace
   │  ├─ runner group → environment → execution → warm pool
   │  ├─ registry account, network account
   │  └─ GitHub repos, storage buckets, AI model bindings
   ├─ identity app ─────────────── end-users, seats, app-organizations, AppHost site
   │  └─ exposed virtual workflows
   ├─ composition → virtual workflow → schedule / exposure
   ├─ agent config → actor (staff) → session
   ├─ ticket ───────────────────── plan gate → git-work → delivery
   └─ subscription ─────────────── seats, add-ons, gates on runners and AppHost
```
