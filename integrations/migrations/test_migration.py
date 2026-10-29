"""Offline checks for reference preservation, scope, and large nested pages."""
import unittest
import threading
from unittest.mock import Mock

from anytype_bound import Client
from notion_apply import Writer, resolve
from notion_transform import Transform


class MigrationTests(unittest.TestCase):
    def test_formatted_spans_keep_whitespace_outside_delimiters(self):
        t = Transform.__new__(Transform)
        t.warnings = []
        self.assertEqual(t.rich([{"type": "text", "plain_text": "Title \n", "annotations": {"bold": True}}]), "**Title** \n")

    def test_adjacent_bold_spans_keep_nested_code(self):
        t = Transform.__new__(Transform)
        t.warnings = []
        values = [{"type": "text", "plain_text": "tool", "annotations": {"bold": True, "code": True}},
                  {"type": "text", "plain_text": ".", "annotations": {"bold": True}}]
        self.assertEqual(t.rich(values), "**`tool`.**")

    def test_reference_rewriting_preserves_unrelated_urls(self):
        t = Transform.__new__(Transform)
        identity = "12345678-1234-1234-1234-123456789abc"
        t.known_compact = {identity.replace("-", ""): identity}
        t.s = {"databases": {}}
        self.assertEqual(t.url("https://www.notion.so/Title-" + identity.replace("-", "")),
                         "anytype://object?objectId=notion:" + identity)
        self.assertEqual(t.url("https://example.com/" + identity), "https://example.com/" + identity)

    def test_bound_client_rejects_foreign_and_delete_before_transport(self):
        c = Client.__new__(Client)
        c.space = "kase"
        with self.assertRaises(ValueError):
            c.request("GET", "/v2/spaces/foreign/objects")
        with self.assertRaises(ValueError):
            c.request("DELETE", "/v2/spaces/kase/objects/example")

    def test_type_cleanup_cannot_archive_objects_other_types_or_without_preconditions(self):
        c = Client.__new__(Client)
        c.space = "kase"
        c.archive_type_paths = frozenset(["/v2/spaces/kase/types/owned_type"])
        for path, identity, etag in [
            ("/v2/spaces/kase/objects/example", "cleanup", "revision"),
            ("/v2/spaces/kase/types/page", "cleanup", "revision"),
            ("/v2/spaces/foreign/types/owned_type", "cleanup", "revision"),
            ("/v2/spaces/kase/types/owned_type", None, "revision"),
            ("/v2/spaces/kase/types/owned_type", "cleanup", None),
        ]:
            with self.subTest(path=path, identity=identity, etag=etag), self.assertRaises(ValueError):
                c.request("DELETE", path, identity=identity, etag=etag)

    def test_cycles_can_resolve_after_shell_creation(self):
        ledger = {"objects": {"a": {"id": "A"}, "b": {"id": "B"}}, "assets": {}}
        self.assertEqual(resolve({"a": ["notion:b"], "b": ["notion:a"]}, ledger), {"a": ["B"], "b": ["A"]})

    def test_large_nested_page_keeps_parent_and_sibling_order(self):
        w = Writer.__new__(Writer)
        w.lock = threading.RLock()
        w.ledger = {"objects": {"source": {"id": "destination"}}, "assets": {}, "completed": {}}
        w.save = Mock()
        actual, parents, stack = [], {}, {}
        def patch(identity, key, ops):
            indexes = [i for i, op in enumerate(ops) if op["op"] == "insert_blocks"]
            if not indexes:
                return {}
            index = indexes[0]
            op = ops[index]
            base = parents[op["inside"]] + 1 if "inside" in op else 0
            minted = {}
            for i, block in enumerate(op["blocks"]):
                block_id = str(len(actual))
                level = base + block.get("indent", 0)
                actual.append((block["text"], level))
                parents[block_id] = level
                minted[f"ops[{index}].blocks[{i}]"] = block_id
            return {"created_blocks": minted}
        w.patch = patch
        blocks = [{"type": "row", "text": "row", "indent": 0}, {"type": "column", "text": "left", "indent": 1}]
        blocks += [{"type": "paragraph", "text": str(i), "indent": 2} for i in range(520)]
        blocks += [{"type": "column", "text": "right", "indent": 1}, {"type": "paragraph", "text": "end", "indent": 2},
                   {"type": "paragraph", "text": "outside", "indent": 0}]
        w.body("source", {"properties": {}, "blocks": blocks})
        self.assertEqual(actual, [(b["text"], b["indent"]) for b in blocks])


if __name__ == "__main__":
    unittest.main()
