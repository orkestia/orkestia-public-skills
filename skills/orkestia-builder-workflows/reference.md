# TypeScript composition reference

Recipes: [SKILL.md](SKILL.md).

## Combinators

| Construct | Role |
| --- | --- |
| `defineComposition({ name, inputs, metadata }, (c) => …)` | authoring unit |
| `t.string()` / `integer` / `boolean` / `uuid` / `list` / `dict` + `.optional()` | input decls |
| `c.step(typeOrBinding, args)` | atomic step; args are symbolic |
| `c.layer(name, fn)` | explicit layer |
| `c.parallel(...)` | explicit parallelism |
| `c.output({ … })` | composition outputs |
| `cond.eq` / `neq` / ordering / `truthy` / `falsy` / `in` / `not` / `allOf` / `anyOf` | runtime conditions |
| `.when(cond)` | skip/run step |
| `fanOut(items, fn)` | map collection |
| `loop({ maxIterations, breakWhen }, …)` | bounded iteration |
| `.compensateWith(...)` | saga compensation |
| `.unrecoverable()` | no compensation |

## Authoring vs compiled dialect

| Authoring (TS / `composition.save` input) | After server compile |
| --- | --- |
| `input_mapping` wire key `field` | unchanged conceptually |
| upstream `source: "step"` | compiled DAG may rename to `state_data` |
| no `content_hash` | server stamps hash |

Do not hand-write compiled DAG JSON.

## CLI

```bash
orkestia composition push                 # offline JSON
orkestia composition push --save          # save + activate
orkestia composition push --save --expose
orkestia composition push --save --force  # ignore skip cache
orkestia composition expose [--yes]
```

## Artifacts

| File | Meaning |
| --- | --- |
| `.orkestia/<name>.composition.json` | authoring JSON |
| `.orkestia/composition.push-state.json` | active type + source hash cache |
| `.orkestia/app.lock.json` | browser exposure map |

## End-user vs protected

| `metadata` | Typical |
| --- | --- |
| `{ enduser: true }` | eligible for exposure |
| `{ enduser: false, operator_only: true }` | Staff / member only |

Still must not expose: Identity admin, `connection.setup`, runner provision, protected AI config, support-only seed.

## React

`useWorkflow(workflowType)` under `AppShell`: `start(inputs)`, `phase`, `output`, `error`. Phase is derived from `state_name` / `is_terminal` / `terminal_status`.
