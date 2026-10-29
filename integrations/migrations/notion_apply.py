"""Apply the inspected migration only to its qualified Anytype channel.

Run on macOS through macctl. Private checkpoints make each creation and block
batch resumable; every write is read back. No Notion mutation or global setup.
"""
import argparse
from copy import deepcopy, copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import time
import threading
from urllib.parse import urlsplit
import urllib.request
import uuid

from anytype_bound import Client, atomic_json


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def content_hash(obj):
    meaningful = deepcopy(obj)
    for key in ("created_date", "creator", "last_modified_date", "last_modified_by", "last_opened_date", "last_opened_by"):
        meaningful.get("properties", {}).pop(key, None)
    for key in ("etag", "warnings", "_meta"):
        meaningful.pop(key, None)
    def strip_generated_view_ids(value, in_settings=False):
        if isinstance(value, dict):
            if in_settings:
                value.pop("id", None)
            for key, child in value.items():
                strip_generated_view_ids(child, in_settings or key in ("filters", "sorts"))
        elif isinstance(value, list):
            for child in value:
                strip_generated_view_ids(child, in_settings)
    strip_generated_view_ids(meaningful)
    return hash_json(meaningful)


def resolve(value, ledger, native_keys=False):
    if isinstance(value, list):
        return [resolve(v, ledger, native_keys) for v in value]
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            key = ledger.get("properties", {}).get(k, {}).get("key", k) if native_keys else k
            if native_keys and k == "type" and isinstance(v, str):
                v = ledger.get("types", {}).get(v, {}).get("key", v)
            elif native_keys and k in ("property", "group_by", "cover_property", "end_property") and isinstance(v, str):
                v = ledger.get("properties", {}).get(v, {}).get("key", v)
            result[key] = resolve(v, ledger, native_keys)
        return result
    if isinstance(value, str):
        def replacement(match):
            kind, identity = match.groups()
            section = "objects" if kind == "notion" else "assets"
            if identity not in ledger[section]:
                raise ValueError("Unresolved migration reference: " + match.group())
            return ledger[section][identity]["id"]
        return re.sub(r"\b(notion|asset):([a-zA-Z0-9-]+)", replacement, value)
    return value


class Writer:
    def __init__(self, config):
        self.lock = threading.RLock()
        self.config = config
        self.state = Path(config["state_directory"])
        self.plan = json.loads((self.state / "transform.json").read_text())
        if not self.plan.get("source_completed_at") or self.plan["source_errors"]:
            raise ValueError("A complete, error-free source snapshot is required")
        self.client = Client(config)
        self.ledger_path = self.state / "ledger.json"
        self.ledger = json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else {
            "space_id": self.client.space, "properties": {}, "types": {}, "objects": {}, "assets": {},
            "completed": {}, "operations": {}, "readbacks": {}}
        if self.ledger["space_id"] != self.client.space:
            raise ValueError("Checkpoint belongs to another Space")
        plan_hash = hash_json(self.plan)
        if self.ledger.get("plan_hash", plan_hash) != plan_hash:
            raise ValueError("Migration plan changed after application began")
        self.ledger["plan_hash"] = plan_hash
        self.save()

    def save(self):
        with self.lock:
            atomic_json(self.ledger_path, self.ledger)

    def read(self, identity, check_drift=False):
        obj = self.client.scoped("GET", "objects/" + identity + "?ids=full")
        previous = self.ledger["readbacks"].get(identity)
        previous_file = self.state / "readbacks" / (identity + ".json")
        if check_drift and previous and previous_file.exists():
            if content_hash(json.loads(previous_file.read_text())) != content_hash(obj):
                raise ValueError("Destination was edited since its last migration checkpoint: " + identity)
        with self.lock:
            self.ledger["readbacks"][identity] = {"hash": hash_json(obj), "etag": self.client.last_etag or obj.get("_meta", {}).get("etag"), "at": time.time()}
        atomic_json(self.state / "readbacks" / (identity + ".json"), obj)
        self.save()
        return obj

    def create(self, section, identity, suffix, body):
        if identity in self.ledger[section]:
            return self.ledger[section][identity]
        result = self.client.scoped("POST", suffix + "?ids=full", body, identity="kase:" + section + ":" + identity)
        with self.lock:
            self.ledger[section][identity] = result
            self.save()
        if result.get("id"):
            self.read(result["id"])
        return result

    def patch(self, identity, key, ops):
        if key in self.ledger["operations"]:
            return self.ledger["operations"][key]
        current = self.read(identity, check_drift=True)
        etag = self.ledger["readbacks"][identity]["etag"]
        body = {"ops": ops}
        # Dry-run uses the same concrete object references and installed schemas.
        self.client.scoped("PATCH", "objects/" + identity + "?dry_run=true&ids=full", body)
        result = self.client.scoped("PATCH", "objects/" + identity + "?ids=full", body,
                                    identity="kase:" + key, etag=etag)
        with self.lock:
            self.ledger["operations"][key] = result
            self.save()
        self.read(identity)
        return result

    def schema(self):
        for key, body in self.plan["properties"].items():
            self.create("properties", key, "properties", body)
        for key, body in self.plan["types"].items():
            self.create("types", key, "types", body)
        print(json.dumps({"stage": "schema", "properties": len(self.ledger["properties"]), "types": len(self.ledger["types"])}), flush=True)

    def assets(self):
        for i, (identity, asset) in enumerate(self.plan["assets"].items()):
            if identity in self.ledger["assets"]:
                self.verify_asset(identity)
                continue
            directory = self.state / "assets"
            directory.mkdir(mode=0o700, exist_ok=True)
            target = directory / identity
            if not target.exists():
                if urlsplit(asset["url"]).scheme != "https":
                    raise ValueError("Source attachment must use HTTPS")
                with urllib.request.urlopen(asset["url"], timeout=90) as response:
                    payload = response.read(128 * 1024 * 1024 + 1)
                    mime = response.headers.get_content_type()
                if len(payload) > 128 * 1024 * 1024:
                    raise ValueError("Attachment exceeds the reviewed upload size")
                target.write_bytes(payload)
                target.chmod(0o600)
                atomic_json(directory / (identity + ".json"), {"mime": mime, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload), "name": asset["name"]})
            payload = target.read_bytes()
            info = json.loads((directory / (identity + ".json")).read_text())
            boundary = "kasemigration" + identity
            filename = asset["name"].replace('"', "_").replace("\r", "_").replace("\n", "_")
            prefix = ("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename +
                      '"\r\nContent-Type: ' + info["mime"] + "\r\n\r\n").encode()
            raw = prefix + payload + ("\r\n--" + boundary + "--\r\n").encode()
            result = self.client.scoped("POST", "files?ids=full", identity="kase:asset:" + identity,
                                        raw=raw, content_type="multipart/form-data; boundary=" + boundary)
            # APIs may return the file in a wrapper; retain the full response.
            file_id = result.get("id") or result.get("file", {}).get("id")
            if not file_id:
                raise ValueError("File response did not identify the uploaded object")
            self.ledger["assets"][identity] = {"id": file_id, "sha256": info["sha256"], "size": info["size"], "response": result}
            self.save()
            self.read(file_id)
            self.verify_asset(identity)
            if i % 10 == 0:
                print(json.dumps({"stage": "assets", "uploaded": len(self.ledger["assets"]), "total": len(self.plan["assets"])}), flush=True)

    def verify_asset(self, identity):
        entry = self.ledger["assets"][identity]
        if entry.get("verified_sha256"):
            return
        data = self.client.scoped("GET", "files/" + entry["id"] + "/content?width=0", binary=True)
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry["sha256"]:
            info = json.loads((self.state / "assets" / (identity + ".json")).read_text())
            if not info["mime"].startswith("image/"):
                raise ValueError("Destination attachment bytes differ: " + identity)
            directory = self.state / "rendered-assets"
            directory.mkdir(mode=0o700, exist_ok=True)
            (directory / identity).write_bytes(data)
            entry["image_reencoded"] = True
            entry["visual_verification"] = "pending"
        entry["verified_sha256"] = actual
        self.save()

    def shells(self):
        for identity, obj in self.plan["collections"].items():
            initial = deepcopy(obj)
            initial["collection_items"] = []
            if "icon" in initial:
                initial["icon"] = resolve(initial["icon"], self.ledger)
            self.create("objects", identity, "objects", initial)
        for i, (identity, obj) in enumerate(self.plan["pages"].items()):
            properties = {k: v for k, v in obj["properties"].items() if k in ("name", "source", "notion_source_id", "notion_created_at", "notion_edited_at")}
            initial = {"formatVersion": "2.0", "type": obj["type"], "template": "none", "properties": properties, "blocks": []}
            for key in ("icon", "cover"):
                if key in obj:
                    initial[key] = resolve(obj[key], self.ledger)
            self.create("objects", identity, "objects", initial)
            if i % 50 == 0:
                print(json.dumps({"stage": "objects", "created": len(self.ledger["objects"]), "total": len(self.plan["pages"]) + len(self.plan["collections"])}), flush=True)

    def body(self, source_id, obj):
        target = self.ledger["objects"][source_id]["id"]
        if source_id in self.ledger["completed"]:
            return
        properties = resolve(obj["properties"], self.ledger)
        blocks = resolve(obj["blocks"], self.ledger)
        if not blocks:
            self.patch(target, "properties:" + source_id, [{"op": "set_properties", "set": properties}])
        stack, views, cursor = {}, [], 0
        while cursor < len(blocks):
            depth = blocks[cursor].get("indent", 0)
            end = cursor + 1
            while end < len(blocks) and end < cursor + 256 and blocks[end].get("indent", 0) >= depth:
                end += 1
            run = []
            for block in blocks[cursor:end]:
                item = {k: v for k, v in block.items() if k != "_views"}
                item["indent"] = item.get("indent", 0) - depth
                run.append(item)
            operation = {"op": "insert_blocks", "blocks": run}
            if depth:
                operation["inside"] = stack[depth - 1]
            ops = [{"op": "set_properties", "set": properties}, operation] if cursor == 0 else [operation]
            op_index = 1 if cursor == 0 else 0
            result = self.patch(target, "body:" + source_id + ":" + str(cursor), ops)
            minted = result.get("created_blocks", {})
            for offset, block in enumerate(blocks[cursor:end]):
                block_id = minted.get("ops[" + str(op_index) + "].blocks[" + str(offset) + "]")
                if not block_id:
                    raise ValueError("Missing destination block identity")
                level = block.get("indent", 0)
                stack = {k: v for k, v in stack.items() if k < level}
                stack[level] = block_id
                if block.get("_views"):
                    views.append((block_id, block["_views"]))
            cursor = end
        for block_id, source_views in views:
            current = self.read(target)
            view_block = next(v for v in current["blocks"] if v["id"] == block_id)
            existing = view_block.get("views", [])
            ops = []
            for i, source_view in enumerate(source_views):
                settings = {k: v for k, v in source_view.items() if k not in ("name", "columns")}
                columns = {v["property"]: {k: val for k, val in v.items() if k != "property"} for v in source_view.get("columns", [])}
                if i == 0 and existing:
                    operation = {"op": "update_view", "block": block_id, "view": existing[0]["id"], "set": {"name": source_view["name"], **settings}, "columns": columns}
                    for column in existing[0].get("columns", []):
                        if column["property"] not in columns:
                            operation["columns"][column["property"]] = None
                else:
                    operation = {"op": "insert_view", "block": block_id, "name": source_view["name"], "set": settings, "columns": columns}
                ops.append(operation)
            self.patch(target, "views:" + source_id + ":" + block_id, ops)
        with self.lock:
            self.ledger["completed"][source_id] = {"hash": hash_json(obj), "blocks": len(blocks)}
            self.save()

    def bodies(self):
        local = threading.local()
        def apply_page(item):
            if not hasattr(local, "writer"):
                local.writer = copy(self)
                local.writer.client = copy(self.client)
            local.writer.body(*item)
        with ThreadPoolExecutor(max_workers=3) as pool:
            for i, _ in enumerate(pool.map(apply_page, self.plan["pages"].items())):
                if i % 25 == 0:
                    print(json.dumps({"stage": "content", "verified": len(self.ledger["completed"]), "total": len(self.plan["pages"])}), flush=True)
        for identity, obj in self.plan["collections"].items():
            target = self.ledger["objects"][identity]["id"]
            items = resolve(obj["collection_items"], self.ledger)
            if items:
                self.patch(target, "membership:" + identity, [{"op": "add_items", "items": items}])
        print(json.dumps({"stage": "content-complete", "pages": len(self.ledger["completed"]), "collections": len(self.plan["collections"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--stage", choices=["schema", "assets", "objects", "content", "all"], required=True)
    args = parser.parse_args()
    os.umask(0o077)
    writer = Writer(json.loads(args.config.read_text()))
    for stage in ["schema", "assets", "objects", "content"] if args.stage == "all" else [args.stage]:
        {"schema": writer.schema, "assets": writer.assets, "objects": writer.shells, "content": writer.bodies}[stage]()
