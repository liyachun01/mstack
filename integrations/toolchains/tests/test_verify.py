import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "verify.py"
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location("toolchain_verify", SOURCE)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)
TEST_GIT = Path(os.environ.get("MCP_STACK_TEST_GIT", "/usr/bin/git"))
TEST_LFS_DIR = Path(os.environ.get("MCP_STACK_TEST_LFS_DIR", "/usr/bin"))


class VerificationContractTests(unittest.TestCase):
    def test_private_environment_does_not_inherit_credentials_or_runtime_hooks(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "SECRET", "NODE_OPTIONS": "--require /private/module", "PATH": "/untrusted",
            "GIT_CONFIG_GLOBAL": "/private/config", "PYTHONPATH": "/private/python", "HTTP_PROXY": "SECRET",
        }):
            env = verify.isolated_environment(Path(directory) / "home", [Path("/managed/bin")])
            for name in ("DEEPSEEK_API_KEY", "NODE_OPTIONS", "PYTHONPATH", "HTTP_PROXY"):
                self.assertNotIn(name, env)
            self.assertEqual(env["PATH"], "/managed/bin:/usr/bin:/bin")
            self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
            self.assertEqual(env["COREPACK_ENABLE_NETWORK"], "0")

    def test_no_runtime_is_selected_by_common_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / verify.CONFIGS[0]
            config.parent.mkdir(parents=True)
            config.write_text('[tools]\nnode = "24.19.0"\n')
            with self.assertRaisesRegex(ValueError, "common baseline"):
                verify.read_declarations(root)

    def test_no_floating_versions_or_unapproved_probes(self):
        for tool, version in (("bun", "latest"), ("npm:unknown-cloud-cli", "1.2.3")):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for relative in verify.CONFIGS:
                    config = root / relative
                    config.parent.mkdir(parents=True, exist_ok=True)
                    config.write_text('[tools]\n')
                (root / verify.CONFIGS[0]).write_text('[tools]\n"' + tool + '" = "' + version + '"\n')
                with self.assertRaises(ValueError):
                    verify.read_declarations(root)

    def test_dsh_metadata_probe_does_not_start_profile_or_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            manifest = prefix / "lib/node_modules/@deepseek-ai/dsh/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"name": "@deepseek-ai/dsh", "version": "0.2.0-rc.2", "secret": "SECRET"}))
            entry = {"tool": "npm:@deepseek-ai/dsh", "binary": "dsh", "version": "0.2.0-rc.2", "prefix": str(prefix)}
            with patch.object(verify.subprocess, "run", side_effect=AssertionError("must not start dsh")):
                result = verify.probe_version(entry, {}, prefix)
            self.assertEqual(result["observed_version"], "0.2.0-rc.2")
            self.assertNotIn("SECRET", json.dumps(result))

    def test_binary_symlink_cannot_escape_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin").mkdir()
            (root / "bin/git").symlink_to("/usr/bin/git")
            with self.assertRaises(ValueError):
                verify.find_binary(root, "git")

    def test_exact_mise_binary_resolver_supports_nested_archive_and_aube(self):
        for tool, binary, relative in (
            ("aqua:git-lfs/git-lfs", "git-lfs", "git-lfs-3.7.1/git-lfs"),
            ("npm:@deepseek-ai/dsh", "dsh", "node_modules/.bin/dsh"),
        ):
            with self.subTest(tool=tool), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prefix = root / "install"
                executable = prefix / relative
                executable.parent.mkdir(parents=True)
                executable.write_text("#!/bin/sh\nexit 0\n")
                executable.chmod(0o700)
                declaration = {"tool": tool, "version": "3.7.1", "binary": binary, "config": verify.CONFIGS[0]}
                completed = subprocess.CompletedProcess([], 0, str(executable) + "\n", "")
                with patch.object(verify.subprocess, "run", return_value=completed) as run:
                    selected = verify.resolve_binary(Path("/managed/mise"), declaration, prefix,
                                                     root / "scratch", root / "home", root / "repo")
                self.assertEqual(selected, executable)
                self.assertEqual(run.call_args.args[0], ["/managed/mise", "which", binary, "--tool", tool + "@3.7.1"])
                self.assertEqual(run.call_args.kwargs["env"]["MISE_INSTALL_MISSING_TOOLS"], "0")
                self.assertEqual(run.call_args.kwargs["env"]["MISE_TRUSTED_CONFIG_PATHS"], str(root / "repo/infra"))

    def test_exact_mise_resolver_rejects_external_binary_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "install"
            prefix.mkdir()
            external = root / "outside-git"
            external.write_text("#!/bin/sh\nexit 0\n")
            external.chmod(0o700)
            (prefix / "git").symlink_to(external)
            declaration = {"tool": "conda:git", "version": "2.54.0", "binary": "git", "config": verify.CONFIGS[0]}
            completed = subprocess.CompletedProcess([], 0, str(prefix / "git") + "\n", "")
            with patch.object(verify.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(ValueError, "outside"):
                    verify.resolve_binary(Path("/managed/mise"), declaration, prefix,
                                          root / "scratch", root / "home", root / "repo")

    def test_version_probe_accepts_v_prefix_without_revealing_output(self):
        entry = {"tool": "node", "binary": "node", "version": "24.19.0", "executable": "/managed/node"}
        completed = subprocess.CompletedProcess([], 0, "v24.19.0\nSECRET", "PRIVATE")
        with patch.object(verify.subprocess, "run", return_value=completed):
            result = verify.probe_version(entry, {}, Path("/tmp"))
        self.assertEqual(result["observed_version"], "24.19.0")
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_npm_pnpm_uses_safe_version_probe_under_explicit_node_path(self):
        self.assertEqual(verify.TOOL_BINARIES["npm:pnpm"], "pnpm")
        entry = {"tool": "npm:pnpm", "binary": "pnpm", "version": "10.33.0", "executable": "/managed/pnpm"}
        completed = subprocess.CompletedProcess([], 0, "10.33.0\n", "")
        with tempfile.TemporaryDirectory() as directory:
            env = verify.isolated_environment(Path(directory) / "home", [Path("/managed/node/bin")])
            with patch.object(verify.subprocess, "run", return_value=completed) as run:
                result = verify.probe_version(entry, env, Path(directory))
            self.assertEqual(run.call_args.args[0], ["/managed/pnpm", "--version"])
            self.assertEqual(run.call_args.kwargs["env"]["PATH"], "/managed/node/bin:/usr/bin:/bin")
            self.assertEqual(result["observed_version"], "10.33.0")
            self.assertEqual(env["MISE_INSTALL_MISSING_TOOLS"], "0")

    def test_archive_verification_detects_tampering_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup = root / "private-backup"
            backup.mkdir(mode=0o700)
            archive = backup / "legacy-runtimes.tar"
            archive.write_bytes(b"opaque archive fixture; no extraction")
            archive.chmod(0o600)
            (backup / "baseline.json").write_text(json.dumps({
                "archive": str(archive), "archive_sha256": verify.sha256(archive)}))
            (root / "current-path.txt").write_text(str(backup))
            self.assertTrue(verify.check_backup(root))
            archive.write_bytes(b"changed")
            self.assertFalse(verify.check_backup(root))

    def test_archive_verification_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "current-path.txt").write_text("/outside/private")
            self.assertFalse(verify.check_backup(root))


class OfflineGitTests(unittest.TestCase):
    @unittest.skipUnless(TEST_GIT.is_file() and (TEST_LFS_DIR / "git-lfs").is_file(),
                         "provide installed Git/LFS paths for offline integration test")
    def test_real_git_commit_worktree_lfs_without_owner_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / "untrusted-hooks"
            hooks.mkdir()
            sentinel = root / "unexpected-hook"
            hook = hooks / "pre-commit"
            hook.write_text('#!/bin/sh\ntouch "' + str(sentinel) + '"\nexit 1\n')
            hook.chmod(0o700)
            owner_config = root / "owner-gitconfig"
            owner_config.write_text('[core]\n hooksPath = ' + str(hooks) + '\n')
            before = owner_config.read_bytes()
            with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(owner_config), "DEEPSEEK_API_KEY": "SECRET"}):
                result = verify.offline_git_smoke(TEST_GIT, [TEST_GIT.parent, TEST_LFS_DIR], root / "scratch")
            self.assertTrue(result["passed"])
            self.assertIn("lfs-object-fsck", result["steps"])
            self.assertIn("worktree-remove", result["steps"])
            self.assertFalse(sentinel.exists())
            self.assertEqual(owner_config.read_bytes(), before)
            self.assertFalse((root / "scratch/worktree").exists())


if __name__ == "__main__":
    unittest.main()
