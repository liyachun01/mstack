# DeepSeek vision plugin — npm-only update proposal

**Cancelled on 2026-10-02, never implemented.** Latest user decision accepts upstream pnpm and approves continuing the previously proposed corrected update. Do not execute the npm migration/moves below. See [active pnpm update and result](DEEPSEEK-VISION-UPDATE-PROPOSAL.md).

2026-10-02: the user selects **npm, not pnpm**. This replaces the pnpm retry proposal; **no npm plugin install, dependency-directory move or lockfile migration has been executed**. The official CLI is already 0.2.0-rc.2; the existing third-party vision plugin remains 0.1.32. Concrete npm migration/update approval is required under the setup guard. Version 0.1.46 retains the previously proposed exact pin, not a new check of a moving tag after the date changed.

## One component, exact target

- Ubuntu devbox, existing `/home/developer/.dsh/profiles/web` profile; update existing `@anionex/dsh-vision-toolkit` **0.1.32 → 0.1.46** and manage this profile's dependency tree with npm.
- Reuse existing Node **24.19.0** and npm **11.17.0** through their absolute paths. No Node/npm/mise/pnpm/Corepack install, uninstall, shell setup or system-level configuration.
- Third-party [maintainer source](https://github.com/Anionex/dsh-vision-toolkit), [pinned npm registry metadata](https://registry.npmjs.org/@anionex/dsh-vision-toolkit/0.1.46). Do not follow a moving `latest` tag during execution.
- Candidate tarball `https://registry.npmjs.org/@anionex/dsh-vision-toolkit/-/dsh-vision-toolkit-0.1.46.tgz`, verified integrity `sha512-81V9AI0u77D3B9kVrdHvN7x7iOYwgLO/hsdDZNPsZUTELw0eZI2b68zHR5ltQgR9SqTt4umQzuMUgvx1K1sxjQ==`. Recheck exact metadata/integrity before install. Root has no install/postinstall/prepare scripts; all dependency lifecycle scripts remain disabled.
- Node range accepts the existing runtime, and declared DeepSeek peers explicitly include **0.2.0-rc.2**. Direct dependencies are pinned by the publisher: saxes 6.0.0, tar 7.5.22, undici 8.10.0, zod 4.4.3. Declared compatibility is not profile/vision runtime qualification.

## Why these npm flags

Existing profile package.json has one dependency (the vision plugin) and a retained three-bundle list. No npm lockfile or profile .npmrc exists as of inspection. npm will create `package-lock.json`; it does not use the pnpm lock as its dependency lock. [npm install](https://docs.npmjs.com/cli/v11/commands/npm-install/), [npm lockfile](https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json/).

`--legacy-peer-deps` deliberately prevents npm from building an additional DeepSeek/React peer tree inside the profile, preserving the previous no-auto-peer-install policy. This **ignores peer enforcement**, rather than proving peer compatibility; do not describe it as the general npm default or a fix for all peer problems. Check the manifest ranges separately against the installation-owned core; qualify actual imports/boot later. `--omit=peer` is not equivalent because npm still resolves peer constraints with that option. [npm peer configuration](https://docs.npmjs.com/cli/v11/using-npm/config/#legacy-peer-deps); the installed npm 11.17.0 definition confirms this behavior.

## Proposed commands, files and persistence

Before mutation: recheck recognized live DeepSeek processes, exact CLI/Node/npm/plugin identities, free disk space, existing profile and full protected-home metadata/content hashes, global tool identities and all container IDs/status/start times/restart counts/ports/networks. Do not stop a live session. Require `node_modules` is a real directory, existing pnpm lock a regular non-symlink file, package-lock/shrinkwrap/yarn lock absent and no added profile dependency; stop for review if these assumptions changed.

From `/home/developer/workspace/mcp-stack`, after approval:

```sh
set -euo pipefail
umask 077
MCP_STACK_DEEPSEEK_NPM_BACKUP="$(mktemp -d backups/deepseek-vision-npm-20261002.XXXXXX)"
tar -C /home/developer -czf "$MCP_STACK_DEEPSEEK_NPM_BACKUP/existing-home.tar.gz" .dsh
tar -tzf "$MCP_STACK_DEEPSEEK_NPM_BACKUP/existing-home.tar.gz" >/dev/null
sha256sum "$MCP_STACK_DEEPSEEK_NPM_BACKUP/existing-home.tar.gz" \
  > "$MCP_STACK_DEEPSEEK_NPM_BACKUP/archives.sha256"
install -m 0600 /home/developer/.dsh/profiles/web/package.json \
  "$MCP_STACK_DEEPSEEK_NPM_BACKUP/profile-package.before.json"
# Capture private protected manifests before these moves; never display credentials.
mv -T -- /home/developer/.dsh/profiles/web/node_modules \
  "$MCP_STACK_DEEPSEEK_NPM_BACKUP/original-node_modules"
mv -T -- /home/developer/.dsh/profiles/web/pnpm-lock.yaml \
  "$MCP_STACK_DEEPSEEK_NPM_BACKUP/original-pnpm-lock.yaml"
NODE_DISABLE_COMPILE_CACHE=1 \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/bin/node \
  /home/developer/.local/share/fnm/node-versions/v24.19.0/installation/lib/node_modules/npm/bin/npm-cli.js \
  install @anionex/dsh-vision-toolkit@0.1.46 \
  --prefix /home/developer/.dsh/profiles/web \
  --global=false --save-prod --save-exact --package-lock=true \
  --install-strategy=hoisted --legacy-peer-deps \
  --registry=https://registry.npmjs.org \
  --cache=/home/developer/workspace/mcp-stack/infra/harnesses/deepseek/state/npm-cache \
  --ignore-scripts --no-audit --no-fund --update-notifier=false
```

These are narrowly scoped, recoverable **moves**, not deletion of the old dependency tree or old lock. Verify a unique restricted destination and same filesystem before moving; never overwrite a previous backup. Earlier CLI/failed-attempt backups remain untouched. Runtime backups/cache are ignored and restricted, never committed.

Expected changes: existing profile package.json gains exact `0.1.46` pin with its bundle list/other fields unchanged; npm `package-lock.json` and replacement `node_modules` are created; original pnpm lock/dependencies move to the private backup. Retain existing `pnpm-workspace.yaml` unchanged (npm ignores it; upstream profile initialization expects it). No new .npmrc, global config, credentials or settings. This is a narrow explicit exception for the user's pre-existing home, not permission to put new mcp-stack tool configs outside `infra/`. Cache/logs stay under `infra/harnesses/deepseek/state/npm-cache`, parent 0700. No ports, services, database, harness registration or PKM changes.

## Verification and limits

Verify installed plugin and direct dependency versions; exact dependency pin, retained bundle list, npm lock integrity matching the pinned tarball, matching resolved tree and no automatically installed DeepSeek peer packages. Record resolved versions/integrities privately. Compare all non-approved home hashes/file inventory/modes/symlinks, including settings, credentials, sessions, profile YAML and workspace file; compare global identities and retained containers. Do not boot/import plugin code merely to inspect metadata. Disabled scripts or failed installation must be reported; do not retry with scripts enabled or another manager.

Installed `dsh plugin ...` explicitly delegates to pnpm; **do not use it**, even after npm succeeds. The update bypasses that wrapper, preserving the existing `dsh.profile.bundles` rather than depending on its reconciliation behavior. No patch to upstream source or assertion that the UI's package manager is npm-native. Future launcher/functional qualification must respect npm-only selection and avoid plugin-management actions that invoke pnpm. No profile startup, Python bootstrap, model download, authentication, remote provider/paid call or MCP test in this step. Do not uninstall existing pnpm/Corepack or clean its caches implicitly.

## Recovery and after-report

On success report exact version/paths, integrity and protected-state results, original dependency/lock recovery location and limits, then stop before startup/integration. Record completion in setup status/runbook.

On failure after moves, retain everything and report the profile as potentially incomplete. A **separately approved** rollback moves only the replacement `node_modules` and new `package-lock.json` (if present) into unique restricted recovery paths, restores `original-node_modules` and `original-pnpm-lock.yaml` to their validated exact profile paths, and restores only the before package.json if modified. Recheck for intervening user changes first. No whole-home overwrite, uninstall or deletion; no credentials/sessions restoration needed unless separately investigated. Archive content contains private credentials/sessions: never publish. No cleanup is approved.
