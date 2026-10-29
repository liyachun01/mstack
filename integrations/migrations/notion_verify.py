"""Compare migrated native documents against the inspected transformation."""
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
try:
    from markdown_it import MarkdownIt
    MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("strikethrough")
except ImportError:
    MARKDOWN = None

from anytype_bound import Client, atomic_json
from notion_apply import resolve


def equal_value(a, b):
    if a == b:
        return True
    if a is None and b in (None, "", []):
        return True
    if isinstance(a, str) and isinstance(b, str):
        try:
            def date(value):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc) if not dt.tzinfo else dt.astimezone(timezone.utc)
            return date(a) == date(b)
        except ValueError:
            pass
    return False


def compare(expected, actual, path, issues):
    if isinstance(expected, dict):
        for key, value in expected.items():
            if key in ("_views", "template", "formatVersion"):
                continue
            default = {"indent": 0, "hidden": False, "checked": False, "is_header": False,
                       "sorts": [], "filters": [], "type": "table", "direction": "asc", "width": 200}.get(key)
            compare(value, actual.get(key, default) if isinstance(actual, dict) else None, path + [key], issues)
    elif isinstance(expected, list):
        if path and path[-1] == "cells" and actual is None:
            actual = []
        if not expected and path and path[-1] == "columns" and isinstance(actual, list) and all(v.get("property") == "name" or v.get("hidden") is True for v in actual):
            return
        if not expected and actual is None:
            return
        if isinstance(actual, list) and path and path[-1] == "cells" and len(actual) < len(expected) and all(v == "" for v in expected[len(actual):]):
            actual = actual + [""] * (len(expected) - len(actual))
        if not isinstance(actual, list) or len(expected) != len(actual):
            issues.append({"path": path, "expected_count": len(expected), "actual_count": len(actual) if isinstance(actual, list) else None})
        else:
            for i, (a, b) in enumerate(zip(expected, actual)):
                compare(a, b, path + [i], issues)
    elif actual is None and (expected == "" or expected is False):
        return
    elif isinstance(expected, str) and isinstance(actual, str) and MARKDOWN and (path[-1] == "text" or "cells" in path) and MARKDOWN.renderInline(expected) == MARKDOWN.renderInline(actual):
        return
    elif not equal_value(expected, actual):
        issues.append({"path": path, "expected": expected, "actual": actual})


def verify(config, offline=False):
    state = Path(config["state_directory"])
    plan = json.loads((state / ("corrected-transform.json" if (state / "corrected-transform.json").exists() else "transform.json")).read_text())
    ledger = json.loads((state / "ledger.json").read_text())
    client, local = None if offline else Client(config), threading.local()
    all_issues = {}
    def one(item):
        source, expected = item
        if not offline and not hasattr(local, "client"):
            local.client = copy(client)
        if offline:
            obj = json.loads((state / "final-readbacks" / (source + ".json")).read_text())
        else:
            obj = local.client.scoped("GET", "objects/" + ledger["objects"][source]["id"] + "?ids=full")
            atomic_json(state / "final-readbacks" / (source + ".json"), obj)
        desired = resolve(expected, ledger, native_keys=True)
        for block in desired.get("blocks", []):
            if block.get("_views"):
                block["views"] = block.pop("_views")
        desired.pop("template", None)
        desired["blocks"] = desired.get("blocks", [])
        obj.setdefault("blocks", [])
        obj.setdefault("collection_items", [])
        issues = []
        compare(desired, obj, [], issues)
        return source, issues
    items = {**plan["pages"], **plan["collections"]}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, (source, issues) in enumerate(pool.map(one, items.items()), 1):
            if issues:
                all_issues[source] = issues
            if i % 100 == 0:
                print(json.dumps({"verified_objects": i, "objects_with_differences": len(all_issues)}), flush=True)
    atomic_json(state / "verification-differences.json", all_issues)
    result = {"objects": len(items), "pages": len(plan["pages"]), "collections": len(plan["collections"]),
              "native_content_blocks": sum(len(p["blocks"]) for p in plan["pages"].values()),
              "collection_memberships": sum(len(p["collection_items"]) for p in plan["collections"].values()),
              "objects_with_differences": len(all_issues), "differences": sum(len(v) for v in all_issues.values())}
    atomic_json(state / "verification-summary.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    verify(json.loads(args.config.read_text()), args.offline)
