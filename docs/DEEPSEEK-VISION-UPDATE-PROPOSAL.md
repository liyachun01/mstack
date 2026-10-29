# Existing DeepSeek vision plugin update

**Reactivated and corrected retry approved on 2026-10-02:** the user accepts upstream pnpm use and requests “continue fix,” superseding the interim npm-only decision. Apply the already proposed corrected direct-pnpm command and recoverable dependency-directory move below; do not ask for this same approval again. No npm migration or package-manager install/removal. Profile startup and `dsh plugin` wrapper reconciliation remain outside this direct-update step.

## Completed retry — 2026-10-02

Subsequent read-only React investigation: [the Web shell supplies all vision browser imports](DEEPSEEK-WEB-SMOKE-PROPOSAL.md), including bundled React 18.3.1. No extra React package is indicated by the standalone warning. Source-only audit/9 helper tests passed; browser/profile/vision startup remains unexecuted. The existing Python cache marker matches the packaged snapshot/requirements, not proof of runtime health. The next separately gated foundation smoke excludes vision to avoid automatic preparation/install actions.

- Installed **@anionex/dsh-vision-toolkit 0.1.46** with existing Node **24.19.0**, cached pnpm **10.33.0**, corrected `--config.` flags and `--ignore-scripts`. Command exited 0 in 7.4 seconds, 11 resolved/downloaded/added profile packages. No new manager/runtime installed; CLI/MCP client remain **0.2.0-rc.2**.
- Fresh complete-home comparison against the existing verified archive passed before mutation. Only the old profile `node_modules` was moved intact to `/home/developer/workspace/mcp-stack/backups/deepseek-vision-update-20261001.j5zoEz/original-node_modules`; original archive/checksums/manifests retained. No deletion or npm-lock migration.
- pnpm retained `^0.1.46` despite `--save-exact`; detected before completion. Corrected only that approved dependency specifier using `apply_patch` in profile `package.json`, `pnpm-lock.yaml` and generated `node_modules/.pnpm/lock.yaml`. Actual installed version/resolved tarball unchanged, no second installer invocation. Exact **0.1.46** pin and identical lock snapshots verified. Bundle list/all other manifest fields unchanged.
- Lock integrity matches the pinned tarball; direct dependencies saxes **6.0.0**, tar **7.5.22**, undici **8.10.0**, zod **4.4.3** verified. Hoisted layout, pnpm version, no-auto-peer setting and project-local `infra/harnesses/deepseek/state/pnpm-store/v10` verified. Cache/state remain under the ignored mode-0700 parent; private metadata/lock integrity inventory at `infra/harnesses/deepseek/state/vision-update-verification.json` (0600).
- Missing-peer warnings are retained as a qualification limit, not silently “fixed.” All **21 @deepseek-ai peers** are present in the installation-owned CLI tree and their declared ranges accept actual bundled versions. **React is not present as a standalone installed peer** in that tree/profile; client source references it, so actual frontend resolution/boot remains unqualified. Do not claim all peers or Web UI/plugin behavior passed; no automatic peer install or React addition.
- Protected settings/credentials/sessions/profile YAML/workspace contents, file inventory, modes and symlinks match pre-update manifests; settings and credentials remain **0600**. Global package version identities, CLI entry hash/bin link and all **21 containers** (IDs/status/start times/restart counts/ports/networks) unchanged. No service/MCP/database/Basic Memory/PKM action or model download/call.
- No `dsh plugin` wrapper reconciliation, profile startup, Python bootstrap, model/vision test, upstream patch or permission exemption. Runtime and unresolved React qualification are the next proposed investigation before project-local harness integration, requiring a separate concrete startup/test proposal.
- Backups remain restricted/verified; old complete dependencies plus archive permit recovery. No rollback needed, no cleanup performed. Any later restore remains separately gated, preserving intervening user changes.

The attempt/proposed-command sections below are historical for audit; they are not a request to rerun the completed installation.

2026-10-01 historical attempt: approved update rejected at pnpm CLI options before installation; plugin then remained 0.1.32. The retry result above is authoritative. The plugin is third-party, maintained by Anionex, not an official DeepSeek package.

## Attempt result and corrected retry

- Executed the initially approved command with cached pnpm **10.33.0**, existing Node **24.19.0**, scripts disabled. It exited 1: unknown options `state-dir`, `auto-install-peers`, `manage-package-manager-versions`, `update-notifier`. Their presence in pnpm's configuration schema does **not** mean its `add` command accepts them as ordinary flags; the original proposal's qualification was incomplete.
- Inspected local pnpm parser: unknown-option rejection occurs before configuration loading/install handling. A complete `tar --compare` against the fresh `.dsh` archive passed after the attempt, as did protected-file hashes/inventory/modes/symlinks. Global package versions, CLI entry hash/link and all **21** container IDs/status/start times/restart counts/ports/networks are unchanged. No plugin/profile/model/MCP/service action succeeded; no automatic retry.
- Restricted backup retained at `/home/developer/workspace/mcp-stack/backups/deepseek-vision-update-20261001.j5zoEz/` (0700), `existing-home.tar.gz` and private manifests (0600); archive listing and checksum checks passed. Prior CLI backup retained. No restoration or cleanup required.
- Corrected flags below use pnpm's `--config.` normalization, verified in the installed 10.33.0 parser and [documented CLI escape hatch](https://pnpm.io/pnpm-cli). The three Boolean settings are typed Boolean in pnpm's configuration schema; `state-dir` is a String.
- A second issue was found read-only before retry: existing `node_modules/.modules.yaml` refers to `/home/developer/.local/share/pnpm/store/v10`, whereas the proposed update uses a new project-local store. pnpm explicitly rejects incompatible existing stores. **Additional proposed action:** after fresh protected checks, move only `/home/developer/.dsh/profiles/web/node_modules` intact into the restricted backup as `original-node_modules`, then build replacement dependencies. No deletion, `--force`, global store cleanup or use of the old global store. This move has not been executed.

The retry keeps the same pinned version and exclusions. Obtain approval for the corrected command and this narrow recoverable dependency-directory move before acting. Before retry, require complete archive comparison still passes and `original-node_modules` does not exist; if the user home changed, stop and take a newly reviewed backup rather than proceeding against stale manifests. Confirm source is a real directory, destination backup is restricted, and same filesystem permits the move.

```sh
# Only after separate retry approval and the checks above.
umask 077
test -d /home/developer/.dsh/profiles/web/node_modules
test ! -L /home/developer/.dsh/profiles/web/node_modules
test ! -e /home/developer/workspace/mcp-stack/backups/deepseek-vision-update-20261001.j5zoEz/original-node_modules
mv -T -- /home/developer/.dsh/profiles/web/node_modules \
  /home/developer/workspace/mcp-stack/backups/deepseek-vision-update-20261001.j5zoEz/original-node_modules
# Then execute the corrected pinned pnpm command in the operation section below.
```

If installation fails after the move, retain the original dependency directory/archives and report; do not boot the incomplete profile or overwrite changed settings. A separately approved rollback can move aside only any replacement `node_modules`, put `original-node_modules` back, and restore only profile `package.json`/`pnpm-lock.yaml` if modified. Never restore the whole home over live user changes.

## Target and compatibility

- Ubuntu devbox, existing `/home/developer/.dsh/profiles/web` profile. Update only existing `@anionex/dsh-vision-toolkit` **0.1.32 → 0.1.46**, the registry `latest` checked on 2026-10-01, published `2026-10-01T04:46:42.727Z`.
- [Maintainer source](https://github.com/Anionex/dsh-vision-toolkit), [registry metadata](https://registry.npmjs.org/@anionex/dsh-vision-toolkit/0.1.46).
- Tarball: `https://registry.npmjs.org/@anionex/dsh-vision-toolkit/-/dsh-vision-toolkit-0.1.46.tgz`; integrity `sha512-81V9AI0u77D3B9kVrdHvN7x7iOYwgLO/hsdDZNPsZUTELw0eZI2b68zHR5ltQgR9SqTt4umQzuMUgvx1K1sxjQ==`. Downloaded and inspected in memory; integrity matched, no extraction/execution. Root has no install/postinstall/prepare lifecycle scripts; build/prepack scripts exist and will not run.
- Node requirement `^22.19.0 || >=24.0.0` accepts existing **24.19.0**. Declared DeepSeek peer ranges explicitly include **0.2.0-rc.2**. This establishes declared compatibility, **not runtime qualification**.
- Fixed direct dependencies: `saxes 6.0.0`, `tar 7.5.22`, `undici 8.10.0`, `zod 4.4.3`. Preserve existing `autoInstallPeers: false` / `nodeLinker: hoisted`; do not fetch individual DeepSeek packages using their stale `latest` tags. The harness supplies its matched core packages when a separately approved profile starts.

## Exact proposed operation

First recheck running recognized DeepSeek processes, current CLI/plugin versions, retained profile and protected-home hashes, disk space and container inventory. Do not stop a running session automatically. Create a **new** unique mode-0700 backup directory under ignored `backups/`; archive the complete existing `.dsh` home with mode-0600 output and validate the archive. Keep the earlier CLI backup too. Capture private before manifests so settings, credentials, sessions, profile YAML, workspace configuration and all unrelated files can be compared without displaying their content.

Use the **already cached pnpm 10.33.0** directly through existing Node, bypassing the Corepack shim and disabling pnpm self-management. No Node/pnpm/Corepack install or global configuration change:

```sh
umask 077
NODE_DISABLE_COMPILE_CACHE=1 \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  /home/developer/.cache/node/corepack/v1/pnpm/10.33.0/bin/pnpm.cjs \
  --dir /home/developer/.dsh/profiles/web \
  add --workspace-root --save-exact @anionex/dsh-vision-toolkit@0.1.46 \
  --registry=https://registry.npmjs.org \
  --store-dir=/home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state/pnpm-store \
  --cache-dir=/home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state/pnpm-cache \
  --config.state-dir=/home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state/pnpm-state \
  --config.auto-install-peers=false --config.manage-package-manager-versions=false \
  --config.update-notifier=false --ignore-scripts --reporter=append-only
```

The parent project state directory is already ignored/restricted by the CLI step. Confirm cached pnpm identity/entrypoint before execution; if missing or mismatched, stop instead of fetching it. The corrected `--config.` options bypass command-specific flag validation and are normalized into known typed configuration settings; the initial ordinary-flag form was rejected. [Exact package pins/workspace-root add](https://pnpm.io/cli/add), [pnpm configuration](https://pnpm.io/settings).

Expected mutations: dependency version in existing `profiles/web/package.json` (exact `0.1.46`, preserving the bundle list and other fields), matching `pnpm-lock.yaml`, profile `node_modules/`, ignored project-local pnpm cache/store/state and a private backup. This narrow update of the user's **existing plugin dependency configuration** is the explicit exception being proposed; it does not relocate settings or create new user-level mcp-stack config. No other `.dsh` files, shell config, global tools or container state may change. No ports/listeners added; no profile launched.

## Verification, exclusions and rollback

Verify package identity/version, registry integrity in lockfile, exact direct dependency pin, peer declaration and unchanged bundle list; inventory resolved dependencies. Compare private hashes/modes/symlinks for settings, credentials, YAML, workspace config, sessions and other files outside the approved dependency paths. Compare all retained container identities/start times/status/ports/networks/restart counts. Missing supplied peers may produce warnings while this profile is stopped; do not fix those by auto-installing packages.

No `dsh plugin`, `dsh web`, Python bootstrap, vision model download, remote provider configuration, authentication, paid API/model call, MCP registration or functional vision/session test is included. If disabled scripts prevent installation, stop and propose the exact additional action; never retry with scripts enabled automatically.

Report completion/deviations immediately and stop before the next component. A separately approved rollback moves aside only the new profile dependency directory and restores the old profile `package.json`, lockfile and complete `node_modules` from the validated backup. Never overwrite credentials/settings/sessions or the entire `.dsh` home automatically. Backups remain private and retained; no cleanup is approved.
