"""Keep new collection rows on their migrated source-specific Anytype type."""
import json
from pathlib import Path
from notion_apply import Writer
from notion_transform import digest


def defaults(config):
    w = Writer(config)
    sources = set(w.plan["collections"])
    target_sources = {w.ledger["objects"][s]["id"]: s for s in sources}
    changed = 0
    for source in list(w.plan["collections"]) + list(w.plan["pages"]):
        target = w.ledger["objects"][source]["id"]
        if source not in sources and not any(b["type"] == "dataview" for b in w.plan["pages"][source]["blocks"]):
            continue
        actual = w.read(target, check_drift=True)
        ops = []
        for block in actual.get("blocks", []):
            if block["type"] != "dataview":
                continue
            table_source = source if source in sources else target_sources.get(block.get("object_id"))
            if table_source:
                typ = w.ledger["types"]["ntn_" + digest(table_source)]["id"]
                ops.extend({"op": "update_view", "block": block["id"], "view": v["id"], "set": {"default_type_id": typ}}
                           for v in block.get("views", []))
        if ops:
            w.patch(target, "row-type-defaults-v1:" + source, ops)
            changed += 1
    w.ledger["row_type_defaults"] = {"objects": changed}
    w.save()
    print(json.dumps(w.ledger["row_type_defaults"]), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    defaults(json.loads(args.config.read_text()))
