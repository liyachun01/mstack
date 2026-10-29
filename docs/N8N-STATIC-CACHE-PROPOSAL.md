# n8n static cache: scoped writable tmpfs proposal

Approved/executed2026-10-04, user “go”. **n8n2.41.6 is healthy and its local UI
foundation is qualified.** Added exactly one tmpfs entry and recreated only n8n;
no download/new image, host tool, persistent volume, credentials, database
migration script, runner, workflow, harness connection or model.

## Completed outcome and handoff

- Runtime remains macOS OrbStack context `orbstack`; no Ubuntu Docker/tool install
  or global configuration change. Private backup at
  `backups/n8n-cache-before-20261004-8_02l0ld/`; original evidence retained.
- Only Compose change: approved64MiB node-owned0700 `/home/node/.cache` tmpfs.
  Stopped only the failed app and recreated it once with `--no-deps --pull never`.
  Rootfs remains read-only, official user `node`, capabilities dropped, no socket
  or privilege escalation,1CPU/1GiB/256PID limits, loopback UI and internal broker.
- **Healthy, zero restarts.** macOS readiness/root/setup HTTP200 and the editor's
  main JS entry asset200. Verified exact image/version, mounts/ports/networks,
  non-root readable source-equivalent0600 keys and0600 application settings.
- Cache verified as actual tmpfs, UID1000/mode0700, limit67,108,864bytes; generated
  index present. Observed cache use49,025,024bytes (~46.8MiB), greater than the
  raw source-file estimate26.5MiB. Keep this measured headroom in upgrade reviews;
  remeasure regenerated assets before changing versions, never silently enlarge
  the cache or disable read-only rootfs.
- All21 other container snapshots, DB owners/ACLs/role flags, original keys,
  protected files except approved Compose delta and retained DeepSeek home
  unchanged. Existing n8n DB retains142 public tables. No owner account created
  by the agent, external runner, workflow import/execution or model/memory call.
- Private qualification: `infra/n8n/state/cache-repair-2cu55z28/qualification.json`,
  run/baseline/logs0700/0600. **20 n8n offline contracts,23 DeepSeek Python tests,
  shell syntax pass**. One app sample544.3MiB/1GiB and0.01%CPU; PG52.88MiB/0.06%.
  These samples are not long-session/resource/battery guarantees.
- Open **http://127.0.0.1:5678/** on macOS and create your owner account privately.
  No paid license/model key is needed for this foundation. Browser rendering,
  owner creation, restore/recreation persistence, Code runner and workflow/harness
  integrations are separate checks; HTTP shell/assets do not prove all of them.
- No cleanup/rollback needed. Individually reviewed n8n-only stop remains a
  data-preserving rollback; DB/app/secret volumes/keys retained, cache disposable.

The original scope/evidence below records what was approved; do not rerun the
one-shot cache installer or the earlier completed secret/pull/database steps.

## Evidence from the pinned running artifact

- Official2.41.6 now reads its private keys and connects to the isolated `n8n`
  database. Official startup migrations completed: **142 public tables**. Source
  keys, DB owner/ACL/role metadata, all21 other containers, protected files except
  the approved Compose delta, and retained DeepSeek home are unchanged.
- Temporary secret initializer removed. New `mcp-stack-n8n-secrets` is read-only
  in the app; files UID/GID1000:1000/mode0600, directory0700, identical to original
  keys. Original UID501 source files remain0600, unchanged.
- Startup then fails at static-asset generation with `ENOENT: no such file or
  directory, mkdir '/home/node/.cache'`. The app is still restarting; UI not ready.
- Inspected **installed** official `dist/commands/start.js` and `n8n-core/dist/
  instance-settings/instance-settings.js` via read-only Docker copy/tar streams:
  `staticCacheDir = path.join(config.userHome, '.cache/n8n/public')`; startup creates
  this directory and writes compiled HTML/JS/CSS. The config derives userHome from
  the existing n8n data location. Moving it would also change persistence paths;
  no supported independent cache-path override was established.
- Read-only listing of installed `n8n-editor-ui/dist` measured **985 candidate
  HTML/JS/CSS files, 27,811,998 bytes (~26.5MiB)**. A64MiB cache tmpfs leaves room
  for filesystem blocks/config substitutions; this is a bound, not a claim of
  measured runtime residency or battery use. Cache regeneration happens on start.

Private evidence retained at `infra/n8n/state/secret-repair-vzhjpu59/`, original
definition backup at `backups/n8n-secret-before-20261004-5b74k7kk/`. Do not rerun
the successful secret initializer/volume creation or completed image pull.

## Exact next approval scope

1. Snapshot current app ID, all21 other containers, DB metadata, source-key and
   protected/home fingerprints; privately back up current Compose. Preserve the
  142-table DB, app volume, secret volume and keys. Recheck port5678 ownership.
2. Stop **only** the currently failing `mcp-stack-n8n-1`.
3. `apply_patch` adds this **one entry** to `infra/n8n/compose.yaml`:

```yaml
    tmpfs: ["/tmp:size=128m,mode=1777", "/home/node/.cache:size=64m,uid=1000,gid=1000,mode=0700"]
```

The existing `/tmp` is unchanged. Keep official user `node`, read-only rootfs,
all dropped capabilities, no-new-privileges, existing1CPU/1GiB/256PID limits,
loopback5678/internal broker, source/image/entry point, volumes, `_FILE` settings,
DB/network/retention/exclusions and all other settings unchanged. The cache is
ephemeral and not memory/PKM data. No root helper or added capability is needed.

4. Add a guarded one-shot cache continuation and offline exact-delta tests under
   `integrations/n8n/`; launch through the existing `infra/n8n/install-app.sh`.
   Private state remains ignored under `infra/n8n/state/`. Never repeat initial
   prepare/activation, secret repair or provisioning. No global config change.
5. Validate and recreate **only n8n once**, using the existing image without pull:

```sh
macctl run docker stop --time 30 mcp-stack-n8n-1
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml config --quiet
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml up -d --no-deps --pull never --force-recreate n8n
```

6. Bounded restart-free readiness200; editor/setup shell and JS entry asset200;
   cache owner/mode and actual tmpfs security/size; unchanged source-equivalent
   read-only keys and0600 settings; existing DB/volumes/networks; all21 other
   containers/DB metadata/protected/home preservation and bounded resource sample.
   No owner creation, workflow, model or memory call. Report failure rather than
   retrying or making the whole container writable.

Rollback: separately reviewed n8n-only stop, preserving DB/app/secret volumes,
keys/networks. tmpfs contents disappear when stopped and can be regenerated; no
durable data deletion or global restore. Do not re-enable either known-broken
configuration as a claimed working rollback, or stop/restart PG/other services.
