"""Session capture hook: mirror an agent session's turns onto its task's discussion.

Claude Code: registered for UserPromptSubmit ("in", the prompt) and Stop ("out",
the last reply), reading the hook event on stdin. Codex: passed per invocation as
`-c notify=[..., "--codex"]` by the mstack worker; the turn JSON is the last argv.

Every gate must agree, otherwise the hook is a silent no-op:

1. the session's project (its main checkout when the session runs in a task
   worktree) has a valid `.mstack/stack.json` whose `capture` section is enabled
   for this harness and event;
2. project scope only: Claude must find the hook in the project's
   `.claude/settings.json` or `settings.local.json` and in no user-level settings;
   Codex must be started by the mstack worker (MSTACK_CODEX_NOTIFY) with no
   global `~/.codex/config.toml` notify pointing here;
3. a task is bound via $MSTACK_TASK or .mstack/cache/current-task.

Always exits 0; the write runs detached through `mstack board note`.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

STACK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STACK_ROOT / "integrations/stack"))
SECRET = re.compile(r"(anytype_[0-9A-Za-z_]{20,}|sk-[0-9A-Za-z_-]{16,}|Bearer\s+\S+|ghp_[0-9A-Za-z]{20,}|lin_api_[0-9A-Za-z]{20,})")
MARK = "integrations/agents/capture_hook.py"
USER_SETTINGS = ("settings.json", "settings.local.json")
PROJECT_SETTINGS = ("settings.json", "settings.local.json")  # shared or local-visibility project


def registered(path):
    try:
        return MARK in json.dumps(json.loads(path.read_text()).get("hooks", {}))
    except (OSError, ValueError, AttributeError):
        return False


def config_root(session):
    """The directory holding .mstack/stack.json: the session dir, or its main checkout for a worktree."""
    if (session / ".mstack/stack.json").is_file():
        return session
    done = subprocess.run(["git", "-C", str(session), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                          capture_output=True, text=True)
    main = Path(done.stdout.strip()).parent if done.returncode == 0 else None
    return main if main and (main / ".mstack/stack.json").is_file() else None


def project_scope_only(harness, dirs, home, env):
    if harness == "codex":
        global_cfg = Path(env.get("CODEX_HOME") or home / ".codex") / "config.toml"
        clean = not (global_cfg.is_file() and MARK in global_cfg.read_text(errors="replace"))
        return env.get("MSTACK_CODEX_NOTIFY") == "1" and clean
    if not any(registered(d / ".claude" / name) for d in dirs for name in PROJECT_SETTINGS):
        return False
    claude_home = Path(env.get("CLAUDE_CONFIG_DIR") or home / ".claude")
    return not any(registered(claude_home / name) for name in USER_SETTINGS)


def bound_task(dirs, env):
    task = env.get("MSTACK_TASK", "").strip()
    for d in dirs:
        marker = d / ".mstack/cache/current-task"
        if not task and marker.is_file():
            task = marker.read_text().strip()
    # Anytype object ids (bafy…) or Linear issue ids (UUID)
    ok = re.fullmatch(r"bafy[a-z0-9]{20,}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", task or "")
    return task if ok else None


def last_reply(event):
    if event.get("last_assistant_message"):
        return event["last_assistant_message"]
    path = event.get("transcript_path")
    if not path or not Path(path).is_file():
        return ""
    reply = ""
    for line in Path(path).read_text(errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") or {}
        if entry.get("type") == "assistant" and message.get("role") == "assistant":
            texts = [c.get("text", "") for c in message.get("content") or [] if c.get("type") == "text"]
            if any(texts):
                reply = "\n".join(t for t in texts if t)
    return reply


def turns(harness, event):
    """[(event name, direction, text)] for one hook call."""
    if harness == "codex":
        if event.get("type") != "agent-turn-complete":
            return []
        asked = (event.get("input-messages") or [""])[-1]
        return [("UserPromptSubmit", "in", asked), ("Stop", "out", event.get("last-assistant-message") or "")]
    name = event.get("hook_event_name")
    if name == "UserPromptSubmit":
        return [(name, "in", event.get("prompt", ""))]
    if name == "Stop":
        return [(name, "out", last_reply(event))]
    return []


def decide(harness, event, env, home=Path.home()):
    """Return (task, [(direction, text)], max_chars) when every gate agrees, else None."""
    import config
    session = Path(env.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()).resolve()
    root = config_root(session)
    if not root:
        return None
    capture = config.project_config(root).get("capture") or {}
    if not capture.get("enabled") or capture.get("sink") != "anytype-taskboard" \
            or harness not in capture.get("harnesses", ["claude"]):
        return None
    top = subprocess.run(['git', '-C', str(session), 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True).stdout.strip()
    dirs = list(dict.fromkeys(d for d in (session, Path(top) if top else None, root) if d))
    if not project_scope_only(harness, dirs, home, env):
        return None
    task = bound_task(dirs, env)
    if not task:
        return None
    allowed = capture.get("events", ["UserPromptSubmit", "Stop"])
    posts = [(d, SECRET.sub("[redacted]", t or "").strip()) for n, d, t in turns(harness, event) if n in allowed]
    posts = [(d, t) for d, t in posts if t]
    return (task, posts, capture.get("max_chars", 1800)) if posts else None


def main(argv):
    try:
        harness = "codex" if "--codex" in argv else "claude"
        event = json.loads(argv[-1]) if harness == "codex" else json.load(sys.stdin)
        decision = decide(harness, event, os.environ)
        if not decision:
            return
        task, posts, limit = decision
        agent = os.environ.get("MSTACK_AGENT", harness)
        for direction, text in posts:
            child = subprocess.Popen(
                [sys.executable, str(STACK_ROOT / "integrations/orchestrator/cli.py"), "note",
                 "--task", task, "--agent", agent, "--direction", direction, "-"],
                cwd=STACK_ROOT, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            child.stdin.write(text[:limit].encode())
            child.stdin.close()
    except Exception:
        pass  # capture must never break the agent turn


if __name__ == "__main__":
    main(sys.argv[1:])
