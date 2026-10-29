import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[2]
key = (root / ".secrets/agentgateway-client-key").read_text().strip()
assert len(key) == 64 and all(c in "0123456789abcdef" for c in key)


def status(path, credential=None):
    config = "" if credential is None else 'header = "Authorization: Bearer ' + credential + '"\n'
    result = subprocess.run(
        ["macctl", "run", "curl", "--config", "-", "--silent",
         "--show-error", "--noproxy", "*", "--max-time", "3",
         "--output", "-", "--write-out", "\n%{http_code}",
         "http://127.0.0.1:58080" + path],
        cwd=root, input=config, text=True, capture_output=True, timeout=10,
    )
    code = result.stdout.rsplit("\n", 1)[-1]
    return int(code) if result.returncode == 0 and code.isdigit() else 0


deadline = time.monotonic() + 30
while status("/healthz", key) != 200:
    if time.monotonic() >= deadline:
        raise SystemExit("Gateway did not become ready; inspect sanitized operational logs")
    time.sleep(1)

for path in ["/healthz", "/mcp", "/ui", "/api/runtime", "/unmatched"]:
    for credential in [None, "invalid-foundation-key"]:
        actual = status(path, credential)
        if actual not in [401, 403]:
            raise SystemExit(f"Authentication rejection failed for {path}: HTTP {actual}")

for path, expected in [("/healthz", 200), ("/mcp", 503), ("/ui", 404),
                       ("/api/runtime", 404), ("/unmatched", 404)]:
    actual = status(path, key)
    if actual != expected:
        raise SystemExit(f"Route check failed for {path}: HTTP {actual}, expected {expected}")
print("PASS: authenticated health, missing/invalid-key rejection, unavailable MCP and no public UI/API")
