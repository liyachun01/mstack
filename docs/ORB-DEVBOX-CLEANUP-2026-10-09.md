# orb-devbox cleanup and macOS compression check

**Later update — 2026-10-15:** the user authorized and completed the Linux mise
cutover and safe duplicate cleanup. The proposal-only status in this dated
record is historical. See the [migration result](ORB-DEVBOX-MISE-MIGRATION-2026-10-15.md)
for current selections, required legacy retention and rollback evidence.

Updated 2026-10-09, Asia/Shanghai. This records the user's follow-up to the
[toolchain audit](ORB-DEVBOX-MISE-AUDIT-2026-10-09.md).

## Completed Linux removals

- Uninstalled the mise-managed **Supabase CLI 2.117.0**. Removed its dedicated
  download/cache directories, aliases, shims and installation metadata, plus
  `~/.supabase` telemetry/traces and the verified-empty `~/supabase/tests`
  scaffold. Project source, database containers and volumes were preserved.
- Removed standalone **Deno 2.9.5** and `~/.deno`; removed its two PATH/environment
  lines from `~/.zshrc`.
- Changed the existing Supabase selection in `{{mstack:CLIENT_REPO}}`, `{{mstack:CLIENT_REPO}}-growth`,
  `{{mstack:CLIENT_REPO}}-growth-implementation` and `{{mstack:CLIENT_REPO}}-memory-speed` to
  `supabase = { version = "latest", os = ["macos"] }`. Linux no longer selects
  that tool; existing Node/Wrangler declarations and lockfiles were preserved.

Verification: neither CLI resolves, all removed targets are absent, `zsh -n`
passes, and offline mise selection in all four {{mstack:CLIENT_REPO_CAMEL}} checkouts includes only
their existing Node/Wrangler tools. All **15 existing Docker container IDs and
names** match before/after; no container lifecycle or database operation ran.

Private configuration backups, hashes, cleanup manifest, container comparison
and verification results are under ignored mode-0700
`infra/maintenance/orb-devbox-cleanup/20261009-194523/.secrets/`. Backed-up files
have mode 0600. Deleted binaries/caches were not copied: restoring the runtimes
would require obtaining the exact versions again. Restore individual config
edits against current contents rather than overwriting another chat's changes.

## Bun dependency found; retained for now

The user asked why gstack needs Bun and said to keep it if already mise-managed.
Linux **Bun 1.3.14 is actually standalone**, at `~/.bun/bin/bun`: no mise Bun
installation, shim or receipt exists. It is preserved for now as a gstack
dependency; moving it under mise remains part of the proposed migration.

During the cleanup audit, two running {{mstack:CLIENT_REPO_CAMEL}} gstack helpers executed
`browse/src/terminal-agent.ts` and `browse/src/server.ts` from
`{{mstack:CLIENT_REPO}}/.agents/vendor/gstack`. Other gstack scripts also depend on Bun.
The two helpers were absent at the follow-up inspection; this task did not stop
them. No Bun process, installation, cache or shell hook was changed. The earlier
assumption that Bun was unused is superseded by these source/process checks.

gstack's `ARCHITECTURE.md` explains the choice: compiled executables, built-in
SQLite for Chromium cookie handling, direct TypeScript execution, and a built-in
HTTP server. Its package declares `engines.bun`; browser/terminal code uses
`Bun.serve` and other Bun APIs. Installing Node does not replace that dependency
without adapting the source. Compiled executables can bundle the runtime, but
the source helpers and other scripts still invoke external Bun.

macOS Bun belongs to the compression lab's pinned toolchain and is outside the
Linux removal request.

## iOS compression tests already moved to macOS

The active native test workspace is
`/Users/{{mstack:MAC_USER}}/Developer/{{mstack:CLIENT_BRAND_LOWER}}-ios-media-lab`, branch
`codex/media-compression-lab`, clean at `ce43bc2`. Its provenance records the
Linux source checkout. Its `Lab/Sources/MemoryUploadCompression.swift` matches
the Linux candidate byte for byte (SHA-256
`6d7daa28a81287ff543ab1f712a5ff5f6f003e5db87d79db9a029a2c4aebe83f`).

Existing lab evidence records simulator build/visible compression checks,
18 local uploads across the CN/Global test peers, generated EXIF verification
and raw-file fallback. Preview checks record successful EXIF/client-copy checks
but incomplete large CN transport. These are existing simulator/lab records;
this audit performed no new build, device test, upload or deployment.

Use the macOS lab for further compression testing. The Linux
`{{mstack:CLIENT_BRAND_LOWER}}-ios-memory-speed` clone still has an uncommitted
`MemoryImportService.swift` integration patch that is absent from the lab.
Preserve that patch before retiring the clone; the lab does not constitute a
completed production app integration. The two growth worktrees remain retirement
candidates; `{{mstack:CLIENT_REPO}}-memory-speed` still contains local backend work to preserve.

## Inbox Zero and host Node

For the full Docker deployment, Node runs **inside the application containers**.
Host Node 24+ is needed for the optional setup CLI or source installation,
not for ongoing `docker compose` operation. Manual setup is supported.
[Official deployment guide](https://docs.getinboxzero.com/hosting/self-hosting),
[container startup source](https://github.com/elie222/inbox-zero/blob/0ae922dfd758f89e66aaa14272e6b88d3120bcce/docker/scripts/start.sh).

Keep the configuration in this VM's `infra/inbox-zero/`, and use the existing
macOS OrbStack Docker engine through its bridge. Container execution is on that
engine, rather than a new daemon in the `devbox` guest. Docker/Compose remain
system infrastructure. Neither an extra macOS Node installation nor a Linux
Docker daemon is needed.

macOS already has mise-managed Node **24.21.0** and Node/npm shims. A shell outside
a configured project reports no selected version; that is not a missing install
and does not justify setting a global version. Linux also has Node 24.21.0 under
mise, while active consumers still use fnm's Node 24.19.0. That broader migration
remains planned. Inbox Zero was installed later at the user's request using
Option B and recovered shared PG; see the
[completion report](INBOX-ZERO-SETUP-REPORT-2026-10-09.md) and
[integration plan](INBOX-ZERO-SETUP-PLAN.md).
