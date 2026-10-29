# DeepSeek CLI update — existing configuration retained

Requested on 2026-10-01. **Approved CLI-only update completed on 2026-10-01.** This proposal takes precedence over the earlier recommendation to create a new project `DSH_HOME`: the user requests keeping the existing configuration. No config relocation, new profile, MCP connection, service start or model call is included. Discovery/proposed-operation details below describe the pre-update state; the completion record is authoritative for current versions.

## Completion record

- Existing Ubuntu user-global CLI **0.1.0-rc.7 → 0.2.0-rc.2**, using existing Node **24.19.0** and the exact npm command below. Bundled MCP client and all inspected bundled `@deepseek-ai/dsh-*` packages are **0.2.0-rc.2**. Do not update these individually using `latest`: some package tags still point to older releases.
- npm succeeded with lifecycle scripts disabled: 191 packages added, 105 removed and 347 changed inside the CLI dependency tree. A `node-domexception@1.0.0` deprecation warning and npm major-update notice were informational; npm remains **11.17.0**, Corepack and other global package identities unchanged. No Node/mise/npm upgrade was performed.
- Reviewed installed dispatch and ran only explicit-Node `--version`: **0.2.0-rc.2**, exit 0. No profile/plugin startup or native/vision/model functional test; disabled-script limitations remain unqualified beyond this smoke check.
- Complete `.dsh` regular-file content hashes and file inventory/modes/symlinks match before/after, including after the version command. Existing settings/credentials remain 0600; all sessions/profile config and installed vision plugin **0.1.32** are retained.
- All **21** existing container IDs/status/start times/restart counts/ports/networks exactly match the pre-update inventory. No service/MCP/database/PKM action.
- Restricted backups: `/home/developer/workspace/mcp-stack/backups/deepseek-cli-update-20261001.8fuIQV/` (0700), containing `cli-0.1.0-rc.7.tar.gz`, `existing-home.tar.gz` and private manifests (0600). Both archives list successfully and checksum verification passes. These contain credentials/private sessions: do not publish. Restore remains separately gated; no cleanup needed or executed.
- `.gitignore` now excludes `infra/harnesses/deepseek/state/`; its parent is 0700. npm cache/logs, private resolved dependency tree (`npm ls --global --all --json`, no reported problems) and downloaded public tarball response-body integrity records reside there. This global npm operation produced no lockfile; the attempted inventory copy therefore had no source and made no file. Do not treat the tree/cache inventory as a complete reproducible dependency lock. All **277** inspected bundled `@deepseek-ai/dsh-*` packages match 0.2.0-rc.2. No global npmrc/shell configuration created.
- Subsequent step on 2026-10-02: [vision plugin 0.1.46 pnpm update completed](DEEPSEEK-VISION-UPDATE-PROPOSAL.md), after the user accepted upstream pnpm and approved the corrected retry. Interim npm migration was cancelled, never executed. Exact plugin pin/lock integrity/protected state checked; runtime/React peer qualification and project-local harness integration remain later steps. The “0.1.32 retained” entry above describes the earlier CLI-only checkpoint.

## Exact target and source

- Execution domain: **Ubuntu devbox**, existing user-global fnm installation, not macOS or an apt/system installation. This is an explicitly proposed exception for updating the user's existing CLI, not permission to install Ubuntu mise/Node or other global tools.
- Node **24.19.0**, verified with its existing absolute binary. Installed `@deepseek-ai/dsh` **0.1.0-rc.7**; bundled MCP client **0.1.0-rc.8**.
- Official npm registry `latest` and `next` both resolve to **0.2.0-rc.2**, published `2026-09-29T09:56:27.792Z`. This is a release candidate/developer preview, not a stable GA release. [Official package metadata](https://registry.npmjs.org/@deepseek-ai/dsh), [official product/preview warning](https://github.com/deepseek-ai/deepseek-harness).
- Candidate tarball: `https://registry.npmjs.org/@deepseek-ai/dsh/-/dsh-0.2.0-rc.2.tgz`; integrity `sha512-EAJ3gPNcVt/uv8X19PMm9NkVhWgT7xXNMk0UKCVm+IQ5rpSQOcsMUa0HWlnYYVybKMsccjcRB21vVVsaXQ6IdA==`, SHA-1 `dfc8f7e09cfa96b854d6f0cf3a973ce7f2948925`.
- Tarball inspected in memory only, integrity matched, package version/bin metadata checked; no files extracted, code executed or installer invoked. Root package declares no lifecycle scripts. Dependencies still need resolution; an exact CLI pin does not imply a fully locked transitive tree. Record resolved versions/integrities after installation.

## Where the existing configuration is

Effective `DSH_HOME` is `/home/developer/.dsh` (default; no override observed):

- `settings.yaml`: existing UI/provider/default-model settings, mode `0600`; values not displayed.
- `.credentials.yaml`: existing credentials, mode `0600`; contents not read or displayed.
- `profiles/web/cordis.yml` and `cordis.patch.yml`: existing profile/patch files, regular files with empty parsed lists; comments retained, no modifications.
- `profiles/web/package.json`, `pnpm-lock.yaml`, workspace file and `node_modules/`: existing user plugin configuration/dependencies.
- Other existing sessions/state under this home stay intact; do not dump their content or copy them into a new runtime home.

These are **pre-existing user-level files**, not created by mcp-stack. Reuse them as requested, without moving them or placing a new config there. Any future mcp-stack launcher/MCP additions still require a project-local proposal under `infra/`; do not silently edit these global settings to add the stack.

Global executable resolves to `/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh/lib/bin.js`. The shell exposes it through a transient fnm multishell path; use the stable Node prefix for this update, not that transient path. No fnm selection/default, Node/npm version, shell profile or macOS mise setting changes.

## Compatibility concern: preserve, do not silently repair

Existing web profile has third-party `@anionex/dsh-vision-toolkit` **0.1.32**. Its declared DeepSeek peer ranges are `^0.1.0-rc.6`, which do not include `0.2.0-rc.2`. This is a declared compatibility mismatch, not proof of runtime failure. Do not update/remove/reinstall the plugin, change its lockfile or start the profile to see what happens during this CLI-only step.

Keep user config/credentials unchanged; bundled defaults/code can change with the CLI version. CLI metadata/version verification is **not** web-profile/plugin/session compatibility qualification. Propose that test separately, against a protected copy/explicitly approved environment, before launching the retained profile. No model/API test is implicit.

## Proposed commands after explicit approval

Before mutation, recheck exact CLI/Node/config identity and recognized running dsh entrypoints, free space, existing protected file hashes and unchanged stack container inventory. No listener on Ubuntu 3080 was observed during discovery; that does not exclude custom ports or remote launchers. Do not stop a live agent automatically.

Create a unique restricted backup directory under ignored repository `backups/`. Preserve the full old CLI directory **including nested dependencies** and the original `bin/dsh` symlink, plus a separate protected archive of `/home/developer/.dsh` (contains credentials/private sessions). Observed apparent sizes: old CLI about **272 MiB**, existing home about **185 MiB**; pre-update free space was **228 GB**. Archives were created and verified as recorded above.

```sh
# Run only after approval, from /home/developer/workspace/mcp-stack.
umask 077
mkdir -p backups
MCP_STACK_DEEPSEEK_BACKUP="$(mktemp -d backups/deepseek-cli-update-20261001.XXXXXX)"
tar -C /home/developer/.local/share/fnm/node-versions/v24.19.0/installation \
  -czf "$MCP_STACK_DEEPSEEK_BACKUP/cli-0.1.0-rc.7.tar.gz" \
  lib/node_modules/@deepseek-ai/dsh bin/dsh
tar -C /home/developer -czf "$MCP_STACK_DEEPSEEK_BACKUP/existing-home.tar.gz" .dsh
tar -tzf "$MCP_STACK_DEEPSEEK_BACKUP/cli-0.1.0-rc.7.tar.gz" >/dev/null
tar -tzf "$MCP_STACK_DEEPSEEK_BACKUP/existing-home.tar.gz" >/dev/null
rg --files --hidden --no-ignore -0 /home/developer/.dsh \
  | sort -z | xargs -0 sha256sum > "$MCP_STACK_DEEPSEEK_BACKUP/existing-home.sha256"
sha256sum "$MCP_STACK_DEEPSEEK_BACKUP/cli-0.1.0-rc.7.tar.gz" \
  "$MCP_STACK_DEEPSEEK_BACKUP/existing-home.tar.gz" \
  > "$MCP_STACK_DEEPSEEK_BACKUP/archives.sha256"
# Add infra/harnesses/deepseek/state/ to .gitignore using apply_patch,
# then create that state directory with mode 0700 before npm writes cache/logs.
/home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/npm/bin/npm-cli.js \
  install --global @deepseek-ai/dsh@0.2.0-rc.2 \
  --prefix /home/developer/.local/share/fnm/node-versions/v24.19.0/installation \
  --registry https://registry.npmjs.org \
  --cache /home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state/npm-cache \
  --ignore-scripts --no-audit --no-fund
# Compare private home-file hashes without displaying the manifest.
sha256sum --check --quiet "$MCP_STACK_DEEPSEEK_BACKUP/existing-home.sha256"
```

Changes: only the existing global dsh package/dependency tree and its CLI link, restricted ignored backup files, and project-local npm cache/log state. Add `infra/harnesses/deepseek/state/` to `.gitignore` before creating it. Preserve source files/other global packages/configs and existing `.dsh` home. No npmrc/global environment defaults or shell activation changes. Explicit prefix/cache/registry are per-command settings, not persistent global configuration. [npm install flags](https://docs.npmjs.com/cli/v11/commands/npm-install/).

Lifecycle scripts disabled, audit/funding extras off. If a native dependency needs a build/install script, report it and propose that exact script separately; do not rerun without `--ignore-scripts`, download another runtime or install compilers automatically.

## Verification and after-report

1. Revalidate installed package and bundled MCP versions/dependency inventory, symlink and Node version; keep detailed manifests private under ignored state if they include machine paths.
2. Only invoke the verified version-only dispatch, using explicit existing Node:

   ```sh
   /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
     /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/@deepseek-ai/dsh/lib/bin.js \
     --version
   ```

   Inspect the installed dispatch before execution; no profile/default boot, config dump, `web`, plugin command or agent job. If imports/version dispatch require unexpected initialization or fail, stop and report rather than broadening scope.
3. Compare existing config/credential/profile/lock hashes, file modes, session/state manifest and other global package identities before/after. Do not publish credential hashes or contents. Confirm no existing container lifecycle/network/config changes.
4. Report exact resolved versions/files, verification results, disabled-script limitations and the plugin compatibility caveat. Stop before startup, launcher setup, MCP registration, n8n or model tests.

## Rollback

The archived complete **0.1.0-rc.7 tree**, not a fresh registry reinstall with newly resolved dependencies, is the exact-code recovery source. A separately approved rollback would move aside only the newly installed dsh package directory into restricted recovery storage, restore the old package tree to its validated exact location and restore the old CLI link. Do not delete/move the Node installation prefix or unrelated global packages.

Config should need no restoration because this step never boots it. If hashes differ unexpectedly, stop and diagnose; do not overwrite current settings/credentials/sessions from the backup automatically. Keep backups and the failed/new tree for recovery. No broad uninstall, prune or recursive home-directory deletion.
