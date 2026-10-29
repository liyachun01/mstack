#!/usr/bin/python3
"""Preview/merge the two known remote project entries while Desktop is closed."""
import argparse
import copy
import datetime
import json
import os
from pathlib import Path
import subprocess

OLD_ID = "f33df298-105b-4eb5-93fd-b4be5798a84a"
NEW_ID = "79121e91-e22d-42fd-993a-af57ffc38fc4"
OLD_PATH = "/home/developer/workspace/mcp-stack"
NEW_PATH = "/home/developer/workspace/mstack"
STATE = Path("/Users/{{mstack:MAC_USER}}/.codex/.codex-global-state.json")
EVIDENCE = Path(__file__).resolve().parent / ".state"


def replacement(value):
    if isinstance(value, str):
        if value == OLD_ID:
            return NEW_ID
        if value == OLD_PATH or value.startswith(OLD_PATH + "/"):
            return NEW_PATH + value[len(OLD_PATH):]
    if isinstance(value, list):
        return [replacement(item) for item in value]
    if isinstance(value, dict):
        return {key: replacement(item) for key, item in value.items()}
    return value


def candidate(before):
    after = copy.deepcopy(before)
    projects = after["remote-projects"]
    old = [p for p in projects if p["id"] == OLD_ID]
    new = [p for p in projects if p["id"] == NEW_ID]
    assert len(new) == 1 and new[0]["remotePath"] == NEW_PATH
    if not old:
        return after
    assert len(old) == 1 and old[0]["remotePath"] == OLD_PATH
    assert old[0]["hostId"] == new[0]["hostId"]
    after["remote-projects"] = [p for p in projects if p["id"] != OLD_ID]
    for key in ("thread-project-assignments", "thread-workspace-root-hints",
                "thread-writable-roots", "selected-project"):
        if key in after:
            after[key] = replacement(after[key])
    for key in ("project-order", "pinned-project-ids"):
        if key in after:
            after[key] = list(dict.fromkeys(replacement(after[key])))
    # Abort rather than drop any unexpected project-keyed state.
    for key in ("sidebar-project-thread-orders", "project-appearances"):
        if OLD_ID in after.get(key, {}):
            raise RuntimeError("Additional project-keyed state needs explicit merging: " + key)
    return after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    original = STATE.read_bytes()
    before = json.loads(original)
    after = candidate(before)
    changed = [key for key in before if before[key] != after[key]]
    assignments = sum(v.get("projectId") == OLD_ID
                      for v in before.get("thread-project-assignments", {}).values())
    report = {"changed_keys": changed, "chat_assignments": assignments,
              "preserves_chat_ids": True, "applied": False}
    if args.apply and changed:
        processes = subprocess.check_output(
            ["macctl", "run", "ps", "-axo", "comm="], text=True)
        if any(Path(p.strip()).name in
               ("Codex", "ChatGPT", "Codex (Service)", "Codex (Renderer)")
               for p in processes.splitlines()):
            raise RuntimeError("Quit Codex/ChatGPT Desktop fully before applying; no app was stopped.")
        assert STATE.read_bytes() == original, "Desktop settings changed during preflight"
        EVIDENCE.mkdir(mode=0o700, exist_ok=True)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = EVIDENCE / ("desktop-global-before-" + stamp + ".json")
        with backup.open("xb") as stream:
            os.chmod(backup, 0o600)
            stream.write(original)
        temp = STATE.with_name(STATE.name + ".mstack-relocation.tmp")
        with temp.open("x") as stream:
            os.chmod(temp, STATE.stat().st_mode & 0o777)
            json.dump(after, stream, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        assert STATE.read_bytes() == original, "Settings changed; original remains untouched"
        os.replace(temp, STATE)
        assert json.loads(STATE.read_bytes()) == after
        report["applied"] = True
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
