# Ubuntu development toolchain migration to mise — 2026-10-15

> **2026-10-18 correction:** Git and Git LFS now use Ubuntu packages under
> `/usr/bin`; they are no longer selected by mise. The repository rename to
> `mstack` broke the old command links and shell bootstrap; those paths are repaired.
> See [the editor Git repair](../infra/maintenance/git-editor/README.md).
> The migration details below remain historical.


Status: **Linux mise migration finished, including the authorized helper drain.**
Headroom, Serena and language servers now run on mise. Obsolete fnm and uv
Python paths are absent from home; exact rollback copies remain private.

The user authorized finishing the earlier mise migration. This work targets the
OrbStack Ubuntu development machine, reuses installed mise **2026.9.6**, and
preserves existing versions. Native macOS tools, applications and Docker
services are not migration targets. OS Python and PostgreSQL client remain OS
dependencies.

## Configuration and source ownership

Tool selections live in repository configuration, rather than user-global
`[tools]` declarations. Separate profiles prevent an incidental shell-wide Node
or Python selection from overriding another project's runtime.

| File | Exact selection and purpose |
| --- | --- |
| `infra/toolchains/orb-devbox/mise.toml` | Common Linux CLI baseline: Git 2.54.0, Git LFS 3.7.1, GitHub CLI 2.97.0, uv 0.12.3, Bun 1.3.14, direnv 2.37.1, fd 10.3.0, fzf 0.67.0, jq 1.8.1, ripgrep 15.1.0, ShellCheck 0.11.0, shfmt 3.12.0, tmux 3.6a. No Node/Python selection. |
| `infra/toolchains/node-cli/mise.toml` | Explicit legacy CLI runtime: Node 24.19.0, pnpm 10.33.0, `@volcengine/cli` 1.1.8, `@volcengine/vefaas-cli` 0.3.1, `ve-tos-cli` 1.0.2. |
| `infra/toolchains/python/mise.toml` | Development/MCP Python 3.13.15 and uv 0.12.3. `python.compile = false` rejects a missing precompiled distribution instead of compiling implicitly. |
| `infra/harnesses/deepseek/mise.toml` | Node 24.19.0 and official `@deepseek-ai/dsh` 0.2.0-rc.2. |
| `infra/mise.toml` | mcp-stack project Node 24.19.0 and pnpm 10.33.0. |
| Profile-local `mise.lock` files | Resolved artifact URLs/checksums where the selected backend supports them; inspect the npm exception below. |
| `integrations/toolchains/entrypoint.py` | Repo-owned compatibility command implementation. Selects installed exact tools, preserves the caller's working directory, and refuses missing installations. |
| `integrations/toolchains/install.py` | Explicit profile installation, with reviewed per-invocation scope and private logs. This is an installation command, not a routine health check. |
| `integrations/toolchains/inventory.py` | Bounded runtime/process/config inventory, with private report output and no discovered-program execution. |
| `integrations/toolchains/snapshot.py` | Private rollback copies, legacy-runtime archive, apt inventory and Docker identity baseline. |
| `integrations/toolchains/verify.py` | Installed binary/version checks and an offline scratch Git/LFS/worktree exercise. No provider login or calls. |
| `integrations/toolchains/cutover.py` | Verified shell/25-command link cutover, exact private backups and guarded rollback. |
| `integrations/toolchains/retire.py` | Exact 12-package apt cleanup and unused standalone Bun retirement, requiring verified rollback files. Not a routine startup command. |
| `integrations/agents/deepseek_launch.py` | Consumer launcher updated to resolve installed pinned mise tools, without downloading or starting unrelated components. |

`~/.zshrc` sources repo-owned `infra/toolchains/orb-devbox/activate.zsh`, replacing
only the old fnm/Bun activation blocks. Twenty-five `~/.local/bin` command links
point to the repo-owned entrypoint. Root `.mise.toml` is a discovery symlink to
`infra/mise.toml`, explicitly trusted along with the five reviewed configs.
The lexical symlink needs its own trust entry; trusting its target alone failed
the first fresh-shell check and was corrected before cleanup. Such links are
launch plumbing; tool/service configuration remains in `infra/`. Global mise
`config.toml`, Bash startup and `.profile` remain byte-identical to the snapshot.

Existing {{mstack:CLIENT_REPO_CAMEL}} project selection **Node 24.21.0** must continue to win inside
its own worktrees. Project selections override compatibility defaults. Keep
native Codex login/provider settings and global MCP registrations unchanged.

## Installed and active selections

The common, Node CLI, Python, DeepSeek and project profiles are installed.
Fresh shells verified root Node 24.19.0/npm 11.17.0/Corepack 0.35.0/pnpm 10.33.0;
{{mstack:CLIENT_REPO_CAMEL}} still resolves its existing Node 24.21.0. Actual Node process paths,
working directories and literal arguments were checked. All 25 compatibility
commands resolve inside mise installations. A real terminal verified Bun 1.3.14
loading gstack 1.61.0.0's package without starting its browser or agents.

The user then explicitly authorized temporary helper downtime to finish the
migration. Sixteen verified MCP helper trees (44 processes) stopped cleanly;
the main Codex daemon remained running. Existing bindings reconnected through
`config/mcpServer/reload`: Headroom and Serena are connected in all 10 loaded
sessions. No global configuration/authentication or model turn changed.
OS `python3` remains Ubuntu's interpreter. The uv/uvx invocation profile uses
mise Python 3.13.15, respecting explicit `UV_PYTHON`/project selection.

Ordinary command resolution must never run an installer. Compatibility launches
set missing-tool auto-installation off and reject absent exact versions. A tool
update requires an explicit declaration/lock change and its own installation;
it does not occur because a command happened to be absent.

Standalone email-mcp's `infra/email-mcp/runtime.json` now points to exact mise
Node 24.19.0. Its source, dependencies and security patches are preserved; all
three credential-free synthetic tests pass through the updated launcher.
Mailboxes stay unconnected, sending disabled and harness registration absent.

The DeepSeek preparation launcher resolves pinned mise Node and dsh, without
starting Web/forwarder or calling a model. Its npm/Aube layout uses
`node_modules`, rather than the assumed `lib/node_modules`; the launcher now
accepts either unambiguous contained layout. Native composition uses the
canonical package path to resolve Aube's symlinked dependencies. The new tree's
pinned MCP client hash, composition/schema and two offline SDK regressions pass.
All 430 existing `~/.dsh` links now point to the byte-identical project copy at
`infra/harnesses/deepseek/runtime/profile-packages/dsh`, replacing the fnm
location. This preserves 25,906 files, 452,257,315 bytes, 11 internal symlinks,
all 3,711 profile real files and the 96 pre-existing broken links. Those broken
links were not introduced or repaired by relocation. Substituting the fresh
mise dependency graph would change 26 package versions, so the preserved
project dependencies remain separate from mise's top-level harness install.
Both trees pass native offline composition with fnm absent. Retained-profile
startup and provider/tool execution were not activated or tested.

## Integrity and backend limitations

Git uses explicit `conda:git` with conda-forge, because installed mise has no
plain `git` registry alias. Its isolated prefix includes supporting libraries
and Perl; it is not a single static binary. The mise backend manages those
dependencies without installing a second conda package manager. The common
binary tools use pinned Aqua/core backends. See the exact artifact research in
[backend notes](../integrations/toolchains/backend-notes.md).

The current npm backend/profile combination does **not** provide the same
resolved artifact-URL coverage in mise.lock as the binary backends. A lockfile
containing npm version entries must not be described as a complete immutable
dependency lock. A blanket `mise install --locked` may reject those entries
because their platform URLs are missing. Use the explicit reviewed installer
behavior and record the resulting package/dependency evidence; do not disable
integrity checking for the unrelated binary profiles to work around this.

The Node CLI profile explicitly selects npm for installation and disables
lifecycle scripts. Top-level versions, npm integrity metadata and actual
installed package versions still require checks. A passing package-version
check for DeepSeek or a cloud CLI proves installed code identity, not valid
credentials, a working provider session, cloud access or tool execution.
Do not launch profiles or paid model probes merely to check a package version.

Node 24.19.0 officially bundles npm 11.17.0, matching the previous runtime.
Corepack 0.35.0 also needs preservation/verification; do not silently substitute
the npm/Corepack versions bundled in the separately installed Node 24.21.0.

## Scope isolation

Lock/install operations use their exact profile directory, an ancestor ceiling
at that directory's **parent**, and empty repo-owned global/system config
sentinels. Trust is supplied for the reviewed file for that invocation; this
does not permanently trust the entire `infra/` tree.

`MISE_CONFIG_FILE` is a legacy alias of `MISE_GLOBAL_CONFIG_FILE`, not a selector
for one project file. Pointing it at a profile causes that file to be classified
as global and can make a plain `mise lock` update an ancestor instead. The
profile installer deliberately uses isolated scope instead. Inspect active
config paths before any additional lock or install operation.

## Helper drain and completed retirement

Stopping alone was insufficient: existing venvs and profile links also needed
migration. Changed only interpreter links and `pyvenv.cfg` home fields in
146 existing Python 3.13.15 environments, preserving 21,931 package metadata/
source/file-hash identity records. Every environment executed offline and
confirmed its existing venv prefix, mise base interpreter, version and native
stdlib imports. No package reinstall, dependency update or cache deletion ran.
Graphify's system-Python environment was untouched.

After reconnect, live procfs shows no fnm executable, old uv Python or deleted
standalone uv process. Headroom/Serena and their language servers use mise.
The original `~/.local/share/fnm`, old uv Python version directory and alias
were moved to private rollback quarantine after exact archive comparison:
35,040 fnm entries and 5,006 interpreter entries matched, with no added,
changed or missing files. Original home runtime paths are absent.

**Keep uv's tools and cache directories.** They contain the applications and
dependencies now using mise Python; they are not redundant interpreter stores.
Mise owns the uv executable and Python runtime; uv manages package environments.

Standalone uv/uvx were replaced by command links after backup. Unused
`~/.bun/bin/bun`, `bunx` and `~/.bun/_bun` were removed after archive checksum,
file/link identity, fresh-terminal and gstack checks. Bun caches remain.
No app environment was rebuilt.

After replacement checks, exactly these duplicate apt packages were removed:
`git`, `git-man`, `git-lfs`, `gh`, `direnv`, `fd-find`, `fzf`, `jq`, `ripgrep`,
`shellcheck`, `shfmt`, `tmux`. Simulation selected exactly those 12, with no
extra removals/installations. Exact cached `.deb` files were copied privately
and checksum-verified first; some old versions are no longer in repository
metadata. No autoremove, purge or cache cleanup ran. In particular retain:

- `/usr/bin/python3` and OS Python packages used by Ubuntu or launch plumbing.
- PostgreSQL client 18.6 (`psql`, `pg_dump`, `pg_restore`, client-common).
- Native macOS Docker/Compose and all existing container data, networks and
  credentials; no Docker lifecycle is needed for this migration.
- Existing build dependencies and unrelated project tools unless explicitly
  assessed and selected for removal.

`conda:libpq` cannot replace the PostgreSQL CLI: its packaging keeps `pg_config`
but strips the other executables. Selecting full `conda:postgresql` instead would
add server binaries/dependencies; this migration deliberately leaves the
existing OS client alone.

## Verification and rollback

The private backup pointer is
`infra/maintenance/orb-devbox-mise/current-path.txt`. It names a timestamped
0700 directory below that area's `.secrets/`. Do not publish its contents.
The snapshot records copied shell/global mise configuration, an archived fnm/
Bun/uv executable baseline, the archive SHA256, apt versions/manual marks and
the identities/start times of **30 existing Docker containers**.

Verification must include exact installed versions/paths, common command
resolution, caller cwd preservation, root versus {{mstack:CLIENT_REPO_CAMEL}} Node precedence,
Bun consumers, isolated Git/LFS/worktrees, configured Python/uv consumers,
DeepSeek/email-mcp launcher resolution, original OS clients and unchanged
Docker identities/start times. Keep reports private; publish only redacted
qualification results.

Rollback uses the matching timestamped baseline, not an older October 9 record:

1. Preserve any settings changed by the owner after the snapshot before
   restoring shell bootstrap or compatibility links.
2. Restore only files changed by this cutover from their exact private copies.
   Remove only newly created links recorded as migration-owned. Do not overwrite
   the rest of the owner's `.local/bin` or mise configuration.
3. If an old executable was replaced, verify the backup archive SHA256 and
   restore only its selected matching member/path. Never unpack the archive
   broadly over a live home or delete the old store preemptively.
4. Restore the former launcher runtime path from its recorded backup if that
   consumer was changed. Preserve mailbox/provider state and application data.
5. Start a fresh shell and verify the previous selection. Existing processes
   continue on their original executable; no mass stop/restart is needed.

The concrete shell/link rollback is
`python3 integrations/toolchains/cutover.py --rollback`. It checks the shell
against the recorded before/after hashes and refuses to overwrite later edits.
For full rollback, first reinstall only the 12 `.deb` paths recorded in private
`retirement/manifest.json` with `sudo dpkg -i`, retaining their existing OS
dependencies. Restore only the three recorded Bun archive members and any
required standalone uv files after verifying the archive checksum; do not
extract the entire archive over a live home. Restore email-mcp's former `node`
field from the documented retained fnm path if rolling back that consumer.
Rollback packages/archives were checksum-validated, not reinstalled as a test.

New mise installations may remain inactive during rollback. Removing them is
unnecessary to restore behavior and must not remove an installation another
project now uses. Database/server rollback is not applicable because these
services are outside the migration.

## Helper drain operations and rollback

The explicit maintenance helpers are:

- `stop_legacy_helpers.py`: identity-checked stop of Codex-owned legacy helper
  trees, never Codex itself or containers. Inspect a new plan before any stop.
- `python_rebind.py`: same-version venv interpreter/link changes, package
  identity checks, offline execution verification and exact rollback.
- `deepseek_rehome.py`: exact-byte package relocation and atomic profile links.
- `mcp_refresh.py`: status/reconnect over the existing Codex Unix WebSocket;
  never starts a daemon or model turn and never changes configuration.

For drain rollback, first re-inventory and stop only the affected MCP helper
processes; never replay saved PIDs or stop Codex. Restore the three original
home paths from quarantine recorded in private `drain/retired-stores.json`.
Run `python_rebind.py rollback --manifest <private>/drain/python-rebind/manifest.json`
and `deepseek_rehome.py rollback --state-dir <recorded-private-state-directory>`.
Then run `mcp_refresh.py reload`, check status and verify executable paths.
The helpers reject config/link drift; preserve later owner edits. Original
archives and per-link/config manifests remain private for exact rollback.

Codex's supported reload reconnects configured MCP servers without restarting
its daemon. Its Unix socket requires WebSocket HTTP Upgrade, rather than raw
JSONL; the installed 0.159.2 schema requires omitted/null reload parameters.
[Official app-server protocol](https://developers.openai.com/codex/app-server/).
These are maintenance operations, not routine startup/doctor commands.

## Final qualification

| Checkpoint | Status |
| --- | --- |
| Private snapshot/archive | SHA256 verified; 35,046 archive members |
| Exact replacement installations | 20 unique tools pass; versions preserved |
| Migration unit tests | 57 toolchain + 7 DeepSeek launcher tests pass |
| Offline Git/LFS/worktrees | 12 steps pass, including commit, pointer handling, fsck and worktree |
| Post-cleanup replacement verification | Pass; archive rechecked |
| Fresh-shell/25-command cutover | Pass; no missing-tool installation fallback |
| Root/{{mstack:CLIENT_REPO_CAMEL}} selection | Node 24.19.0/24.21.0 respectively; cwd/arguments preserved |
| Python/Bun | uv selects mise Python 3.13.15; Bun loads existing gstack package |
| email-mcp | Updated Node path; 3 synthetic checks pass, no mailbox connection |
| DeepSeek | Preparation and offline composition pass; retained profile/startup not activated |
| Docker preservation | All 30 names/IDs/start times unchanged; no additions/removals/restarts |
| OS/home/native macOS preservation | OS Python/PG and protected home configs unchanged; no macOS tool/config mutation |
| Safe cleanup | 12 duplicate apt packages + 3 standalone Bun paths removed; exact rollback retained |
| Authorized helper stop/reconnect | 16 trees / 44 processes stopped; both MCPs connected in all 10 loaded sessions |
| Existing Python environments | 146 rebound and executed offline; 21,931 package identity records preserved |
| DeepSeek profile links | 430 relocated to exact-byte project dependencies; fnm no longer required |
| Obsolete runtime stores | Original fnm/old uv Python paths absent; zero legacy runtime processes |
| Required retained data | uv application environments/cache, project dependencies and private rollback copies |

See `infra/maintenance/orb-devbox-mise/qualification-2026-10-15-drain.json` for the
latest public result; the earlier receipt records the first cutover before
authorized helper downtime. The private pointer covers replacement/consumer,
cutover, retirement, drain, reconnect and preservation receipts. The canonical
[handover](HANDOVER.md) remains the entry point for status and workflow.
