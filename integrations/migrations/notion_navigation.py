"""Expose the three entry points and byte-exact original backups in kase."""
import hashlib
import json
from pathlib import Path

from notion_apply import Writer
from anytype_bound import atomic_json


def finish(config):
    w = Writer(config)
    if len(w.ledger["completed"]) != len(w.plan["pages"]):
        raise ValueError("Navigation follows completed content transfer")
    w.ledger.setdefault("preservation", {})
    w.ledger.setdefault("navigation", {})
    archives = json.loads((w.state / "preservation" / "manifest.json").read_text())
    for item in archives:
        identity = item["sha256"]
        if w.ledger["preservation"].get(identity, {}).get("verified"):
            continue
        if identity not in w.ledger["preservation"]:
            payload = Path(item["path"]).read_bytes()
            boundary = "kaseoriginal" + identity
            raw = ("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + item["name"] +
                   '"\r\nContent-Type: application/zip\r\n\r\n').encode() + payload + ("\r\n--" + boundary + "--\r\n").encode()
            result = w.client.scoped("POST", "files?ids=full", raw=raw,
                                    content_type="multipart/form-data; boundary=" + boundary,
                                    identity="kase:preservation:" + identity)
            target = result.get("id") or result.get("file", {}).get("id")
            w.ledger["preservation"][identity] = {"id": target, "name": item["name"], "sha256": identity}
            w.save()
        target = w.ledger["preservation"][identity]["id"]
        w.read(target)
        actual = w.client.scoped("GET", "files/" + target + "/content", binary=True)
        if hashlib.sha256(actual).hexdigest() != identity:
            raise ValueError("Original archive differs after upload")
        w.ledger["preservation"][identity]["verified"] = True
        w.save()
    snapshot = json.loads((w.state / "snapshot.json").read_text())
    formulas = []
    for source_id, source in snapshot["data_sources"].items():
        entries = [(name, prop["formula"]["expression"]) for name, prop in source.get("properties", {}).items() if prop["type"] == "formula"]
        if entries:
            formulas.append({"type": "link", "object_id": w.ledger["objects"][source_id]["id"]})
            for name, expression in entries:
                formulas.extend([{"type": "heading_3", "text": name}, {"type": "code", "language": "plain text", "text": expression}])
    formula_id = None
    if formulas:
        formula_id = w.create("navigation", "formulas", "objects", {"formatVersion": "2.0", "type": "page", "template": "none",
                             "properties": {"name": "Formula definitions"}, "blocks": formulas})["id"]
    archive = {"formatVersion": "2.0", "type": "page", "template": "none",
               "properties": {"name": "Original files", "description": "Original attachments and source structure retained from Notion."},
               "blocks": [{"type": "file", "object_id": v["id"]} for v in w.ledger["preservation"].values()]}
    if formula_id:
        archive["blocks"].extend([{"type": "divider"}, {"type": "link", "object_id": formula_id}])
    archive_id = w.create("navigation", "originals", "objects", archive)["id"]
    roots = [w.ledger["objects"][i]["id"] for i in ["29b99dce-f499-8042-8e5c-c9f0639303c1", "37599dce-f499-8065-bd60-f1a586a5744c", "2e099dce-f499-8086-a586-000b83a0ce5a"]]
    home = {"formatVersion": "2.0", "type": "page", "template": "none", "properties": {"name": "kase"},
            "blocks": [{"type": "link", "object_id": i} for i in roots] +
                      [{"type": "divider"}, {"type": "link", "object_id": archive_id}]}
    home_id = w.create("navigation", "home", "objects", home)["id"]
    w.ledger.setdefault("widgets", {})
    for i, target in enumerate([home_id] + roots):
        if target in w.ledger["widgets"]:
            continue
        result = w.client.scoped("POST", "widgets", {"target": target, "scope": "space", "layout": "link", "position": "first" if i == 0 else "last"},
                                 identity="kase:widget:" + target)
        w.ledger["widgets"][target] = result
        w.save()
        readback = w.client.scoped("GET", "widgets?ids=full")
        atomic_json(w.state / "widgets-readback.json", readback)
        if target not in json.dumps(readback):
            raise ValueError("Navigation widget was not read back")
    print(json.dumps({"home_id": home_id, "root_ids": roots, "original_archives": len(archives)}), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    finish(json.loads(args.config.read_text()))
