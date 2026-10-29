"""Back up source attachments; renew expired URLs with the authenticated CLI."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlsplit, urlunsplit, quote

from anytype_bound import atomic_json
from notion_snapshot import Reader
from notion_transform import digest


def urls(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "url" and isinstance(child, str) and child.startswith("https://"):
                yield child
            else:
                yield from urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from urls(child)


def asset_id(url):
    p = urlsplit(url)
    return digest(p.scheme + "://" + p.netloc + p.path)


def backup(state):
    plan = json.loads((state / "transform.json").read_text())
    snapshot = json.loads((state / "snapshot.json").read_text())
    owners = {}
    for section, endpoint in [("pages", "pages"), ("blocks", "blocks"), ("data_sources", "data_sources")]:
        for identity, obj in snapshot[section].items():
            for url in urls(obj):
                owners[asset_id(url)] = "v1/" + endpoint + "/" + identity
    directory = state / "assets"
    directory.mkdir(mode=0o700, exist_ok=True)
    reader = Reader(state / "url-renewals")

    def fetch(item):
        identity, asset = item
        target = directory / identity
        if target.exists():
            return
        url = asset["url"]
        if url.startswith("https://app.notion.com/images/"):
            url = url.replace("https://app.notion.com/", "https://www.notion.so/", 1)
        for attempt in range(2):
            p = urlsplit(url)
            if p.scheme != "https":
                raise ValueError("Attachment requires HTTPS")
            url = urlunsplit((p.scheme, p.netloc, quote(p.path, safe="/%:@"), p.query, p.fragment))
            try:
                with urllib.request.urlopen(url, timeout=90) as response:
                    payload = response.read(128 * 1024 * 1024 + 1)
                    mime = response.headers.get_content_type()
                break
            except urllib.error.HTTPError as exc:
                if attempt or exc.code not in (400, 403):
                    raise RuntimeError("Attachment fetch failed: " + identity + " HTTP " + str(exc.code)) from None
                refreshed = reader.call("GET", owners[identity])
                candidates = [u for u in urls(refreshed) if asset_id(u) == identity]
                if not candidates:
                    raise RuntimeError("Source attachment URL is no longer available: " + identity)
                url = candidates[0]
        if len(payload) > 128 * 1024 * 1024:
            raise ValueError("Attachment exceeds 128 MiB")
        target.write_bytes(payload)
        target.chmod(0o600)
        atomic_json(directory / (identity + ".json"), {"mime": mime, "size": len(payload), "name": asset["name"],
                    "sha256": hashlib.sha256(payload).hexdigest()})

    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, _ in enumerate(pool.map(fetch, plan["assets"].items()), 1):
            if i % 10 == 0:
                print(json.dumps({"attachments_backed_up": i, "total": len(plan["assets"])}), flush=True)
    print(json.dumps({"attachments_backed_up": len(plan["assets"]), "complete": True}), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    backup(args.state)
