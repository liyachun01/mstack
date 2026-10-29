"""Preserve column order and visibility in collection and embedded views."""
import json
from pathlib import Path
from notion_apply import Writer, resolve


def view_ops(block, desired):
    ops = []
    for old, view in zip(block["views"], desired):
        base = {"op": "update_view", "block": block["id"], "view": old["id"]}
        columns = view.get("columns", [])
        if not columns:
            visibility = {c["property"]: {"hidden": c["property"] != "name"} for c in old.get("columns", [])}
            visibility["name"] = {"hidden": False}
            ops.append({**base, "columns": visibility})
            continue
        first = columns[0]
        settings = {k: value for k, value in first.items() if k != "property"}
        settings.setdefault("hidden", False)
        ops.append({**base, "columns": {first["property"]: settings}})
        removals = {c["property"]: None for c in old.get("columns", []) if c["property"] != first["property"]}
        if removals:
            ops.append({**base, "columns": removals})
        for column in columns[1:]:
            settings = {k: value for k, value in column.items() if k != "property"}
            settings.setdefault("hidden", False)
            ops.append({**base, "columns": {column["property"]: settings}})
    return ops


def fix(config):
    w = Writer(config)
    plan = json.loads((w.state / "corrected-transform.json").read_text())
    count = 0
    for section in ["collections", "pages"]:
        for source, original in plan[section].items():
            desired = resolve(original, w.ledger, native_keys=True)
            views = [(i, b.get("_views") if section == "pages" else b.get("views")) for i, b in enumerate(desired["blocks"]) if b["type"] == "dataview"]
            if not views:
                continue
            target = w.ledger["objects"][source]["id"]
            actual = w.read(target, check_drift=True)
            ops = []
            for i, definitions in views:
                if len(actual["blocks"][i].get("views", [])) != len(definitions):
                    raise ValueError("Unexpected view count: " + source)
                ops.extend(view_ops(actual["blocks"][i], definitions))
            w.patch(target, "all-view-columns-v3:" + source, ops)
            count += 1
    w.ledger["view_columns_verified"] = {"objects": count}
    w.save()
    print(json.dumps(w.ledger["view_columns_verified"]), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    fix(json.loads(args.config.read_text()))
