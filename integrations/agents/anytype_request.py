"""Run on macOS: access its loopback Anytype API with a project-private key.

No key is sent through command arguments, stdout or the clipboard. This utility
does not register MCP tools. Bootstrap reads qualify the key before Space binding.
"""
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request


def main():
    p = argparse.ArgumentParser()
    p.add_argument("credential", type=Path)
    p.add_argument("method", choices=["GET", "POST", "PATCH"])
    p.add_argument("path")
    p.add_argument("--body", type=Path)
    p.add_argument("--space")
    p.add_argument("--idempotency-key")
    args = p.parse_args()
    args.path = "/" + args.path.lstrip("/")
    bootstrap = args.method == "GET" and (
        args.path in ["/v2/auth/whoami", "/v2/spaces?ids=full"]
        or args.path.startswith("/v2/schemas")
    )
    scoped = args.space and args.path.startswith("/v2/spaces/" + args.space + "/")
    if not (bootstrap or scoped):
        sys.exit("Request outside the explicitly bound Space")
    if args.credential.is_symlink() or args.credential.stat().st_mode & 0o077:
        sys.exit("Credential must be a private regular file")
    key = args.credential.read_text().strip()
    if not key:
        sys.exit("Credential is empty")
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if args.idempotency_key:
        headers["Idempotency-Key"] = args.idempotency_key
    request = urllib.request.Request(
        "http://127.0.0.1:31009" + args.path,
        data=args.body.read_bytes() if args.body else None,
        method=args.method, headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(json.dumps({"http_status": response.status,
                              "body": json.loads(response.read())}))
    except urllib.error.HTTPError as error:
        print(json.dumps({"http_status": error.code,
                          "body": error.read().decode()}))
        sys.exit(1)


if __name__ == "__main__":
    main()
