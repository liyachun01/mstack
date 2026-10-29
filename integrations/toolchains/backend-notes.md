# Ubuntu ARM64 backend qualification

Read-only research on 2026-10-15 for the authorized migration. This file is
source qualification, not a record that a tool was installed or selected.
The inspected existing binary is mise **2026.9.6 linux-arm64**. No mise upgrade,
tool installation, OS package mutation, service change or home configuration
change was performed by this research.

## Exact declarations supported by the installed registry

These exact versions each have a Linux ARM64 release asset in the named
maintainer's official GitHub release. The release API provided SHA256 digests
for every listed asset. Prefer explicit backend IDs so future registry changes
cannot change the chosen distribution.

| Declaration | Official Linux ARM64 artifact | Release |
| --- | --- | --- |
| `"aqua:git-lfs/git-lfs" = "3.7.1"` | `git-lfs-linux-arm64-v3.7.1.tar.gz` | [v3.7.1](https://github.com/git-lfs/git-lfs/releases/tag/v3.7.1) |
| `"aqua:cli/cli" = "2.97.0"` | `gh_2.97.0_linux_arm64.tar.gz` | [v2.97.0](https://github.com/cli/cli/releases/tag/v2.97.0) |
| `"aqua:astral-sh/uv" = "0.12.3"` | `uv-aarch64-unknown-linux-gnu.tar.gz` | [0.12.3](https://github.com/astral-sh/uv/releases/tag/0.12.3) |
| `bun = "1.3.14"` | `bun-linux-aarch64.zip` | [bun-v1.3.14](https://github.com/oven-sh/bun/releases/tag/bun-v1.3.14) |
| `"aqua:pnpm/pnpm" = "10.33.0"` | `pnpm-linux-arm64` | [v10.33.0](https://github.com/pnpm/pnpm/releases/tag/v10.33.0) |
| `"aqua:direnv/direnv" = "2.37.1"` | `direnv.linux-arm64` | [v2.37.1](https://github.com/direnv/direnv/releases/tag/v2.37.1) |
| `"aqua:sharkdp/fd" = "10.3.0"` | `fd-v10.3.0-aarch64-unknown-linux-gnu.tar.gz` | [v10.3.0](https://github.com/sharkdp/fd/releases/tag/v10.3.0) |
| `"aqua:junegunn/fzf" = "0.67.0"` | `fzf-0.67.0-linux_arm64.tar.gz` | [v0.67.0](https://github.com/junegunn/fzf/releases/tag/v0.67.0) |
| `"aqua:jqlang/jq" = "1.8.1"` | `jq-linux-arm64` | [jq-1.8.1](https://github.com/jqlang/jq/releases/tag/jq-1.8.1) |
| `"aqua:BurntSushi/ripgrep" = "15.1.0"` | `ripgrep-15.1.0-aarch64-unknown-linux-gnu.tar.gz` | [15.1.0](https://github.com/BurntSushi/ripgrep/releases/tag/15.1.0) |
| `"aqua:koalaman/shellcheck" = "0.11.0"` | `shellcheck-v0.11.0.linux.aarch64.tar.xz` | [v0.11.0](https://github.com/koalaman/shellcheck/releases/tag/v0.11.0) |
| `"aqua:mvdan/sh" = "3.12.0"` | `shfmt_v3.12.0_linux_arm64` | [v3.12.0](https://github.com/mvdan/sh/releases/tag/v3.12.0) |
| `"aqua:tmux/tmux-builds" = "3.6a"` | `tmux-3.6a-linux-arm64.tar.gz` | [v3.6a](https://github.com/tmux/tmux-builds/releases/tag/v3.6a) |

Resolve a linux-arm64 lockfile, inspect checksums, then use locked installation.
Installed mise's `lock --help` explicitly states that locking creates URLs and
checksums without installing; `install --locked` rejects missing platform URLs.
A tool being available in a release does not prove that its Aqua package rule
or final executable works; that still requires installation and runtime checks.
Keep apt packages until their corresponding replacement passes those checks.

## Git: native conda backend, with dependencies

There is no `git` shorthand in the installed registry. The qualified candidate is:

```toml
[tools]
"conda:git" = { version = "2.54.0", channel = "conda-forge" }
```

The [channel metadata](https://api.anaconda.org/package/conda-forge/git) lists
`linux-aarch64/git-2.54.0-pl5321h5dcfaa0_1.conda`, 14,442,457 bytes, SHA256
`9a5903559d6e66abee4abc92339a8532d8ad9b767252dd273aca96a20e010654`.
This is not a single static binary: it depends on Perl 5, libcurl, libexpat,
libgcc, libiconv, zlib, OpenSSL and PCRE2, including their transitive packages.

The [pinned backend implementation](https://github.com/jdx/mise/blob/v2026.9.6/src/backend/conda.rs)
solves an isolated prefix without a separate conda/mamba installation and stores
dependency URLs/checksums in the lockfile. Downloads enforce the supplied SHA256.
Only requested-package commands enter the outer PATH; launchers activate the
prefix for child processes. Verify Git status/worktrees, HTTPS transport, LFS,
existing credential helper behavior and hooks before retiring apt Git. Do not
rewrite authentication or repository settings as part of this migration.

## PostgreSQL client: retain OS ownership

Retain existing apt PostgreSQL client **18.6** as an explicit OS dependency.
The installed `postgres` alias points to `conda:postgresql`, which includes server
binaries and a broad dependency set. Installing it does not start a server, but
it adds substantially more than the requested client replacement.

`conda:libpq@18.6` is not a client-CLI replacement: the maintainer's
[runtime packaging script](https://github.com/conda-forge/postgresql-feedstock/blob/main/recipe/install_runtime.sh)
removes every executable except `pg_config`. The
[database packaging script](https://github.com/conda-forge/postgresql-feedstock/blob/main/recipe/install_db.sh)
keeps the full installation. Do not remove apt `psql`, `pg_dump`, `pg_restore`
or `postgresql-client-common` based on the existence of a `libpq` build.

## Python and npm runtime boundaries

Use exact project Python **3.13.15**, with `python.compile = false` to fail rather
than silently build a missing precompiled distribution. Existing uv already has
`cpython-3.13.15-linux-aarch64-gnu`; preserve its consumer environments. The
[pinned Python backend](https://github.com/jdx/mise/blob/v2026.9.6/src/plugins/core/python.rs)
uses Astral python-build-standalone artifacts and release SHA256SUMS. Preserve
Ubuntu system Python for OS consumers; do not globally select a dev Python.

The [pinned npm backend](https://github.com/jdx/mise/blob/v2026.9.6/src/backend/npm.rs)
has no per-tool `node_version` option. Node is an ordering dependency, not an
automatic added tool. Embedded aube can install packages without Node or npm;
runtime CLIs with `#!/usr/bin/env node` still need a selected Node on PATH.
Do not put Node-dependent CLIs into a Node-free baseline and assume mise supplies
their runtime. Select them with Node in a project toolchain, or provide an
explicit dedicated invocation wrapper. Keep dependency scripts disabled unless
a specific package requires and receives approval for them.

Root and DeepSeek should preserve **Node 24.19.0**. {{mstack:CLIENT_REPO_CAMEL}}'s existing project
selection **24.21.0** takes precedence in its worktrees. Existing mise 24.21.0
contains npm 11.19.0 and Corepack 0.36.0; that is not a substitute for the root's
current npm 11.17.0/Corepack 0.35.0. The official
[Node release index](https://nodejs.org/dist/index.json) confirms Node24.19.0
bundles npm11.17.0. Inspect the archive for Corepack; if necessary select
`"npm:corepack" = "0.35.0"` in the root/DeepSeek scope. Its
[official package metadata](https://registry.npmjs.org/corepack/0.35.0) provides
SHA512 integrity and Node compatibility `^22.22.2 || ^24.15.0 || >=26.0.0`.
Verify executable precedence rather than modifying the selected Node
installation in place.

## Isolate one configuration scope when locking/installing

`MISE_CONFIG_FILE` is a legacy alias for `MISE_GLOBAL_CONFIG_FILE`; neither selects
one project file. Setting the baseline itself as that variable makes mise treat
it as global. A plain `mise lock` then skips it and can lock the ancestor project
instead. The [pinned environment source](https://github.com/jdx/mise/blob/v2026.9.6/src/env.rs)
and [lock scope code](https://github.com/jdx/mise/blob/v2026.9.6/src/cli/lock.rs)
confirm this distinction.

For a scope operation, replace global/system config with explicitly empty
repo-owned TOML files, or known nonexistent sentinel paths, and stop ancestor
discovery at the target directory's **parent**. A ceiling directory itself is
excluded; setting the ceiling to the target omits its config entirely.

This exact read-only probe returned only the 13 common baseline tools and no
ancestor `infra/mise.toml`:

```sh
MISE_AUTO_INSTALL=0 \
MISE_NO_ENV=1 \
MISE_NO_HOOKS=1 \
MISE_GLOBAL_CONFIG_FILE=/tmp/mcp-stack-mise-research-no-global.toml \
MISE_SYSTEM_CONFIG_FILE=/tmp/mcp-stack-mise-research-no-system.toml \
MISE_CEILING_PATHS=/home/developer/workspace/mcp-stack/infra/toolchains \
MISE_TRUSTED_CONFIG_PATHS=/home/developer/workspace/mcp-stack/infra/toolchains/orb-devbox/mise.toml \
mise -C /home/developer/workspace/mcp-stack/infra/toolchains/orb-devbox config ls --json
```

The sentinel paths did not exist and were not created. For actual mutation use
documented repository sentinels and separately authorized commands, keeping the
same ceiling/directory pairing. Verify `config ls` first; this research did not
run lock or install. Trust only the exact reviewed file for the invocation,
not the whole `infra/` tree. `--no-config` disables all configs, so it is useful
for an explicit bare tool invocation, not loading a scope's declarations.
