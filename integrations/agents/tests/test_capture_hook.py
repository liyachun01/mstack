import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import capture_hook

TASK = "bafyreifryuoqtjlx6dlicnv7ighz4sziojrgyqprrjghwyktq35rfiax2m"
HOOKS = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command",
         "command": "python3 /x/integrations/agents/capture_hook.py"}]}]}}
CAPTURE = {"enabled": True, "sink": "anytype-taskboard", "harnesses": ["claude", "codex"]}


class CaptureGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "project"
        self.home = Path(temp.name) / "home"
        (self.root / ".mstack").mkdir(parents=True)
        (self.root / ".claude").mkdir()
        (self.home / ".claude").mkdir(parents=True)
        self.write_config(CAPTURE)
        (self.root / ".claude/settings.local.json").write_text(json.dumps(HOOKS))
        self.env = {"CLAUDE_PROJECT_DIR": str(self.root), "MSTACK_TASK": TASK}
        self.event = {"hook_event_name": "UserPromptSubmit", "prompt": "hello sk-abcdefghijklmnopqrstu"}

    def write_config(self, capture):
        cfg = {"project": "demo", **({"capture": capture} if capture is not None else {})}
        (self.root / ".mstack/stack.json").write_text(json.dumps(cfg))

    def decide(self, event=None, env=None, harness="claude"):
        return capture_hook.decide(harness, event or self.event, env or self.env, self.home)

    def test_all_gates_agree_and_secrets_are_redacted(self):
        self.assertEqual(self.decide(), (TASK, [("in", "hello [redacted]")], 1800))

    def test_config_must_opt_in(self):
        self.write_config(None)
        self.assertIsNone(self.decide())
        self.write_config({**CAPTURE, "enabled": False})
        self.assertIsNone(self.decide())
        self.write_config({**CAPTURE, "events": ["Stop"]})
        self.assertIsNone(self.decide())
        self.write_config({**CAPTURE, "harnesses": ["codex"]})
        self.assertIsNone(self.decide())

    def test_invalid_config_is_rejected(self):
        self.write_config({**CAPTURE, "credential_file": ".mstack/secrets/x"})
        with self.assertRaises(ValueError):
            self.decide()

    def test_requires_project_registration(self):
        (self.root / ".claude/settings.local.json").write_text("{}")
        self.assertIsNone(self.decide())

    def test_refuses_when_also_registered_at_user_level(self):
        for name in capture_hook.USER_SETTINGS:
            path = self.home / ".claude" / name
            path.write_text(json.dumps(HOOKS))
            self.assertIsNone(self.decide())
            path.unlink()

    def test_project_without_mstack_config_is_ignored(self):
        self.assertIsNone(self.decide(env={**self.env, "CLAUDE_PROJECT_DIR": str(self.home)}))

    def test_requires_bound_task(self):
        self.assertIsNone(self.decide(env={"CLAUDE_PROJECT_DIR": str(self.root)}))
        (self.root / ".mstack/cache").mkdir()
        (self.root / ".mstack/cache/current-task").write_text(TASK)
        self.assertEqual(self.decide(env={"CLAUDE_PROJECT_DIR": str(self.root)})[0], TASK)

    def test_worktree_session_uses_main_checkout_config(self):
        git = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        tree = self.root.parent / "wt"
        git("worktree", "add", "-q", "-b", "task/x", str(tree))
        (tree / ".mstack/cache").mkdir(parents=True)
        (tree / ".mstack/cache/current-task").write_text(TASK)
        self.assertEqual(self.decide(env={"CLAUDE_PROJECT_DIR": str(tree)})[0], TASK)

    def test_session_in_an_app_folder_of_a_worktree_finds_its_task(self):
        git = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        tree = self.root.parent / "wt"
        git("worktree", "add", "-q", "-b", "task/y", str(tree))
        (tree / ".mstack/cache").mkdir(parents=True)
        (tree / ".mstack/cache/current-task").write_text(TASK)
        (tree / "apps/api").mkdir(parents=True)
        self.assertEqual(self.decide(env={"CLAUDE_PROJECT_DIR": str(tree / "apps/api")})[0], TASK)

    def test_codex_needs_worker_invocation_and_no_global_notify(self):
        turn = {"type": "agent-turn-complete", "cwd": str(self.root),
                "input-messages": ["fix cart"], "last-assistant-message": "done"}
        env = {"MSTACK_TASK": TASK}
        self.assertIsNone(self.decide(turn, env, "codex"))
        env["MSTACK_CODEX_NOTIFY"] = "1"
        self.assertEqual(self.decide(turn, env, "codex")[1], [("in", "fix cart"), ("out", "done")])
        (self.home / ".codex").mkdir()
        (self.home / ".codex/config.toml").write_text('notify = ["python3", "/x/integrations/agents/capture_hook.py"]')
        self.assertIsNone(self.decide(turn, env, "codex"))


if __name__ == "__main__":
    unittest.main()
