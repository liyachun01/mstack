#!/usr/bin/env python3
"""Verify pinned Ubuntu replacements without installing, logging in, or restarting.

All subprocess environments are explicitly assembled. Version probes and the
offline Git/LFS test use a private temporary HOME, never the owner's credentials.
Only private scratch files and an optional JSON evidence file are written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib

try:
    from . import inventory
except ImportError:
    import inventory


REPO = Path(__file__).resolve().parents[2]
CONFIGS = (
    "infra/toolchains/orb-devbox/mise.toml", "infra/toolchains/node-cli/mise.toml",
    "infra/toolchains/python/mise.toml", "infra/harnesses/deepseek/mise.toml",
)
TOOL_BINARIES = {
    "conda:git": "git", "git": "git", "aqua:git-lfs/git-lfs": "git-lfs",
    "aqua:cli/cli": "gh", "gh": "gh", "aqua:astral-sh/uv": "uv", "uv": "uv",
    "bun": "bun", "node": "node", "python": "python", "pnpm": "pnpm",
    "aqua:pnpm/pnpm": "pnpm", "aqua:direnv/direnv": "direnv", "direnv": "direnv",
    "aqua:sharkdp/fd": "fd", "fd": "fd", "aqua:junegunn/fzf": "fzf", "fzf": "fzf",
    "aqua:jqlang/jq": "jq", "jq": "jq", "aqua:BurntSushi/ripgrep": "rg", "ripgrep": "rg",
    "aqua:koalaman/shellcheck": "shellcheck", "shellcheck": "shellcheck",
    "aqua:mvdan/sh": "shfmt", "shfmt": "shfmt", "aqua:tmux/tmux-builds": "tmux", "tmux": "tmux",
    "npm:@deepseek-ai/dsh": "dsh", "npm:@volcengine/cli": "ve",
    "npm:@volcengine/vefaas-cli": "vefaas", "npm:ve-tos-cli": "ve-tos-cli",
    "npm:corepack": "corepack", "npm:pnpm": "pnpm",
}
VERSION_ARGS = {"git-lfs": ["version"], "direnv": ["version"], "tmux": ["-V"]}
PIN = re.compile(r"\d[0-9A-Za-z.+_-]{0,100}\Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_declarations(repo: Path = REPO) -> tuple[list[dict], dict[str, str]]:
    declarations = []
    hashes = {}
    for relative in CONFIGS:
        config = repo / relative
        raw = config.read_bytes()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
        tools = tomllib.loads(raw.decode())["tools"]
        if relative == CONFIGS[0] and any(tool in {"node", "python"} for tool in tools):
            raise ValueError("common baseline must not select Node or Python")
        for tool, options in tools.items():
            if isinstance(options, str):
                version = options
            else:
                if "os" in options and "linux" not in options["os"]:
                    continue
                version = options.get("version", "")
            if not isinstance(version, str) or not PIN.fullmatch(version):
                raise ValueError("all verified declarations must use exact version pins")
            if tool not in TOOL_BINARIES:
                raise ValueError("no approved probe for declared tool: " + tool)
            declarations.append({"tool": tool, "version": version, "config": relative,
                                 "binary": TOOL_BINARIES[tool]})
    return declarations, hashes


def isolated_environment(home: Path, bin_dirs: list[Path]) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Deliberately omit inherited PATH, API keys, proxy credentials, Node options,
    # Python startup variables and the owner's Git/SSH credential configuration.
    return {
        "HOME": str(home), "PATH": ":".join(map(str, bin_dirs + [Path("/usr/bin"), Path("/bin")])),
        "LANG": "C", "LC_ALL": "C", "TERM": "dumb", "CI": "1",
        "XDG_CONFIG_HOME": str(home / "config"), "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"), "XDG_STATE_HOME": str(home / "state"),
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false", "SSH_ASKPASS": "/bin/false",
        "GIT_SSH_COMMAND": "/bin/false", "GCM_INTERACTIVE": "never", "GIT_LFS_SKIP_SMUDGE": "1",
        "MISE_AUTO_INSTALL": "0", "MISE_NOT_FOUND_AUTO_INSTALL": "0", "MISE_YES": "0",
        "MISE_INSTALL_MISSING_TOOLS": "0",
        "COREPACK_ENABLE_NETWORK": "0", "COREPACK_ENABLE_DOWNLOAD_PROMPT": "0",
        "NPM_CONFIG_UPDATE_NOTIFIER": "false", "NPM_CONFIG_AUDIT": "false",
        "UV_OFFLINE": "1", "UV_NO_PROGRESS": "1", "DO_NOT_TRACK": "1",
    }


def resolution_environment(mise: Path, scratch: Path, home: Path, repo: Path) -> dict[str, str]:
    env = isolated_environment(scratch / "mise-home", [mise.parent])
    env.update({"MISE_DATA_DIR": str(home / ".local/share/mise"),
                "MISE_CACHE_DIR": str(scratch / "mise-cache"),
                "MISE_STATE_DIR": str(scratch / "mise-state"),
                "MISE_CONFIG_DIR": str(scratch / "mise-config"),
                "MISE_GLOBAL_CONFIG_FILE": str(repo / CONFIGS[0]),
                "MISE_TRUSTED_CONFIG_PATHS": str(repo / "infra")})
    return env


def resolve_prefix(mise: Path, declaration: dict, scratch: Path, home: Path, repo: Path) -> Path:
    env = resolution_environment(mise, scratch, home, repo)
    result = subprocess.run([str(mise), "where", declaration["tool"] + "@" + declaration["version"]],
                            cwd=(repo / declaration["config"]).parent, env=env,
                            capture_output=True, text=True, check=False, timeout=30)
    # Do not print stderr: misconfigured tools could echo private configuration.
    if result.returncode:
        raise ValueError("exact installation not resolved")
    prefix = Path(result.stdout.strip())
    if not prefix.is_absolute() or not prefix.is_dir():
        raise ValueError("mise did not return an installed absolute directory")
    if not inventory.within(prefix, home / ".local/share/mise/installs"):
        raise ValueError("resolved installation is outside the managed installs directory")
    return prefix


def find_binary(prefix: Path, name: str) -> Path:
    for candidate in (prefix / "bin" / name, prefix / name):
        if candidate.is_file() and os.access(candidate, os.X_OK) and inventory.within(candidate, prefix):
            return candidate
    raise ValueError("declared binary not found within the selected installation")


def resolve_binary(mise: Path, declaration: dict, prefix: Path, scratch: Path,
                   home: Path, repo: Path) -> Path:
    """Use the backend's exact executable layout, including extracted archives."""
    env = resolution_environment(mise, scratch, home, repo)
    result = subprocess.run(
        [str(mise), "which", declaration["binary"], "--tool",
         declaration["tool"] + "@" + declaration["version"]],
        cwd=(repo / declaration["config"]).parent, env=env,
        capture_output=True, text=True, check=False, timeout=30,
    )
    if result.returncode:
        raise ValueError("exact executable not resolved")
    candidate = Path(result.stdout.strip())
    if (not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK)
            or not inventory.within(candidate, prefix)):
        raise ValueError("resolved executable is outside its selected installation")
    return candidate


def metadata_version(prefix: Path, tool: str) -> str:
    name = tool.removeprefix("npm:")
    for manifest in (prefix / "lib/node_modules" / name / "package.json",
                     prefix / "node_modules" / name / "package.json"):
        raw = inventory.bounded_read(manifest, prefix)
        if raw:
            data = json.loads(raw)
            if data.get("name") == name and PIN.fullmatch(str(data.get("version", ""))):
                return data["version"]
    raise ValueError("pinned npm package metadata unavailable")


def probe_version(entry: dict, env: dict, cwd: Path) -> dict:
    if entry["tool"].startswith("npm:") and entry["binary"] not in {"corepack", "pnpm"}:
        actual = metadata_version(Path(entry["prefix"]), entry["tool"])
        if actual != entry["version"]:
            raise ValueError("npm metadata version does not match the declared pin")
        return {"observed_version": actual, "evidence": "package metadata; no provider/profile startup"}
    result = subprocess.run([entry["executable"], *VERSION_ARGS.get(entry["binary"], ["--version"])],
                            env=env, cwd=cwd, capture_output=True, text=True, check=False, timeout=20)
    if result.returncode:
        raise ValueError("version probe failed")
    # Expose only the matched expected version, never raw tool output.
    match = re.search(r"(?<![0-9A-Za-z.])v?(" + re.escape(entry["version"]) + r")(?![0-9A-Za-z.])",
                      result.stdout + result.stderr)
    if not match:
        raise ValueError("version probe did not match the declared pin")
    return {"observed_version": match.group(1), "evidence": "isolated version command"}


def check_backup(root: Path = inventory.OUTPUT_ROOT) -> bool:
    """Validate the exact saved archive without extraction or exposing its paths."""
    try:
        pointer = inventory.bounded_read(root / "current-path.txt", root)
        if not pointer:
            return False
        base = Path(pointer.decode().strip())
        if not base.is_absolute() or not inventory.within(base, root):
            return False
        raw = inventory.bounded_read(base / "baseline.json", root)
        data = json.loads(raw) if raw else {}
        archive = Path(data["archive"])
        expected = data["archive_sha256"]
        if (not archive.is_absolute() or not inventory.within(archive, base) or not archive.is_file()
                or archive.stat().st_mode & 0o077 or not re.fullmatch(r"[a-f0-9]{64}", expected)):
            return False
        return sha256(archive) == expected
    except (OSError, ValueError, TypeError, KeyError):
        return False


def offline_git_smoke(git: Path, bin_dirs: list[Path], scratch: Path) -> dict:
    """Exercise only a scratch repository, with no remote or owner configuration."""
    scratch.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = isolated_environment(scratch / "home", bin_dirs)
    repo, worktree = scratch / "repo", scratch / "worktree"
    hooks = scratch / "hooks"
    hooks.mkdir(mode=0o700)
    passed = []

    def run(step: str, args: list[str]) -> str:
        result = subprocess.run([str(git), "-c", "core.hooksPath=" + str(hooks), *args],
                                env=env, cwd=scratch, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError("offline Git step failed: " + step)
        passed.append(step)
        return result.stdout

    run("init", ["init", "--initial-branch=main", "--template=", str(repo)])
    run("lfs-local-install", ["-C", str(repo), "lfs", "install", "--local", "--skip-smudge"])
    run("lfs-track", ["-C", str(repo), "lfs", "track", "*.bin"])
    asset = b"private offline toolchain verification\n" * 64
    (repo / "asset.bin").write_bytes(asset)
    (repo / "note.txt").write_text("scratch-only verification\n")
    run("add", ["-C", str(repo), "add", "--", "note.txt", "asset.bin", ".gitattributes"])
    run("commit", ["-C", str(repo), "-c", "user.name=Toolchain verification", "-c",
                   "user.email=verification@example.invalid", "commit", "-m", "Offline verification"])
    pointer = run("lfs-pointer-readback", ["-C", str(repo), "show", "HEAD:asset.bin"])
    if "oid sha256:" + hashlib.sha256(asset).hexdigest() not in pointer:
        raise ValueError("Git LFS did not store the expected object pointer")
    run("lfs-object-fsck", ["-C", str(repo), "lfs", "fsck"])
    commit = run("head", ["-C", str(repo), "rev-parse", "HEAD"]).strip()
    run("worktree-add", ["-C", str(repo), "worktree", "add", "-b", "verification", str(worktree)])
    if run("worktree-head", ["-C", str(worktree), "rev-parse", "HEAD"]).strip() != commit:
        raise ValueError("worktree HEAD differs from its source commit")
    if run("worktree-clean", ["-C", str(worktree), "status", "--porcelain"]).strip():
        raise ValueError("verification worktree is unexpectedly dirty")
    run("worktree-remove", ["-C", str(repo), "worktree", "remove", str(worktree)])
    return {"passed": True, "steps": passed, "scope": "private scratch repository; no remotes"}


def verify(mise: Path, state: Path, home: Path = Path.home(), repo: Path = REPO) -> dict:
    declarations, before = read_declarations(repo)
    results, failures, resolved = [], [], {}
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.stat().st_mode & 0o077:
        raise ValueError("scratch state directory must have mode 0700")
    with tempfile.TemporaryDirectory(prefix="verification-", dir=state) as directory:
        scratch = Path(directory)
        for declaration in declarations:
            key = (declaration["tool"], declaration["version"])
            if key in resolved:
                continue
            entry = dict(declaration)
            try:
                prefix = resolve_prefix(mise, declaration, scratch, home, repo)
                binary = resolve_binary(mise, declaration, prefix, scratch, home, repo)
                entry.update(prefix=str(prefix), executable=str(binary), realpath=str(binary.resolve()))
                resolved[key] = entry
            except (ValueError, OSError, subprocess.SubprocessError):
                failures.append({"tool": declaration["tool"], "version": declaration["version"],
                                 "stage": "resolve", "reason": "exact installation or executable unavailable"})
            results.append(entry)
        dirs = list(dict.fromkeys(Path(e["executable"]).parent for e in resolved.values()))
        env = isolated_environment(scratch / "probe-home", dirs)
        for entry in resolved.values():
            try:
                entry.update(probe_version(entry, env, scratch))
            except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError):
                failures.append({"tool": entry["tool"], "version": entry["version"],
                                 "stage": "version", "reason": "isolated version or package metadata check failed"})
        by_binary = {entry["binary"]: Path(entry["executable"]) for entry in resolved.values()}
        git_evidence = {"passed": False, "reason": "managed Git and Git LFS both required"}
        if "git" in by_binary and "git-lfs" in by_binary:
            try:
                git_evidence = offline_git_smoke(by_binary["git"], dirs, scratch / "git-smoke")
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                git_evidence = {"passed": False, "reason": str(error) if isinstance(error, ValueError) else "Git subprocess failed"}
        if not git_evidence["passed"]:
            failures.append({"stage": "offline-git", "reason": git_evidence["reason"]})
    after = {relative: sha256(repo / relative) for relative in before}
    if after != before:
        failures.append({"stage": "preservation", "reason": "toolchain declarations changed during verification"})
    if not Path("/usr/bin/python3").is_file() or not Path("/usr/bin/psql").is_file():
        failures.append({"stage": "preservation", "reason": "retained OS Python or PostgreSQL client missing"})
    return {"passed": not failures, "tools": results, "failures": failures,
            "git_offline": git_evidence, "config_hashes": after,
            "source_rollback_contract": {
                "declarations_unchanged": before == after, "temporary_scratch_removed": not scratch.exists(),
                "writes": "private temporary scratch and optional report only",
                "installs": False, "provider_calls": False, "user_home_mutations": False,
                "service_or_process_lifecycle": False, "global_git_config_writes": False,
            },
            "retained_os_dependencies": {"python": str(Path("/usr/bin/python3").resolve()),
                                         "psql": str(Path("/usr/bin/psql").resolve())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mise", type=Path, default=Path.home() / ".local/bin/mise")
    parser.add_argument("--state", type=Path, default=inventory.OUTPUT_ROOT / ".secrets/verification")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-backup", action="store_true", help="rehash saved rollback archive without extraction")
    args = parser.parse_args()
    if not inventory.within(args.state, inventory.OUTPUT_ROOT):
        parser.error("state must remain under infra/maintenance/orb-devbox-mise")
    result = verify(args.mise, args.state)
    if args.check_backup:
        result["archive_verified"] = check_backup()
        if not result["archive_verified"]:
            result["passed"] = False
            result["failures"].append({"stage": "backup", "reason": "private rollback archive verification failed"})
    if args.output:
        inventory.write_output(args.output, result)
        print(json.dumps({"passed": result["passed"], "output": str(args.output), "failures": result["failures"],
                          "archive_verified": result.get("archive_verified")}))
    else:
        print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
