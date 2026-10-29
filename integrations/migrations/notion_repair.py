"""Correct observed Markdown and full-document view import differences."""
import json
from pathlib import Path
from notion_apply import Writer, resolve, hash_json
from notion_transform import Transform
from anytype_bound import atomic_json


def repair(config, revision):
    w = Writer(config)
    corrected = Transform(json.loads((w.state / "snapshot.json").read_text())).build()
    atomic_json(w.state / "corrected-transform.json", corrected)
    total = 0
    for source, desired in corrected["pages"].items():
        original = w.plan["pages"][source]
        edits = [(i, a, b) for i, (a, b) in enumerate(zip(original["blocks"], desired["blocks"]))
                 if a.get("text") != b.get("text") or a.get("rows") != b.get("rows")]
        if not edits:
            continue
        target = w.ledger["objects"][source]["id"]
        actual = w.read(target, check_drift=True)
        ops = []
        for i, old, new in edits:
            native = actual["blocks"][i]
            if new["type"] == "table":
                for row, (a, b) in enumerate(zip(old["rows"], new["rows"])):
                    for col, (left, right) in enumerate(zip(a["cells"], b["cells"])):
                        if left != right:
                            ops.append({"op": "set_cell", "table_id": native["id"], "row": native["rows"][row]["id"],
                                        "col": native["columns"][col]["id"], "value": resolve(right, w.ledger)})
            else:
                ops.append({"op": "update_block", "id": native["id"], "set": {"text": resolve(new["text"], w.ledger)}})
        if ops:
            w.patch(target, "rich-text-correction-" + revision + ":" + source, ops)
            total += len(ops)
    for source, desired in corrected["collections"].items():
        target = w.ledger["objects"][source]["id"]
        actual = w.read(target, check_drift=True)
        block = actual["blocks"][0]
        views = resolve(desired["blocks"][0]["views"], w.ledger, native_keys=True)
        ops = []
        for old, v in zip(block["views"], views):
            if not v.get("columns"):
                continue
            first = v["columns"][0]
            ops.append({"op": "update_view", "block": block["id"], "view": old["id"],
                        "columns": {first["property"]: {k: value for k, value in first.items() if k != "property"}}})
            removals = {c["property"]: None for c in old.get("columns", []) if c["property"] != first["property"]}
            if removals:
                ops.append({"op": "update_view", "block": block["id"], "view": old["id"], "columns": removals})
            for c in v["columns"][1:]:
                ops.append({"op": "update_view", "block": block["id"], "view": old["id"],
                            "columns": {c["property"]: {k: value for k, value in c.items() if k != "property"}}})
        if ops:
            w.patch(target, "collection-column-order-" + revision + ":" + source, ops)
    w.ledger["corrections"] = {"transform_hash": hash_json(corrected), "rich_text_operations": total, "collection_views": len(corrected["collections"])}
    w.save()
    print(json.dumps(w.ledger["corrections"]), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    repair(json.loads(args.config.read_text()), args.revision)
