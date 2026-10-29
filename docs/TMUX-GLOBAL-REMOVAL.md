# macOS global tmux removal — completed

Explicitly requested on 2026-10-01: remove global mise-installed tmux and its configs. Applied the project setup guard and careful-removal checks. No Ubuntu mise/toolchain or project tool declaration changed.

Read-only inventory found a single global mise selection `tmux = "latest"`, resolved to **3.7c**, under `/Users/{{mstack:MAC_USER}}/.local/share/mise/installs/tmux/3.7c`. No running tmux process was found. No `.tmux.conf`, `.tmux.conf.local`, `.tmux/` or `.config/tmux/` existed in the macOS user home; there were no dedicated tmux configuration files to delete.

Executed on macOS through Ubuntu `macctl run`, with auto-install disabled:

```sh
MISE_AUTO_INSTALL=0 mise unuse --global --no-prune tmux
MISE_AUTO_INSTALL=0 mise uninstall tmux@3.7c
MISE_AUTO_INSTALL=0 mise reshim
```

Removed the global tmux declaration, exact installed version and shim. Verified no `tmux` on the checked macOS PATH and no remaining mise tmux installation/download/cache directory or shim. **gh 2.101.0 (`latest`) and xcbeautify 3.2.1 remain selected/installed unchanged**. Mise itself was not updated. No user sessions were terminated, harness config modified or Docker service acted on by this cleanup.

Ignored recovery material lives in `backups/tmux-removal-20261001/`, directory 0700: original global TOML (0600), leftover version-cache contents and dangling `latest` symlink. Empty download directory removed. Initial macOS-to-VM move failed because extended attributes could not be copied; recovered with a content-only `cp -R -X`, byte comparisons, and removal of only the verified residual files/empty directories. Extended attributes are not backed up.

The binary itself was uninstalled, not archived. Restoring it would require a separately approved reinstall; this backup is not a complete installed-tool restore. Restore only the tmux declaration if requested, not the entire old global config over future unrelated edits. Cache files are disposable and not needed to reinstall. No automatic restore or cleanup of these backups.

The remaining global config contains exactly:

```toml
[tools]
gh = "latest"
xcbeautify = "3.2.1"
```
