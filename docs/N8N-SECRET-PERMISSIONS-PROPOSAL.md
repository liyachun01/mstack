# n8n secret permissions: diagnosed cause and scoped fix

Approved/executed2026-10-04, user “approve”. **Secret-volume repair succeeded;
the subsequently approved cache tmpfs now makes the app healthy.** The historical
proposal/outcome below records the secret step and its next-cache checkpoint;
current [completed app qualification](N8N-STATIC-CACHE-PROPOSAL.md). No new image/version,
host tool, second Docker, runner, workflow, model or harness connection installed.

## Actual repair outcome

- Private backup `backups/n8n-secret-before-20261004-5b74k7kk/`, private operation
  `infra/n8n/state/secret-repair-vzhjpu59/` retained,0700/0600. First prepare hit an
  isolated-Python module import-path omission before any lifecycle change; fixed
  the explicit project import path. **17 offline contracts and shell syntax pass**.
- Stopped only the failing n8n app; created `mcp-stack-n8n-secrets`; one same-image
  offline/root/CHOWN-only initializer copied original keys over stdin, assigned
  UID/GID1000 and0700/0600 modes, then auto-removed. No pull or source chmod/chown.
- Applied only the approved secret-delivery Compose delta; recreated n8n once.
  Read-only volume content/ownership/modes verified against original keys without
  printing them (`secret-mount-qualified.json`). n8n reads keys and completes
  official migrations into its isolated DB: **142 public tables**.
- Startup next fails while creating `/home/node/.cache`; app exits/restarts, UI
  unavailable. No further restart/config change performed. Readiness helper
  stopped on the first failed state; partial diagnostics retained. The preapproved
  Docker restart policy remains active. See the concrete next proposal above.
- All21 other container snapshots, DB owners/ACLs/role flags, DeepSeek home,
  source keys and protected files except the approved Compose delta unchanged.
  No owner account, runner/workflow/model or memory/harness integration. Data-safe
  n8n-only stop remains the separately reviewed rollback; no deletion/cleanup.

## Evidence and cause

- Official2.41.6 image downloaded and verified against the approved digest,
  Linux/ARM64, version label and official non-root `node` user.
- App `mcp-stack-n8n-1` exists on **macOS OrbStack**, but exits1 and is restarting
  under its declared `unless-stopped` policy; readiness/UI5678 unavailable. Not OOM.
- Exact startup error: `EACCES: permission denied, open '/run/secrets/n8n_password'`.
- All three source files are UID/GID501:501, mode0600, on both Ubuntu and the
  macOS mirror. Ordinary Compose file-backed secrets are bind mounts, not
  ownership-remapped Swarm secrets. The image's non-root user cannot read these
  private files; `_FILE` loading works but the OS denies access.
- Adding secret `uid`/`gid`/`mode` is not a valid fix here: Docker documents that
  these options are not implemented for file-backed Compose secrets because
  bind mounts cannot remap ownership. [Docker Compose services](https://docs.docker.com/reference/compose-file/services/#secrets).
- Original private files/keys, DB owners/ACLs/role flags, protected files,
  DeepSeek home and all21 pre-existing containers remain unchanged from the
  separately retained **post-user-engine-restart** baseline. No owner account,
  external runner or workflow was created.

Private retry evidence: `infra/n8n/state/retry-after-host-restart-i5fht3la/`, including
`baseline.json`, completed `pull-app.log`, `start-app.log`, `startup-private.log`
and `failed-startup-evidence.json`; directories0700/files0600. Do not publish raw
logs or hashes/contents of credentials. Original failed-pull evidence is retained.

## Proposed one-step repair and authority

1. Revalidate current exact image/container ID, three source-key fingerprints,
   DB/protected/home state and all21 other containers. Back up current app
   definition privately. Refuse colliding volume/helper names or unexpected state.
2. **Stop only the failing n8n container** to end its restart loop. Do not stop
   PG, Basic Memory, either graph, gateway, {{mstack:CLIENT_REPO}} or DeepSeek.
3. Create dedicated named volume **`mcp-stack-n8n-secrets`** on macOS OrbStack.
   Copy exactly the existing three keys into it without generating/rotating keys
   or changing source permissions. Transport contents over the helper's stdin,
   never command arguments, environment variables or printed output.
4. One temporary initializer container, **same already verified official n8n
   image**, no pull, network `none`, no port/socket/host bind, read-only root,
   0.5CPU/128MiB/64PIDs, `no-new-privileges`, all capabilities dropped **except
   `CHOWN`**. Its Node entry point only reads the stdin payload and creates
   three exclusively opened0600 files; determine the image's `node` UID/GID from
   `/etc/passwd`, assign files and directory to that identity, directory0700.
   Write/chown files before changing directory ownership. No n8n app startup,
   database/network request or shell/package/model execution in this helper.
   Temporary root plus `CHOWN` is solely for volume initialization, not the app;
   helper auto-removes on exit, retaining the named volume. Stop on any failure.
5. Change **only secret delivery** in `infra/n8n/compose.yaml`: replace the three
   file-backed secret mounts with `n8n_secrets:/run/secrets:ro`, declaring the
   named volume external after its explicit creation. Remove unused top-level
   Compose secret bindings. Keep `_FILE` variables/paths, official entry point,
   app user `node`, all dropped capabilities, read-only root, image, DB/network/
   port/resource/log settings and the existing application volume unchanged.
6. Adapt reusable repair/qualification logic and tests under `integrations/n8n/`,
   existing guarded launcher under `infra/n8n/`; private operations under ignored
   `infra/n8n/state/`. Preserve initial YAML as historical evidence; do not rerun
   database provisioning, initial prepare/activate or the completed image retry.
7. Recreate **only** n8n once, reusing its app volume, three networks and keys,
   then bounded readiness/security/persistence metadata checks. No further pull.

Exact scoped lifecycle shape (not run):

```sh
macctl run docker stop --time 30 mcp-stack-n8n-1
macctl run docker volume create --label com.mcp-stack.owner=n8n mcp-stack-n8n-secrets
# The initializer is invoked by the guarded Python helper with secret stdin;
# the following script/flags contain no secret values.
macctl run docker run --rm -i --name mcp-stack-n8n-secret-init \
  --pull never --network none --read-only --user 0:0 \
  --cap-drop ALL --cap-add CHOWN --security-opt no-new-privileges:true \
  --cpus 0.5 --memory 128m --pids-limit 64 \
  --mount type=volume,src=mcp-stack-n8n-secrets,dst=/target \
  --entrypoint node \
  n8nio/n8n:2.41.6@sha256:87e0bab2c93192e8dd885ff7b0697c22a1bd97489568a8c67cc140fd7dbb342d \
  -e '<reviewed initializer, no secrets embedded>'
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml config --quiet
macctl run docker compose --project-directory . -p mcp-stack \
  -f infra/n8n/compose.yaml up -d --no-deps --pull never --force-recreate n8n
```

## Verification and rollback

Verify initialized ownership/modes and source-equivalent content privately, then
non-root app read access, readonly secret-volume mount/no host/socket bindings,
unchanged keys, bounded restart-free readiness200, editor/setup shell/entry asset,
new DB migrations, all21 existing container snapshots, DB metadata/protected/home
preservation and bounded CPU/RAM sample. Browser rendering/owner setup, workflow/
runner execution and restore/recreation persistence remain separately qualified.

The extra volume contains sensitive plaintext just like original private files
and application state. Docker administrators remain trusted; volume isolation is
not encryption or a vault. Keep original ignored private keys as recovery source;
no automatic export or cleanup. [Docker volumes](https://docs.docker.com/engine/storage/volumes/).

Rollback: separately reviewed stop of **n8n only**, preserving app/secret volumes,
DB, keys and networks. Do not restore the known-unreadable bind setup as a claimed
working rollback, delete volumes/keys, broadly `down`, or restart PG. If repair
fails, retain diagnostics and report before any further lifecycle/config change.
