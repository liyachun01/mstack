import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "inventory.py"
spec = importlib.util.spec_from_file_location("toolchain_inventory", SOURCE)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class PrivacyTests(unittest.TestCase):
    def test_script_identifiers_omit_secret_arguments(self):
        self.assertEqual(inventory.safe_process_identifier([
            "node", "/safe/pyright-langserver.js", "--token", "VERY_SECRET",
            "https://user:password@example.com/api?key=SECRET"]), "pyright-language-server")
        self.assertEqual(inventory.safe_process_identifier([
            "python", "-m", "headroom.server", "--password=SECRET"]), "module:headroom")
        self.assertEqual(inventory.safe_process_identifier([
            "python", "-m", "headroom.SECRET_PRIVATE_IDENTIFIER"]), "module:headroom")

    def test_eval_unknown_scripts_urls_and_inline_tokens_not_exposed(self):
        for argv in (["node", "-e", "console.log('SECRET')"],
                     ["python", "-c", "SECRET", "headroom"],
                     ["node", "/private/SECRET.js"],
                     ["python", "-m", "SECRET"],
                     ["node", "https://example.com/pyright-langserver.js?token=SECRET"],
                     ["node", "--token=SECRET", "SECRET", "pyright-langserver.js"],
                     ["node", "--", "SECRET", "pyright-langserver.js"]):
            with self.subTest(argv=argv):
                self.assertIsNone(inventory.safe_process_identifier(argv))

    def test_shell_inventory_reports_only_hashes_and_line_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            repo = Path(directory) / "repo"
            home.mkdir()
            repo.mkdir()
            (home / ".zshrc").write_text("export SECRET=not-public\n# fnm old\neval \"$(fnm env)\"\nexport BUN_INSTALL=x\n")
            (home / "arbitrary-secret").write_text("do-not-read")
            result = inventory.config_inventory(home, repo)
            serialized = json.dumps(result)
            self.assertNotIn("not-public", serialized)
            self.assertNotIn("do-not-read", serialized)
            self.assertNotIn("arbitrary-secret", serialized)
            self.assertEqual(result[0]["toolchain_lines"], {"fnm": [3], "bun": [4]})
            self.assertEqual(len(result[0]["sha256"]), 64)

    def test_symlink_does_not_escape_named_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "store"
            outside = Path(directory) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "package.json").write_text('{"name":"npm","version":"1.2.3"}')
            (root / "leak").symlink_to(outside, target_is_directory=True)
            self.assertEqual(inventory.child_dirs(root, root), [])
            self.assertIsNone(inventory.bounded_read(root / "leak/package.json", root))

    def test_manifests_never_return_arbitrary_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "lib/node_modules/npm/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"name":"npm","version":"11.17.0","_authToken":"SECRET"}')
            data = inventory.node_manifests(root, root)
            self.assertEqual(data[0]["version"], "11.17.0")
            self.assertNotIn("SECRET", json.dumps(data))

    def test_secret_symlink_is_not_hashed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home, repo = root / "home", root / "repo"
            home.mkdir()
            repo.mkdir()
            secret = home / ".secrets/key"
            secret.parent.mkdir()
            secret.write_text("do-not-hash")
            (home / ".zshrc").symlink_to(secret)
            data = inventory.config_inventory(home, repo)
            self.assertFalse(any(x["path"] == str(home / ".zshrc") for x in data))

    def test_process_record_never_serializes_argv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc = root / "123"
            proc.mkdir()
            (proc / "exe").symlink_to("/usr/bin/node")
            (proc / "cwd").symlink_to(root)
            fields = ["S"] + ["0"] * 21
            fields[19] = "1234"
            (proc / "stat").write_text("123 (private comm) " + " ".join(fields))
            (proc / "cmdline").write_bytes(b"node\0/safe/pyright-langserver.js\0--token=VERY_SECRET\0")
            result = inventory.process_record(proc)
            self.assertEqual(result["identifier"], "pyright-language-server")
            self.assertEqual(result["start_ticks"], 1234)
            self.assertNotIn("VERY_SECRET", json.dumps(result))
            self.assertNotIn("private comm", json.dumps(result))


class OutputTests(unittest.TestCase):
    def test_output_rejects_escape_and_group_readable_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "private"
            root.mkdir(mode=0o700)
            with self.assertRaises(ValueError):
                inventory.write_output(root / "../outside.json", {}, root=root)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                inventory.write_output(root / "inside.json", {}, root=root)

    def test_output_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inventory.write_output(root / "before.json", {"safe": True}, root=root)
            self.assertEqual((root / "before.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads((root / "before.json").read_text()), {"safe": True})
            self.assertEqual([p.name for p in root.iterdir()], ["before.json"])


if __name__ == "__main__":
    unittest.main()
