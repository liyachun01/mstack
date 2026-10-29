#!/usr/bin/env python3
"""Read-only Ubuntu toolchain evidence; never execute a discovered tool or shim.

The output intentionally omits process argv/environments, shell contents, and
credential files. Directory discovery is bounded to named runtime stores. Only
--output writes anything, and that path must be in the private migration area.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone


REPO = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO / "infra/maintenance/orb-devbox-mise"
TOOLS = (
    "mise", "node", "npm", "pnpm", "corepack", "fnm", "bun", "deno", "uv", "uvx",
    "python", "python3", "git", "git-lfs", "gh", "direnv", "fd", "fdfind", "fzf",
    "jq", "rg", "shellcheck", "shfmt", "tmux", "psql", "swift", "gcc", "make",
    "dsh", "ve", "vefaas", "ve-tos", "graphify", "headroom", "codex",
)
DPKG_PACKAGES = (
    "git", "git-man", "git-lfs", "gh", "direnv", "fd-find", "fzf", "jq", "ripgrep",
    "shellcheck", "shfmt", "tmux", "postgresql-client", "postgresql-client-18",
    "postgresql-client-common", "python3", "python3.14", "swiftlang", "libswiftlang",
    "build-essential", "gcc", "g++", "make", "pkgconf", "zlib1g-dev",
)
NODE_PACKAGES = (
    "npm", "corepack", "pnpm", "@deepseek-ai/dsh", "@volcengine/cli",
    "@volcengine/vefaas-cli", "ve-tos-cli", "agent-browser", "wrangler",
)
SHELL_FILES = (".zshrc", ".zprofile", ".zshenv", ".bashrc", ".bash_profile", ".profile")
REPO_CONFIGS = (
    "infra/mise.toml", "infra/mise.lock", "infra/toolchains/orb-devbox/mise.toml",
    "infra/toolchains/orb-devbox/mise.lock", "infra/harnesses/deepseek/mise.toml",
    "infra/harnesses/deepseek/mise.lock", "integrations/agents/deepseek_launch.py",
)
SHELL_MARKERS = {
    "fnm": r"\bfnm\b", "mise": r"\bmise\b", "bun": r"\.bun/|\bBUN_INSTALL\b",
    "deno": r"\.deno/|\bDENO_INSTALL\b", "uv": r"\buv\b|\.local/bin/env",
    "direnv": r"\bdirenv\b", "pnpm": r"\bPNPM_HOME\b|\bpnpm\b",
}
LISTEN_PORTS = {3080: "deepseek-web", 58081: "deepseek-forwarder", 58080: "agentgateway-mcp",
                58084: "agentgateway-ui"}
VERSION = re.compile(r"v?\d[0-9A-Za-z.+_-]{0,100}\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,100}\Z")
MODULE_PREFIXES = ("headroom", "serena", "graphify", "mcp", "uvicorn", "pytest")
SCRIPT_NAMES = {
    "deepseek_launch.py": "deepseek-launcher", "gateway-forwarder.mjs": "deepseek-forwarder",
    "transport_forwarder.mjs": "deepseek-forwarder", "typescript-language-server": "typescript-language-server",
    "tsserver.js": "typescript-server", "pyright-langserver.js": "pyright-language-server",
    "langserver.index.js": "pyright-language-server", "serena": "serena",
    "headroom": "headroom", "graphify": "graphify", "graphifyy": "graphify",
    "dsh": "deepseek-harness", "dsh.js": "deepseek-harness",
}
MAX_FILE = 4 * 1024 * 1024


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError, RuntimeError):
        return False


def bounded_read(path: Path, root: Path) -> bytes | None:
    """Do not follow a runtime-store symlink into an unrelated location."""
    try:
        if not within(path, root) or not path.is_file() or path.stat().st_size > MAX_FILE:
            return None
        return path.read_bytes()
    except OSError:
        return None


def child_dirs(path: Path, root: Path) -> list[Path]:
    if not within(path, root):
        return []
    try:
        # Runtime stores have a small, bounded number of direct children. No rglob/walk.
        return sorted((p for p in path.iterdir() if SAFE_NAME.fullmatch(p.name)
                       and p.is_dir() and within(p, root)), key=lambda p: p.name)[:128]
    except OSError:
        return []


def executable_inventory(path: str | None = None) -> dict:
    found = {}
    for tool in TOOLS:
        selected = shutil.which(tool, path=path)
        entry = {"path": selected, "realpath": None}
        if selected:
            try:
                target = Path(selected).resolve()
                stat = target.stat()
                entry.update(realpath=str(target), size=stat.st_size, device=stat.st_dev,
                             inode=stat.st_ino)
            except OSError:
                entry["unreadable"] = True
        found[tool] = entry
    return found


def dpkg_inventory() -> dict:
    if not Path("/usr/bin/dpkg-query").is_file():
        return {}
    result = subprocess.run(
        ["/usr/bin/dpkg-query", "-W", "-f=${Package}\t${Version}\t${db:Status-Abbrev}\n", *DPKG_PACKAGES],
        check=False, capture_output=True, text=True, timeout=10,
        env={"PATH": "/usr/bin:/bin", "LANG": "C"},
    )
    installed = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[0] in DPKG_PACKAGES and fields[2].startswith("ii"):
            installed[fields[0]] = fields[1]
    return installed


def node_manifests(prefix: Path, root: Path) -> list[dict]:
    packages = []
    for name in NODE_PACKAGES:
        manifest = prefix / "lib/node_modules" / name / "package.json"
        raw = bounded_read(manifest, root)
        if raw is None:
            continue
        try:
            data = json.loads(raw)
            version = data.get("version", "")
            if data.get("name") == name and isinstance(version, str) and VERSION.fullmatch(version):
                packages.append({"name": name, "version": version, "manifest": str(manifest)})
        except (ValueError, AttributeError):
            continue
    return packages


def installed_stores(home: Path) -> dict:
    stores = {"mise": [], "fnm": [], "uv_python": [], "uv_tools": []}
    mise_root = home / ".local/share/mise/installs"
    for tool in child_dirs(mise_root, mise_root):
        for version in child_dirs(tool, mise_root):
            if VERSION.fullmatch(version.name):
                stores["mise"].append({"tool": tool.name, "version_label": version.name,
                                       "realpath": str(version.resolve()),
                                       "path": str(version), "node_packages": node_manifests(version, mise_root)})
    fnm_root = home / ".local/share/fnm/node-versions"
    for version in child_dirs(fnm_root, fnm_root):
        if VERSION.fullmatch(version.name):
            prefix = version / "installation"
            stores["fnm"].append({"version_label": version.name, "path": str(prefix),
                                  "node_packages": node_manifests(prefix, fnm_root)})
    python_root = home / ".local/share/uv/python"
    for prefix in child_dirs(python_root, python_root):
        if re.fullmatch(r"cpython-[0-9][A-Za-z0-9_.+-]{0,120}", prefix.name):
            stores["uv_python"].append({"version_label": prefix.name, "path": str(prefix),
                                       "realpath": str(prefix.resolve())})
    tools_root = home / ".local/share/uv/tools"
    for tool, distribution in (("graphifyy", "graphifyy"), ("headroom-ai", "headroom_ai")):
        prefix = tools_root / tool
        if not within(prefix, tools_root) or not prefix.is_dir():
            continue
        distributions = []
        for python in child_dirs(prefix / "lib", tools_root):
            site = python / "site-packages"
            # Exact distribution glob at one level, not a scan of its dependency tree.
            for info in sorted(site.glob(distribution + "-*.dist-info"))[:8]:
                if not within(info, tools_root):
                    continue
                raw = bounded_read(info / "METADATA", tools_root)
                if raw:
                    match = re.search(rb"^Version: ([0-9][A-Za-z0-9.+_-]{0,100})\r?$", raw, re.M)
                    if match:
                        distributions.append(match[1].decode("ascii"))
        stores["uv_tools"].append({"tool": tool, "path": str(prefix),
                                    "python_realpath": str((prefix / "bin/python").resolve()),
                                    "versions": sorted(set(distributions))})
    return stores


def safe_process_identifier(argv: list[str]) -> str | None:
    """Recognize only known scripts/modules. Never return an arbitrary argument.

    In particular -c/-e/--eval payloads, URLs, inline credentials and later
    user-supplied arguments cannot become a supposed script name.
    """
    if not argv:
        return None
    for index, arg in enumerate(argv[1:], 1):
        if arg in {"-c", "-e", "--eval", "-p", "--print", "--"}:
            return None
        if arg == "-m":
            if index + 1 < len(argv):
                module = argv[index + 1]
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,100}", module):
                    for prefix in MODULE_PREFIXES:
                        if module == prefix or module.startswith(prefix + "."):
                            # Product identity is enough. Arbitrary submodule names
                            # could contain user-supplied private identifiers.
                            return "module:" + prefix
            return None
        if arg.startswith("-"):
            continue
        # First positional argument only: following arguments can contain anything.
        if "://" in arg or "?" in arg or "#" in arg or "=" in arg:
            return None
        basename = Path(arg).name
        return SCRIPT_NAMES.get(basename)
    return None


def process_record(proc: Path) -> dict | None:
    try:
        executable = os.readlink(proc / "exe")
        cwd = os.readlink(proc / "cwd")
        # Keep only start ticks from stat; do not expose the possibly sensitive comm.
        stat_tail = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        record = {"pid": int(proc.name), "executable": executable, "cwd": cwd,
                  "start_ticks": int(stat_tail[19])}
        argv = (proc / "cmdline").read_bytes().split(b"\0")
        identifier = safe_process_identifier([arg.decode("utf-8", "replace") for arg in argv if arg])
        if identifier:
            record["identifier"] = identifier
        return record
    except (OSError, ValueError, IndexError):
        return None


def relevant_process(record: dict) -> bool:
    basename = Path(record["executable"].removesuffix(" (deleted)")).name
    return bool(re.fullmatch(r"(?:node|nodejs|python(?:\d+(?:\.\d+)?)?|bun|uv|uvx|mise|fnm|codex)", basename)
                or record.get("identifier"))


def listener_inodes(proc_root: Path) -> list[dict]:
    rows = []
    for table, family in (("tcp", socket.AF_INET), ("tcp6", socket.AF_INET6)):
        try:
            lines = (proc_root / "net" / table).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            try:
                address, port_hex = fields[1].split(":")
                port = int(port_hex, 16)
                if fields[3] != "0A" or port not in LISTEN_PORTS:
                    continue
                raw = bytes.fromhex(address)
                raw = b"".join(raw[i:i + 4][::-1] for i in range(0, len(raw), 4))
                rows.append({"name": LISTEN_PORTS[port], "address": socket.inet_ntop(family, raw),
                             "port": port, "inode": int(fields[9])})
            except (IndexError, ValueError, OSError):
                continue
    return rows


def process_inventory(proc_root: Path = Path("/proc")) -> tuple[list[dict], list[dict]]:
    listeners = listener_inodes(proc_root)
    by_inode = {row["inode"]: row for row in listeners}
    processes = []
    try:
        entries = sorted((p for p in proc_root.iterdir() if p.name.isdecimal()), key=lambda p: int(p.name))
    except OSError:
        return [], listeners
    for proc in entries:
        record = process_record(proc)
        if not record:
            continue
        if relevant_process(record):
            processes.append(record)
        if by_inode:
            try:
                for descriptor in (proc / "fd").iterdir():
                    target = os.readlink(descriptor)
                    match = re.fullmatch(r"socket:\[(\d+)\]", target)
                    if match and int(match[1]) in by_inode:
                        row = by_inode[int(match[1])]
                        owners = row.setdefault("processes", [])
                        if not any(owner["pid"] == record["pid"] for owner in owners):
                            owners.append(record)
            except OSError:
                continue
    return processes, listeners


def config_inventory(home: Path, repo: Path) -> list[dict]:
    files = [(home / name, home, True) for name in SHELL_FILES]
    files += [(home / ".config/mise/config.toml", home, False)]
    files += [(repo / name, repo, False) for name in REPO_CONFIGS]
    result = []
    for path, scope, shell in files:
        # Fixed filename allowlist; reject secret-directory symlink destinations too.
        resolved = path.resolve()
        if any(part in {".secrets", ".aws", ".ssh", ".gnupg"} for part in resolved.parts):
            continue
        raw = bounded_read(path, scope)
        entry = {"path": str(path), "present": raw is not None}
        if raw is not None:
            entry.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
            if shell:
                matches = {}
                for number, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
                    if line.lstrip().startswith("#"):
                        continue
                    for marker, pattern in SHELL_MARKERS.items():
                        if re.search(pattern, line):
                            matches.setdefault(marker, []).append(number)
                entry["toolchain_lines"] = matches
        result.append(entry)
    return result


def inventory(home: Path = Path.home(), repo: Path = REPO) -> dict:
    processes, listeners = process_inventory()
    visible_pids = sum(p.name.isdecimal() for p in Path("/proc").iterdir())
    return {"schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
            "execution_domain": "orb-devbox-ubuntu", "uid": os.getuid(),
            "coverage": "fixed runtime stores, selected apt packages/configs, readable procfs; no tool execution",
            "executables": executable_inventory(), "dpkg": dpkg_inventory(),
            "installed_stores": installed_stores(home), "processes": processes,
            "procfs_visibility": {
                "visible_pid_count": visible_pids,
                "pid_1_visible": Path("/proc/1").is_dir(),
                "restricted_visibility_suspected": not Path("/proc/1").is_dir(),
                "scope_note": "Only readable procfs entries are covered; missing consumers are not proof they are absent.",
            },
            "named_listeners": listeners, "config_hashes": config_inventory(home, repo)}


def write_output(output: Path, data: dict, root: Path = OUTPUT_ROOT) -> None:
    target = output.resolve()
    if not within(target, root) or target == root.resolve():
        raise ValueError("output must be a file under infra/maintenance/orb-devbox-mise")
    if not target.parent.is_dir():
        raise ValueError("create the private output parent directory first")
    if target.parent.stat().st_mode & 0o077:
        raise ValueError("output parent must have mode 0700")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="private JSON output under infra/maintenance/orb-devbox-mise")
    args = parser.parse_args()
    evidence = inventory()
    if args.output:
        write_output(args.output, evidence)
        print(json.dumps({"output": str(args.output), "process_count": len(evidence["processes"])}))
    else:
        print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
