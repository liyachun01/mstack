# Ubuntu Git restored for editors — 2026-10-18

The repository moved from `/home/developer/workspace/mcp-stack` to
`/home/developer/workspace/mstack`. The existing command symlinks and zsh bootstrap
still used the old path. Ubuntu Git had been removed during the mise migration,
so Cursor reported `Git installation not found` with no fallback available.

Git 2.54.0, git-man and Git LFS 3.7.1 are restored as Ubuntu packages under
`/usr/bin`, using the exact cached packages matched against the earlier retirement
SHA256 records. No download, unrelated package upgrade/removal or service restart
ran. Existing `~/.local/bin/git` and `git-lfs` now point directly to the system
executables, preserving paths cached by editors. Git no longer depends on the
mstack checkout or mise. Its inactive mise installations remain available for rollback.

Git/LFS declarations and lock entries were removed from the common mise profile.
The compatibility launcher/cutover and retirement helpers no longer manage/remove
system Git. The 23 other existing command links were repaired to the renamed
checkout; their versions remain unchanged. The zsh source path was corrected, and
the bootstrap now resolves its profile relative to itself. Six reviewed existing
profiles received trust at their new paths, with auto-install disabled.

Verification passed with a minimal `/usr/bin:/bin` PATH and with both running
Cursor extension hosts' actual PATH values. Each resolves Git to `/usr/bin/git`
and can inspect the mstack repository. A login shell finds Git, LFS, Node 24.19.0
and ripgrep 15.1.0. Seventeen relevant launcher/bootstrap tests pass. Git settings,
credentials and repository metadata were unchanged during the launcher repair.
No foreground app control was used. Cursor may need **Developer: Reload Window**
once to retry the Git extension after its earlier startup failure.

See [qualification.json](qualification.json). Exact pre-edit files and symlink
mappings are preserved privately under `.state/20261018/`; do not replay the older
mise migration or retirement helpers. Restoring the broken old path mappings is
not a normal rollback procedure.
