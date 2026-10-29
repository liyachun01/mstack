# orb-devbox development tool audit and mise migration plan

Initial audit recorded 2026-10-09, Asia/Shanghai. That audit was report-only.
**Later authorized cleanup removed Linux Supabase CLI and Deno; standalone Bun
is retained for gstack, with migration to mise still proposed.** The iOS compression tests
were also confirmed to have moved to the macOS media lab. The
[cleanup and correction record](ORB-DEVBOX-CLEANUP-2026-10-09.md) supersedes the
original installation inventory and relevant proposals below.
The companion [Inbox Zero plan](INBOX-ZERO-SETUP-PLAN.md) follows this migration.

## Recommendation

Make mise the owner of user-selected development runtimes and CLI versions.
Install and verify replacements first, switch their consumers, then remove the
previous installations by exact target. A destructive reset is unnecessary.

Keep the operating system's Python and runtime libraries, OrbStack guest tools,
and the runtimes bundled inside Codex/Cursor. They are application or OS
dependencies. Removing them would break the machine or the tools doing this work.
Move optional native compilation to a qualified build container where practical;
record any remaining OS dependency explicitly rather than claiming mise replaced it.

Linux mise use is reopened by the user's new request, but this turn is expressly
for a report and plan. The existing repository's macOS-only mise instructions
must be updated as part of an approved migration; they have not been silently
changed. No macOS tool removal is proposed.

## Machine and coverage

- Codex host ID: `remote-ssh-discovered:orb-devbox`; OrbStack machine name and
  Linux hostname: `devbox`. OrbStack lists only this one machine.
- Ubuntu 26.04 LTS, ARM64; user `developer`, UID 501.
- OrbStack reports 55.0 GB for this machine; this is not a reclaimable-space estimate.
- Inspected installed apt metadata, executable paths and symlinks, known runtime
  stores, shell activation lines, user tool metadata, process executable paths,
  listeners, workspace Git state, and macOS Docker container status.
- Commands did not run installers, activate mise, fetch Git history, run builds,
  call authenticated mailbox/cloud APIs, or print secret files, process environments or full
  process arguments. apt commands below were simulations.
- `/root` was inaccessible to this unprivileged inspection. Arbitrary root-owned
  manual installations and every embedded executable in every cache have not
  been exhaustively audited. The installed-package inventory covers system apt
  packages; the manual-file inventory focuses on the developer account.

## What is installed

576 apt packages are installed, 281 marked manual. A manual mark alone does not
mean a package is safe to remove: many are part of the Ubuntu base.

| Component | Observed version and owner | Proposed handling |
| --- | --- | --- |
| mise | 2026.9.6, standalone `~/.local/bin/mise` | Reuse initially; no upgrade required for this migration. |
| Active Node | 24.19.0 under fnm 1.39.0 | Preserve this exact runtime for DeepSeek until a replacement is qualified. |
| Additional Node | 24.21.0 under mise | Already installed; matches {{mstack:CLIENT_REPO_CAMEL}}'s existing mise lockfile. |
| npm / Corepack | 11.17.0 / 0.35.0 in fnm's Node prefix | Account for both when moving global Node CLIs. |
| pnpm | Active Corepack cache 10.33.0; mise also has 10.30.3 | Pin 10.33.0 where `packageManager` requests it. Do not substitute 10.30.3. |
| Git / Git LFS | apt 2.54.0 / 3.7.1 | Qualify mise-managed Git and LFS, then remove their apt packages. |
| GitHub CLI | apt 2.97.0 | Qualify the same version via mise; preserve its authentication state. |
| Python | Ubuntu 3.14.4; uv-managed CPython 3.13.15 | Keep OS Python; declare development Python through mise after consumer qualification. |
| uv / uvx | Standalone uv 0.12.3 | mise can own uv; uv remains useful for project environments and dependency installation. |
| Graphify | uv tool `graphifyy` 0.9.39, using OS Python 3.14.4 | Preserve tool/data; move invocation ownership after an offline smoke check. This differs from historical container Graphify versions. |
| Headroom | uv tool `headroom-ai` 0.34.0, Python 3.13.15 | Preserve active MCP consumers and data; migrate before retiring uv's Python. |
| Bun / Deno | Standalone 1.3.14 / 2.9.5 | Retain exact versions under mise if needed, then retire standalone binaries/hooks. |
| Swift | apt Swift 6.1.3 | Optional Linux toolchain; about 2.20 GiB for `swiftlang` plus about 82 MiB for `libswiftlang`. Retire if Linux Swift checks are no longer needed, or qualify mise Swift first. Native iOS builds still require macOS Xcode. |
| Native compilation | build-essential; GCC/G++ 15.2.0; Make 4.4.1; pkgconf; development headers | Move optional build use to a pinned container or qualify a complete managed toolchain. Review apt dependencies before removal. |
| Existing mise CLIs | Wrangler 4.130.0, Supabase 2.117.0, agent-browser 0.37.1 | Preserve; scope to the projects that need them. Supabase CLI installation does not authorize any Supabase lifecycle action. |
| Other apt utilities | direnv 2.37.1, fd 10.3.0, fzf 0.67.0, jq 1.8.1, ripgrep 15.1.0, ShellCheck 0.11.0, shfmt 3.12.0, tmux 3.6a | Candidates for exact-version mise ownership. Remove direnv only after its hooks/environment behavior are replaced. |
| PostgreSQL client | apt client 18.6 | Keep until a managed or container-based client is qualified. Do not remove or modify any database server/data. |
| Custom standalone tools | `/usr/local/bin/workbench`; `~/.local/bin/raft-computer`, associated WASM file, Docker forwarding wrapper | Provenance/consumer qualification pending. Record and preserve them; do not assume every custom binary is disposable. |
| Codex / Cursor | Codex standalone 0.159.2; Cursor server bundles its own Node | Preserve application-owned installations, sessions, extensions and bundled runtimes. |

No installed apt Node/npm was found. No installed nvm, asdf, Volta, Nix, Devbox
package manager, Rust/Cargo, Go, Java, Ruby or .NET runtime was found in the
inspected locations/PATH. The OrbStack machine being called `devbox` does not
mean the Devbox package manager is installed. Empty mise Docker install
directories do not establish that duplicate Docker clients are installed.

### Node globals that would be lost with fnm

The fnm Node prefix also contains:

| Package | Version |
| --- | --- |
| `@deepseek-ai/dsh` | 0.2.0-rc.2 |
| `@volcengine/cli` | 1.1.8 |
| `@volcengine/vefaas-cli` | 0.3.1 |
| `ve-tos-cli` | 1.0.2 |

These should become explicit, pinned project CLI declarations if retained.
Installing them through a mise npm backend changes install ownership; it does
not eliminate their Node dependency or authorize provider login/deployment.
Existing npm metadata also shows cached Wrangler 4.135.0 and Prettier 3.9.6 from
npx. Cache contents are not another authoritative project tool declaration.

### PATH and consumers

`~/.zshrc` activates fnm twice, at lines 12 and 14. Its Bun and Deno PATH entries
and uv completion setup are separate. The inspected user mise config has no
`[tools]` selections, and the current zsh file has no mise activation block.
Installed mise tools therefore do not control the current session's Node PATH.

The following dependencies prevent immediate deletion:

- DeepSeek Web PID 414648, listening on 3080, and the transport forwarder PID
  402899, listening on 58081, execute fnm Node 24.19.0.
- `integrations/agents/deepseek_launch.py` hardcodes the fnm Node installation;
  the DeepSeek runbooks also reference that prefix.
- Serena TypeScript servers and Pyright use fnm Node. Several active Headroom
  and other Python/MCP processes use uv's CPython 3.13.15.
- Graphify's existing virtual environment references `/usr/bin` Python.
- Cursor's server Node is private to Cursor and must stay there.
- `/home/developer/devmachine` contains the older provisioning source for apt,
  fnm, Bun, Deno, uv and other optional components. Rerunning those profiles would
  reintroduce the old setup. Preserve the source and reconcile/deprecate those
  install paths during migration; do not run the provisioner now.

Process IDs are a point-in-time observation, not a durable shutdown target.
Resolve identities again before any approved restart or removal.

### Disk observations

Allocated usage observed with `du -sk`, rounded to GiB:

| Location | Observed usage | Interpretation |
| --- | ---: | --- |
| `~/.local/share/fnm` | 0.91 | Node, fnm and global CLIs; retire only after cutover. |
| `~/.local/share/mise` | 0.70 | Keep; includes already-installed replacements. |
| `~/.local/share/uv/tools` | 5.83 | Tool environments, not just disposable cache. |
| `~/.local/share/uv/python` | 0.09 | Active Python dependency. |
| `~/.cache/uv` | 20.01 | Large candidate for later selective cleanup; some active environments/scripts are served from here. |
| `~/.npm` | 2.89 | Cache and npx environments; review consumers before cleanup. |
| `~/.local/share/pnpm` | 4.00 | Dependency store; preserve through migration. |
| `~/.cache/pnpm` | 0.61 | Later cleanup candidate. |
| `~/.bun` | 1.03 | Binary plus package cache, not just Bun itself. |
| `~/.deno` | 0.08 | Standalone runtime. |

Do not sum these into promised savings. Hardlinks, filesystem accounting and
replacement/backup space affect actual reclaimed space. A plan to remove old
tool owners is separate from deleting dependency caches and source repositories.

## The four workspace directories

All three {{mstack:CLIENT_REPO_CAMEL}} directories are linked Git worktrees of
`/home/developer/workspace/{{mstack:CLIENT_REPO}}/.git`; the iOS directory is an independent
shallow clone. None is a separate OrbStack machine.

| Directory | Evidence | Recommendation |
| --- | --- | --- |
| `{{mstack:CLIENT_BRAND_LOWER}}-ios-memory-speed` | Branch `codex/memory-client-compression`; HEAD `0fd8248`; modified `MemoryImportService.swift` and untracked `MemoryUploadCompression.swift`; about 85 MiB | **Preserve the uncommitted app integration patch.** Testing has moved to `/Users/{{mstack:MAC_USER}}/Developer/{{mstack:CLIENT_BRAND_LOWER}}-ios-media-lab`; its encoder matches the Linux candidate. See the [follow-up evidence](ORB-DEVBOX-CLEANUP-2026-10-09.md) before retiring the clone. |
| `{{mstack:CLIENT_REPO}}-growth` | Clean tracked/untracked Git status; HEAD `d73065ee4`, last commit September 20; 373 commits behind the local `clientapp-dev-sb` plus two distinct commit IDs, both reported as equivalent patches by `git cherry`; about 142 MiB | **Retire from everyday use.** The planning patches are already represented in the current base. Preserve the branch/reference and any local evidence before archiving the checkout. |
| `{{mstack:CLIENT_REPO}}-growth-implementation` | Clean tracked/untracked Git status; HEAD `7fb4a2d36`, last commit October 1; ancestor of local `clientapp-dev-sb`, 364 commits behind; about 3.34 GiB | **Retire from everyday use.** Its committed work is already in the base. Preserve ignored operator env/evidence before removing the checkout. About 3.05 GiB is root `node_modules`, but this is not a guaranteed physical-space saving. |
| `{{mstack:CLIENT_REPO}}-memory-speed` | Clean tracked/untracked Git status; HEAD `4352d184d`, October 9; nine commits ahead of local `clientapp-dev-sb`, five ahead of cached `origin/clientapp-dev-sb`; about 5.35 GiB | **Keep as the current backend work area.** Contains later avatar/film-stock fixes and handoff updates. Its handoff explicitly describes some changes as Local-only, unpushed and undeployed. Consolidation belongs with the owning work chat. |

These comparisons use local/cached Git refs. No remote fetch or claim of current
server branch state was made. Patch equivalence establishes that the planning
changes have been applied in the base's history, not that every later file is
identical. The implementation worktree has ignored `.env`/test evidence and
generated dependencies; an empty `supabase/snippets/` directory has no source
files. “Git clean” does not authorize discarding ignored state.

No process cwd was observed under these four directories. Recent Codex chats
are associated with the primary {{mstack:CLIENT_REPO_CAMEL}} path, so cwd alone cannot prove that
another chat has no dependency on an auxiliary worktree. Before retirement,
confirm the owning chat is idle, preserve its handoff and local evidence, then
use Git's worktree operations rather than raw directory deletion. Keep branches.

For future work: use the primary {{mstack:CLIENT_REPO_CAMEL}} checkout for general development;
retain the memory worktree until its local work is reviewed and integrated.
Avoid starting new work in either old growth checkout.

## Migration plan

### 1. Prepare a recoverable manifest

First implementation checkpoint is file preparation and backup, not removal.
Capture exact package versions, apt manual marks/sources, binary hashes and
symlinks, shell activation blocks, tool receipts, project lockfiles and process
consumers. Keep private backups under ignored, mode-0700
`infra/maintenance/orb-devbox-mise/`; credentials never go in public reports.
Use an exact allowlist for every later removal. Snapshot/recovery capacity must
be checked before making destructive changes; no machine snapshot was created
by this audit.

Keep project declarations under this repository's `infra/`. Proposed locations:

- `infra/toolchains/orb-devbox/mise.toml`: common Ubuntu CLI baseline and its
  lockfile, without a global Node/Python version selection.
- `infra/mise.toml`: authoritative mcp-stack project selections, updated with
  explicit Linux/macOS constraints while preserving macOS intent.
- `infra/harnesses/deepseek/mise.toml`: exact DeepSeek Node and CLI selections.
- Reusable path/consumer checks under `integrations/`.

{{mstack:CLIENT_REPO_CAMEL}} already has its own `mise.toml` and lockfile; its declaration lives in
that separate repository. Pin its floating `lts`/`latest` requests to the observed
locked versions when authorized, and declare pnpm 10.33.0 explicitly. The iOS
checkout already pins Tuist 4.202.6. No cross-repository file edits happened here.

### 2. Qualify mise replacements beside the old tools

Start with installed mise 2026.9.6. Preserve runtime versions rather than
combining migration with upgrades. Use Node 24.19.0 for the existing DeepSeek
consumer and 24.21.0 for {{mstack:CLIENT_REPO_CAMEL}}. Pin npm/Corepack as needed to preserve the
current behavior; declare pnpm 10.33.0, uv 0.12.3, Bun 1.3.14 and Deno 2.9.5
only in scopes that use them.

Git needs an explicit backend: the installed registry has no `git` shorthand.
Candidate declaration is `"conda:git" = { version = "2.54.0", channel =
"conda-forge" }`. Read-only channel metadata confirms Linux ARM64 builds exist.
The backend includes dependency resolution without installing a separate conda
manager. This remains an **unexecuted candidate**, requiring package/dependency
locking and checks for credential helpers, SSH, worktrees, submodules and LFS
before apt Git is removed. [mise conda backend](https://mise.jdx.dev/dev-tools/backends/conda.html),
[ARM64 Git package metadata](https://api.anaconda.org/package/conda-forge/git).

Use direct release backends for ordinary CLIs where qualified. Python tool
environments can remain uv-managed with mise owning the pinned uv/Python and
entrypoint tasks; moving all their dependencies into the mise binary itself is
not necessary. Recreate virtual environments at their final paths rather than
moving environments with absolute interpreter paths.

mise's `use`, `exec` and `run` can install missing tools. Preparation and
verification must disable automatic installation; run installs only at the
explicit install checkpoint. Inspect backend behavior in the installed version,
not just newer online documentation. [mise tool behavior](https://mise.jdx.dev/dev-tools/).

### 3. Switch shell, editor and service consumers

Prepare one reviewed zsh activation block and remove the two fnm hooks and
standalone Bun/Deno PATH additions only during cutover. No repeated additions
to global tool config. A common CLI default can point to the repo-owned baseline
through an explicit launch environment; project runtime selection stays scoped.

Update the DeepSeek launcher, forwarder launch procedure and runbooks to resolve
the approved mise runtime. Preserve `~/.dsh`, Codex login/provider configuration,
Graphify/Headroom data, cloud CLI credentials and all editor state. Reopen or
restart only the identified consumers in a quiet window. Verify both fresh
interactive shells and noninteractive editor/MCP launches; the current shell's
inherited fnm PATH is not proof of the new setup.

### 4. Remove old owners by exact target

Only after replacement acceptance, remove fnm's single Node prefix/manager and
the standalone binaries that were actually replaced. Retain private rollback
copies until the user accepts the migration. Do not remove all of `~/.local/bin`,
`~/.cache`, `~/.npm`, `~/.local/share/uv`, `~/.codex` or `~/.cursor-server`.

apt's simulated ordinary-CLI removal selected exactly 15 packages:

```text
git git-man git-lfs gh direnv fd-find fzf jq ripgrep shellcheck shfmt tmux
postgresql-client postgresql-client-18 postgresql-client-common
```

This is an inventory candidate, not a command to run now. Every replacement or
retirement decision must pass before its corresponding package is selected.
Retire the Git PPA/GitHub apt source entries only after confirming that no
remaining package depends on them; preserve OS update sources.

The native-build removal simulation has a material complication: removing
`build-essential make swiftlang pkg-config pkgconf pkgconf-bin zlib1g-dev`
would **install** `make-guile`, `guile-3.0-libs` and `libgc1` because remaining
packages require a Make provider. That proposal must be revised; it does not
achieve a clean removal. Resolve the complete dependency closure and build
requirements first, then simulate the exact final list. Do not run broad
`autoremove`, recursive cache deletion, or Docker prune.

### 5. Retire old worktrees and inspect caches separately

Archive the two growth worktrees after preserving their branches, private env
files and useful evidence. Keep both memory work directories. Use exact Git
worktree targets, without force-removing dirty content. This is independent of
the toolchain migration.

After active uv/npm/pnpm/Bun consumers have moved, identify unused cache entries
and present a separate cleanup manifest and rollback impact. Re-inventory first;
cache residency and package-store links can change during another chat's work.

### 6. Verify and record the result

Acceptance requires:

- Selected runtime/CLI executable paths resolve to the intended mise installs
  in each project and in fresh editor launches; no accidental fallback to fnm.
- Git worktree/status, LFS and credential-helper behavior work with preserved
  repo state; checks need not contact remote providers.
- DeepSeek/forwarder and existing MCP tools start using their approved runtimes
  and preserved settings; no model calls are needed for runtime smoke checks.
- OS Python/apt/networking/SSH and OrbStack bridges still work.
- Protected service identities, volumes and credentials are unchanged except
  explicitly approved consumer restarts; no global harness registration occurs.
- Old installations are removed only from the allowlist, backups are verified,
  and package sources/provisioning instructions no longer recreate retired tools.

Rollback before removal is restoring the previous shell/launcher files and
reopening the affected consumers. After removal, restoration also needs the
exact old binaries/prefixes or previously cached packages. An apt version list
alone does not guarantee an old PPA package remains downloadable; preserve the
artifacts or a tested machine recovery path before deleting them.

## Runtime boundaries observed today

This inventory predates the later authorized Inbox Zero foundation. Shared
PG18.6 has since been recovered from its retained volume and the three Inbox
Zero services are running; see the
[completion report](INBOX-ZERO-SETUP-REPORT-2026-10-09.md). Other historical apps
remain absent, and the original 15 container IDs were preserved.

macOS Docker currently shows the gateway, OpenCodex, 12 running {{mstack:CLIENT_REPO_CAMEL}} Supabase
containers, and one stopped ai-memory container. Historical mcp-stack PG,
Windmill and graph service definitions still exist in the repository; their
containers were absent from this discovery. This report does not restore them.

{{mstack:CLIENT_REPO_CAMEL}}'s ports 54321/54322/54323/54324/54327 remain occupied and protected.
Gateway ports 58080/58084, DeepSeek 3080/58081 and OpenCodex 10100 are also
occupied. Use macOS OrbStack Docker through `macctl`; install no Docker daemon
or duplicate client in Ubuntu. Preserve all infra definitions and durable data.

After the devbox migration is accepted, proceed to the separately prepared
[Inbox Zero setup plan](INBOX-ZERO-SETUP-PLAN.md). Each concrete install/removal
checkpoint follows the loaded
[setup guard](../.agents/skills/mcp-stack-setup-guard/SKILL.md); this report is
not approval to execute those checkpoints.
