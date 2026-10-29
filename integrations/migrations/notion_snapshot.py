"""Read a bounded Notion tree using the owner's authenticated macOS ntn CLI.

No token extraction, Notion writes, dependency installation or destination writes.
Snapshots contain private source documents and must live in ignored state storage.
"""
import argparse
import concurrent.futures
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from urllib.parse import quote

VERSION = "2026-03-11"
ROOTS = [("page", "29b99dce-f499-8042-8e5c-c9f0639303c1"),
         ("page", "37599dce-f499-8065-bd60-f1a586a5744c"),
         ("database", "2e099dce-f499-8074-a7d3-f5a254cf18ee")]


def title(obj):
    if isinstance(obj.get("title"), list):
        return "".join(t.get("plain_text", t.get("text", {}).get("content", "")) for t in obj["title"])
    return "".join(t.get("plain_text", "") for p in obj.get("properties", {}).values()
                   if p.get("type") == "title" for t in p["title"])


class Reader:
    def __init__(self, root):
        self.root = root
        self.cache = root / "responses"
        self.cache.mkdir(parents=True, exist_ok=True, mode=0o700)

    def call(self, method, path, body=None, query=None):
        if not (method == "GET" or (method == "POST" and
                (path == "v1/search" or path.endswith("/query")))):
            raise ValueError("Source reader refuses mutation")
        identity = json.dumps([VERSION, method, path, body, query], sort_keys=True)
        target = self.cache / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
        if target.exists():
            return json.loads(target.read_text())
        argv = ["ntn", "api", path, "-X", method, "--notion-version", VERSION]
        if body is not None:
            argv.extend(["--data", json.dumps(body)])
        argv.extend(k + "==" + str(v) for k, v in (query or {}).items())
        for attempt in range(5):
            result = subprocess.run(["macctl", "run", "zsh", "-lc", shlex.join(argv)],
                                    capture_output=True, text=True, timeout=90)
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError:
                response = {"object": "error", "message": result.stderr[:1000]}
            if result.returncode == 0 and response.get("object") != "error":
                target.write_text(json.dumps(response, ensure_ascii=False, indent=2))
                target.chmod(0o600)
                return response
            if "429" not in result.stderr and "rate_limit" not in str(response):
                raise RuntimeError(json.dumps(response))
            time.sleep(2 ** attempt)
        raise RuntimeError("Notion rate-limit retries exhausted")

    def listing(self, method, path, body=None, query=None):
        values, cursor, seen = [], None, set()
        while True:
            b, q = dict(body or {}), dict(query or {})
            args = b if method == "POST" else q
            args["page_size"] = 100
            if cursor:
                args["start_cursor"] = cursor
            response = self.call(method, path, b if method == "POST" else None, q)
            values.extend(response["results"])
            if not response.get("has_more"):
                return values
            cursor = response.get("next_cursor")
            if not cursor or cursor in seen:
                raise RuntimeError("Invalid pagination cursor")
            seen.add(cursor)


def fetch_item(reader, kind, identity):
    data = {key: {} for key in ["pages", "databases", "data_sources", "blocks", "children", "rows", "views", "property_items"]}
    data["errors"] = []
    queue = deque()
    try:
        fetch_one(reader, data, queue, kind, identity)
    except RuntimeError as exc:
        data["errors"].append({"kind": kind, "id": identity, "error": str(exc)})
    return data, queue


def fetch_one(reader, data, queue, kind, identity):
    if kind == "page":
        obj = reader.call("GET", "v1/pages/" + identity)
        data["pages"][identity] = obj
        for name, prop in obj.get("properties", {}).items():
            if prop.get("has_more") or prop.get("type") in ("relation", "rollup") or (prop.get("type") in ("rich_text", "title") and len(prop.get(prop["type"], [])) >= 25):
                endpoint = "v1/pages/" + identity + "/properties/" + quote(prop["id"], safe="%")
                first = reader.call("GET", endpoint, query={"page_size": 100})
                data["property_items"][identity + ":" + name] = reader.listing("GET", endpoint) if first.get("object") == "list" else first
        queue.append(("children", identity))
    elif kind == "database":
        obj = reader.call("GET", "v1/databases/" + identity)
        data["databases"][identity] = obj
        queue.extend(("data_source", source["id"]) for source in obj.get("data_sources", []))
        try:
            for view in reader.listing("GET", "v1/views", query={"database_id": identity}):
                data["views"][view["id"]] = reader.call("GET", "v1/views/" + view["id"])
                source_id = data["views"][view["id"]].get("data_source_id")
                if source_id:
                    queue.append(("data_source", source_id))
        except RuntimeError as exc:
            data["errors"].append({"kind": "views", "id": identity, "error": str(exc)})
    elif kind == "data_source":
        data["data_sources"][identity] = reader.call("GET", "v1/data_sources/" + identity)
        rows = reader.listing("POST", "v1/data_sources/" + identity + "/query")
        data["rows"][identity] = [row["id"] for row in rows]
        queue.extend(("page", row["id"]) for row in rows)
    elif kind == "children":
        children = reader.listing("GET", "v1/blocks/" + identity + "/children")
        data["children"][identity] = [block["id"] for block in children]
        for block in children:
            data["blocks"][block["id"]] = block
            t = block["type"]
            if t in ("child_page", "child_database"):
                queue.append(("page" if t == "child_page" else "database", block["id"]))
            elif t == "synced_block" and block[t].get("synced_from"):
                queue.append(("children", block[t]["synced_from"]["block_id"]))
            elif block.get("has_children"):
                queue.append(("children", block["id"]))


def snapshot(reader):
    data = {"version": 1, "api_version": VERSION, "started_at": datetime.now(timezone.utc).isoformat(),
            "roots": ROOTS, "pages": {}, "databases": {}, "data_sources": {},
            "blocks": {}, "children": {}, "rows": {}, "views": {}, "property_items": {}, "errors": []}
    queue, seen = deque(ROOTS), set()
    target = reader.root / "snapshot.json"
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
      while queue:
        batch = []
        while queue and len(batch) < 3:
            item = queue.popleft()
            if item not in seen:
                seen.add(item)
                batch.append(executor.submit(fetch_item, reader, *item))
        for future in batch:
            additions, pending = future.result()
            for key, value in additions.items():
                if key == "errors":
                    data[key].extend(value)
                else:
                    data[key].update(value)
            queue.extend(pending)
        if len(seen) % 20 < 3:
            print(json.dumps({"processed": len(seen), "pending": len(queue), "pages": len(data["pages"]),
                              "blocks": len(data["blocks"]), "errors": len(data["errors"])}), flush=True)
        # Persist a recoverable checkpoint throughout the bounded traversal.
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        target.chmod(0o600)
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(json.dumps({"complete": True, "pages": len(data["pages"]), "databases": len(data["databases"]),
                      "data_sources": len(data["data_sources"]), "blocks": len(data["blocks"]),
                      "block_types": Counter(b["type"] for b in data["blocks"].values()),
                      "errors": data["errors"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.state.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot(Reader(args.state))
