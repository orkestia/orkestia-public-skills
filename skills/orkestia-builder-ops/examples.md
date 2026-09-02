# Builder ops examples

Never commit credentials, org UUIDs, or apply receipts.

---

## 1. Bind the org’s only active GCP connection

```bash
orkestia resources import --provider gcp --as gcp-primary --out app/resources/connections.resources.ts
orkestia resources validate
orkestia resources plan
```

Review the plan (`bind` vs `create`). Apply with `--yes` only after the selector is unique. If two GCP connections are active, add `--name` to disambiguate.

---

## 2. Agent runners (provision acknowledgement)

After connections apply cleanly:

```bash
orkestia resources plan
orkestia resources apply --yes --allow-provision
```

Skip `--allow-provision` when the plan is bind/noop only. Staff later:

```ts
agentConfig("consumer", {
  runnerGroupUuid: resourceOutput("runner-group", "agent-runners"),
  modelProfile: resourceOutput("model-profile", "primary-ai"),
});
```

---

## 3. Staff dry-run then apply

```bash
orkestia composition push --save
orkestia staff compile
orkestia staff plan
orkestia staff apply --dry-run --approved-by-user-uuid "$ORKESTIA_APPROVED_BY_USER_UUID"
orkestia staff apply --yes --approved-by-user-uuid "$ORKESTIA_APPROVED_BY_USER_UUID" --watch
```

A failed parent, partial, or blocked apply exits non-zero even without an apply-run UUID.

---

## 4. AppHost smoke

```bash
orkestia apphost publish          # plan
orkestia apphost publish --yes
```

Clean browser: root HTML 200, JS 200, hosted login `client_key` matches config, `/callback` returns, workspace query works, one exposed workflow starts. If login hits the wrong app, Identity UUID/`client_key`/site claim are misaligned — republishing the ZIP will not fix that.
