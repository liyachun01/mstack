"""macOS-local, explicitly Space-bound API client for the kase migration."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Authenticated API redirects are outside the bound transport")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".checkpoint-")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Client:
    def __init__(self, config, archive_type_keys=()):
        destination = config["destination"]
        if destination["api_execution_domain"] != "macos-desktop":
            raise ValueError("Migration requires the desktop's macOS loopback domain")
        self.space = destination["space_id"]
        # Cleanup is opt-in and restricted to exact migration-owned type keys.
        # Ordinary transfer clients still reject every deletion.
        self.archive_type_paths = frozenset(
            "/v2/spaces/" + self.space + "/types/" + identity
            for identity in archive_type_keys
        )
        self.base = destination["api_base"]
        if self.base != "http://127.0.0.1:31009":
            raise ValueError("Unexpected API endpoint")
        credential = Path(destination["credential_file"])
        if credential.is_symlink() or not credential.is_file() or credential.stat().st_mode & 0o077:
            raise ValueError("Credential must be a private regular file")
        self.key = credential.read_text().strip()
        self.last_etag = None
        grant = self.request("GET", "/v2/auth/whoami")["grant"]
        spaces = self.request("GET", "/v2/spaces?ids=full")
        if grant.get("all_spaces") or not grant.get("restricted") or grant.get("permission") != "readwrite":
            raise ValueError("A channel-only read/write grant is required")
        if spaces.get("has_more") or len(spaces["data"]) != 1 or spaces["data"][0]["id"] != self.space:
            raise ValueError("Authenticated grant differs from the explicitly bound Space")

    def request(self, method, path, body=None, identity=None, etag=None, raw=None, content_type=None, binary=False):
        bootstrap = method == "GET" and (path in ("/v2/auth/whoami", "/v2/spaces?ids=full", "/v2/schemas") or path.startswith("/v2/schemas/"))
        scoped = path.startswith("/v2/spaces/" + self.space + "/")
        if not bootstrap and not scoped:
            raise ValueError("Request outside the migration's explicitly bound Space")
        owned_type_archive = method == "DELETE" and path.split("?", 1)[0] in getattr(self, "archive_type_paths", ()) and identity and etag
        if method not in ("GET", "POST", "PATCH") and not owned_type_archive:
            raise ValueError("Deletion is outside this transfer")
        headers = {"Authorization": "Bearer " + self.key,
                   "Content-Type": content_type or "application/json"}
        if identity:
            headers["Idempotency-Key"] = hashlib.sha256(identity.encode()).hexdigest()
        if etag:
            headers["If-Match"] = etag
        payload = raw if raw is not None else json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        for attempt in range(6):
            request = urllib.request.Request(self.base + path, data=payload, headers=headers, method=method)
            try:
                with urllib.request.build_opener(NoRedirect).open(request, timeout=90) as response:
                    self.last_etag = response.headers.get("ETag")
                    data = response.read()
                    return data if binary else json.loads(data)
            except urllib.error.HTTPError as error:
                detail = error.read().decode()
                if error.code == 429:
                    time.sleep(float(error.headers.get("Retry-After", 2 ** attempt)))
                    continue
                if error.code in (502, 503, 504) and (method == "GET" or identity):
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise RuntimeError(json.dumps({"status": error.code, "error": detail})) from None
            except urllib.error.URLError:
                if method != "GET" and not identity:
                    raise
                time.sleep(min(2 ** attempt, 10))
        raise RuntimeError("Anytype rate-limit retries exhausted")

    def scoped(self, method, suffix, body=None, **kwargs):
        return self.request(method, "/v2/spaces/" + self.space + "/" + suffix, body, **kwargs)
