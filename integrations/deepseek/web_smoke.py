"""Approval-gated Web foundation smoke test, not a normal harness launcher.

Runs a credential-free base+web profile in a fresh user/network namespace.
Never mounts the vision bundle, installs packages, or contacts model/MCP APIs.
"""

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


WEB_ROOT = "http://127.0.0.1:13080/"


class SmokeFailure(RuntimeError):
    """Only caller-owned stage labels/statuses, never vendor exception text."""

    def __init__(self, stage: str, status: int | None = None):
        self.stage = stage
        self.status = status
        super().__init__(f"Web smoke failed at {stage}; HTTP status {status}")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def launch_url_from_announcement(text: str) -> str | None:
    """Validate exact loopback URL; its temporary token stays in memory."""
    lines = [line.removeprefix("dsh web: ") for line in text.splitlines()
             if line.startswith("dsh web: ")]
    if not lines:
        return None
    if len(lines) != 1:
        raise SmokeFailure("announcement")
    value = lines[0]
    try:
        url = urllib.parse.urlsplit(value)
        query = urllib.parse.parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
        valid = (value.startswith(WEB_ROOT + "?") and not any(c.isspace() for c in value)
                 and url.scheme == "http" and url.netloc == "127.0.0.1:13080"
                 and url.path == "/" and not url.fragment
                 and len(query) == 1 and query[0][0] == "token" and bool(query[0][1]))
    except ValueError:
        valid = False
    if not valid:
        raise SmokeFailure("announcement")
    return value


def http_response(opener, url: str, stage: str):
    """HTTPError is a response, not a retryable network/readiness failure."""
    try:
        return opener.open(url, timeout=2)
    except urllib.error.HTTPError as response:
        return response
    except (urllib.error.URLError, OSError):
        raise SmokeFailure(stage) from None


def qualify_web(launch_url: str, evidence: dict) -> dict:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                        urllib.request.HTTPCookieProcessor(jar), NoRedirect())

    def request(url, stage, expected, limit):
        with http_response(opener, url, stage) as response:
            evidence[stage] = response.code
            if response.code != expected:
                raise SmokeFailure(stage, response.code)
            # Headers/body are private in-memory values and never serialized.
            return response.headers, response.read(limit)

    request(WEB_ROOT, "unauthenticated_root_http", 401, 1024)
    headers, _ = request(launch_url, "launch_exchange_http", 303, 1024)
    clean_request = urllib.request.Request(WEB_ROOT)
    jar.add_cookie_header(clean_request)
    if headers.get("Location") != "./" or not clean_request.has_header("Cookie"):
        raise SmokeFailure("launch_exchange_cookie", 303)
    evidence["launch_cookie_in_memory"] = True
    _, body = request(WEB_ROOT, "web_entry_http", 200, 8 * 1024 * 1024)
    try:
        html = body.decode()
    except UnicodeError:
        raise SmokeFailure("web_entry_content", 200) from None
    if "DeepSeek Harness" not in html:
        raise SmokeFailure("web_entry_content", 200)
    matches = re.findall(r'<script[^>]+src="([^"\s]+\.js)"', html)
    assets = [value.removeprefix("./").lstrip("/") for value in matches
              if re.fullmatch(r"(?:\./|/)?assets/index-[\w-]+\.js", value)]
    if len(assets) != 1:
        raise SmokeFailure("shell_asset_path")
    _, body = request(WEB_ROOT + assets[0], "shell_asset_http", 200, 32 * 1024 * 1024)
    if b"react/jsx-runtime" not in body:
        raise SmokeFailure("shell_asset_content", 200)
    return evidence


def private_home_manifest(root: Path) -> dict:
    """Compare content/modes/links in memory; never emit credential hashes."""
    result = {}
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Existing DSH home must be a real directory")
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            entry = {"mode": info.st_mode}
            if stat.S_ISLNK(info.st_mode):
                entry["target"] = os.readlink(path)
            elif stat.S_ISREG(info.st_mode):
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(chunk)
                entry["hash"] = digest.hexdigest()
            result[str(path.relative_to(root))] = entry
    return result


def stop_owned_process(process: subprocess.Popen) -> None:
    """Only the process group created by this test, never a port owner lookup."""
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def inside_namespace(args) -> dict:
    if os.stat("/proc/self/ns/net").st_ino == args.parent_net_inode:
        raise ValueError("Network isolation missing; refusing unsandboxed startup")
    if os.stat("/proc/self/ns/user").st_ino == args.parent_user_inode:
        raise ValueError("User isolation missing; refusing host network changes")
    if args.run_dir is None or not args.run_dir.is_dir():
        raise ValueError("Missing owned test directory")
    def terminate(signum, frame):
        # Also covers unshare's parent-death signal, so the owned server is reaped.
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    subprocess.run(["/usr/sbin/ip", "link", "set", "lo", "up"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    home = args.run_dir / "home"
    work = args.run_dir / "work"
    profile = home / "profiles/web"
    profile.mkdir(parents=True, mode=0o700)
    work.mkdir(mode=0o700)
    (profile / "package.json").write_text(json.dumps({
        "name": "mcp-stack-dsh-web-smoke", "private": True, "dependencies": {},
        "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}},
    }, indent=2) + "\n")
    # No vision bundle is present: no Python preparation or vision state copy.
    env = {
        "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
        "DSH_HOME": str(home), "DSH_TELEMETRY_DISABLED": "1",
        "NODE_DISABLE_COMPILE_CACHE": "1",
    }
    command = [str(args.node), str(args.cli_root / "lib/bin.js"), "--profile", "web",
               "--no-open", "--host", "127.0.0.1", "--port", "13080"]
    # Token-bearing startup output stays in restricted, ignored state.
    log_path = args.run_dir / "server.log"
    summary = None
    evidence = {"native_ready_announcement": False, "vision_mounted": False,
                "model_calls": False, "mcp_calls": False, "browser_render_tested": False}
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=work, env=env, stdout=log, stderr=log,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Harness exited before readiness; review private server.log")
                # Native announcement happens after the startup entry audit.
                launch_url = launch_url_from_announcement(log_path.read_text(errors="replace"))
                if launch_url is None:
                    time.sleep(0.25)
                    continue
                evidence["native_ready_announcement"] = True
                summary = qualify_web(launch_url, evidence)
                break
            if summary is None:
                raise RuntimeError("Readiness timeout; review private server.log")
        except SmokeFailure as error:
            evidence["failure_stage"] = error.stage
            evidence["failure_http_status"] = error.status
            raise
        except Exception:
            evidence["failure_stage"] = "startup_or_readiness"
            raise
        finally:
            stop_owned_process(process)
            evidence["owned_server_stopped"] = process.poll() is not None
            (args.run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return {**summary, "owned_server_stopped": process.poll() is not None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-approved", action="store_true")
    parser.add_argument("--node", required=True, type=Path)
    parser.add_argument("--cli-root", required=True, type=Path)
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--existing-home", required=True, type=Path)
    parser.add_argument("--inside-namespace", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--parent-net-inode", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--parent-user-inode", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.execute_approved:
        parser.error("Obtain concrete approval first; no startup without --execute-approved")
    os.umask(0o077)
    if args.inside_namespace:
        try:
            print(json.dumps(inside_namespace(args)))
        except SmokeFailure as error:
            parser.exit(1, json.dumps({"failure_stage": error.stage,
                                      "http_status": error.status}) + "\n")
        except Exception:
            # Vendor exception/log text may contain secrets; never dump it.
            parser.exit(1, "Isolated Web smoke failed; inspect restricted logs locally.\n")
        return
    repository = Path(__file__).resolve().parents[2]
    expected_state = repository / "infra/harnesses/deepseek/state"
    if args.state_root.is_symlink() or args.state_root.resolve() != expected_state.resolve():
        parser.error("State root must be this repository's existing restricted DeepSeek state")
    if not expected_state.is_dir() or stat.S_IMODE(expected_state.stat().st_mode) != 0o700:
        parser.error("State parent must already exist with mode 0700")
    metadata = json.loads((args.cli_root / "package.json").read_text())
    if (metadata.get("name"), metadata.get("version")) != ("@deepseek-ai/dsh", "0.2.0-rc.2"):
        parser.error("CLI identity changed; stop for review")
    if subprocess.check_output([str(args.node), "--version"], text=True, timeout=5).strip() != "v24.19.0":
        parser.error("Node identity changed; stop for review")
    for executable in ("/usr/bin/unshare", "/usr/sbin/ip"):
        if not Path(executable).is_file():
            parser.error("Required existing namespace tools missing; no install/fallback")
    before = private_home_manifest(args.existing_home)
    before_root_mode = args.existing_home.stat().st_mode
    run_dir = Path(tempfile.mkdtemp(prefix="web-smoke-", dir=expected_state))
    command = ["/usr/bin/unshare", "--user", "--map-root-user", "--net", "--fork",
               "--kill-child=TERM", sys.executable, "-I", "-B", str(Path(__file__).resolve()),
               "--execute-approved", "--inside-namespace", "--node", str(args.node),
               "--cli-root", str(args.cli_root), "--state-root", str(args.state_root),
               "--existing-home", str(args.existing_home), "--run-dir", str(run_dir),
               "--parent-net-inode", str(os.stat("/proc/self/ns/net").st_ino),
               "--parent-user-inode", str(os.stat("/proc/self/ns/user").st_ino)]
    result = None
    timed_out = False
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=90,
                                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"})
        (run_dir / "namespace.log").write_text(result.stderr)
    except subprocess.TimeoutExpired:
        # unshare --kill-child terminates its namespace child on exit.
        timed_out = True
    finally:
        unchanged = (before == private_home_manifest(args.existing_home)
                     and before_root_mode == args.existing_home.stat().st_mode)
    if timed_out or result is None or result.returncode != 0 or not unchanged:
        print(json.dumps({"smoke_passed": False, "namespace_timeout": timed_out,
                          "existing_home_unchanged": unchanged,
                          "private_run_directory": str(run_dir)}, indent=2))
        parser.exit(1, "Smoke failed; no fallback or retry.\n")
    summary = json.loads(result.stdout)
    print(json.dumps({**summary, "existing_home_unchanged": unchanged,
                      "network_isolated": True, "private_run_directory": str(run_dir)}, indent=2))


if __name__ == "__main__":
    main()
