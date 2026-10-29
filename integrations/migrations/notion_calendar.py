"""Retain the source start/end Date properties in timeline replacements."""
import json
from pathlib import Path
from notion_apply import Writer, resolve, hash_json
from notion_transform import Transform
from anytype_bound import atomic_json


def fix(config):
    w = Writer(config)
    plan = Transform(json.loads((w.state / "snapshot.json").read_text())).build()
    atomic_json(w.state / "corrected-transform.json", plan)
    count = 0
    for section in ["collections", "pages"]:
        for source, obj in plan[section].items():
            desired = resolve(obj, w.ledger, native_keys=True)
            definitions = [(i, b.get("_views") if section == "pages" else b.get("views")) for i, b in enumerate(desired["blocks"]) if b["type"] == "dataview"]
            relevant = [(i, j, v) for i, views in definitions for j, v in enumerate(views) if v["type"] == "calendar" and v.get("group_by")]
            if not relevant:
                continue
            target = w.ledger["objects"][source]["id"]
            actual = w.read(target, check_drift=True)
            ops = []
            for i, j, v in relevant:
                block = actual["blocks"][i]
                ops.append({"op": "update_view", "block": block["id"], "view": block["views"][j]["id"],
                            "set": {k: v[k] for k in ("group_by", "end_property") if k in v}})
                count += 1
            w.patch(target, "calendar-date-fields-v1:" + source, ops)
    w.ledger["calendar_dates"] = {"views": count, "transform_hash": hash_json(plan)}
    w.save()
    print(json.dumps(w.ledger["calendar_dates"]), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    fix(json.loads(args.config.read_text()))
