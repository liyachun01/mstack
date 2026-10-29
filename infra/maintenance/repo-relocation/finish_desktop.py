#!/usr/bin/python3
"""One-shot, explicitly approved Desktop restart, project merge, alias removal."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import desktop_project

HERE = Path(__file__).resolve().parent
STATE = HERE / ".state"
RESULT = STATE / "desktop-finish-result.json"


def mac(*args):
    return subprocess.run(["macctl", "run", *args], check=True,
                          capture_output=True, text=True, timeout=30)


def writers_present():
    processes = mac("ps", "-axo", "comm=").stdout.splitlines()
    # Crash reporters can outlive the app and never write desktop settings.
    return any(Path(p.strip()).name in
               ("Codex", "ChatGPT", "Codex (Service)", "Codex (Renderer)")
               for p in processes)


def write_result(result):
    RESULT.write_text(json.dumps(result, indent=2) + "\n")
    RESULT.chmod(0o600)


def verify_project():
    data = json.loads(desktop_project.STATE.read_bytes())
    projects = data["remote-projects"]
    assert not any(p["id"] == desktop_project.OLD_ID for p in projects)
    assert sum(p["id"] == desktop_project.NEW_ID and
               p["remotePath"] == desktop_project.NEW_PATH for p in projects) == 1
    assignments = data["thread-project-assignments"]
    assert not any(v.get("projectId") == desktop_project.OLD_ID
                   for v in assignments.values())
    return data


def main():
    assert not RESULT.exists(), "An earlier execution needs inspection before retrying"
    alias = Path(desktop_project.OLD_PATH)
    root = Path(desktop_project.NEW_PATH)
    assert alias.is_symlink() and alias.samefile(root) and not root.is_symlink()
    report = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "desktop_merged": False, "desktop_reopened": False,
              "old_alias_removed": False, "complete": False}
    write_result(report)
    quit_requested = False
    try:
        # The application name and executable were inspected before approval.
        quit_requested = True
        mac("osascript", "-e", 'tell application "ChatGPT" to quit')
        deadline = time.monotonic() + 45
        while writers_present():
            if time.monotonic() >= deadline:
                raise RuntimeError("Desktop did not fully quit; settings and alias retained")
            time.sleep(1)
        merged = subprocess.run([sys.executable, str(HERE / "desktop_project.py"), "--apply"],
                                capture_output=True, text=True, check=True, timeout=30)
        report["merge_report"] = json.loads(merged.stdout)
        verify_project()
        report["desktop_merged"] = True
        write_result(report)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:500]
        raise
    finally:
        if quit_requested:
            try:
                mac("open", "-a", "ChatGPT")
                report["desktop_reopened"] = True
            except Exception as exc:
                report["reopen_error"] = type(exc).__name__
        write_result(report)
    if not report["desktop_reopened"]:
        raise RuntimeError("Desktop reopening failed; alias retained")
    deadline = time.monotonic() + 30
    while not writers_present():
        if time.monotonic() >= deadline:
            raise RuntimeError("Desktop process not observed after reopen; alias retained")
        time.sleep(1)
    for _ in range(5):
        time.sleep(2)
        verify_project()
    report["desktop_merge_persisted_after_restart"] = True
    # Identity checks immediately before unlinking prevent recursive deletion or
    # removal of a replacement directory. Container migration was separately verified.
    assert alias.is_symlink() and os.readlink(alias) == str(root) and alias.samefile(root)
    alias.unlink()
    assert not os.path.lexists(alias) and root.is_dir()
    report.update(old_alias_removed=True, complete=True,
                  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_result(report)


if __name__ == "__main__":
    main()
