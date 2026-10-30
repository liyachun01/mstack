"""Run on macOS: Anytype-managed agent task board in one explicitly granted channel.

Illustration helper for docs/design/005-AGENT-TASK-BOARD.md. Keys never appear in
argv/stdout; the credential is a private 0600 file. Every request after whoami is
confined to the single granted channel. Python 3.9 compatible (macOS system).

  challenge                       ask Anytype Desktop to show a 4-digit code
  exchange <cred> <id> <code> <channel>  save the scoped key after grant checks
  provision <cred> <schema>       properties, type, kanban board query, chat
  seed <cred> <schema>            illustrative tasks, Task Board collection, Agent Log messages
  board <cred>                    dispatcher view: open tasks as JSON
  capture <cred> <task> <agent> <in|out> <text|->   hook/gateway sink; "-" reads stdin
  api <cred> <METHOD> <channel-relative path> [-]     one in-channel request; body on stdin
"""
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "http://127.0.0.1:31009"
STATE = Path(".mstack/evidence/taskboard-test.json")


def http(method, path, key=None, body=None, query=None):
    if query:
        path += "?" + urllib.parse.urlencode(query)
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(API + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        raise SystemExit("%s %s -> HTTP %s %s" % (method, path, error.code, error.read().decode()[:600]))


def read_key(cred):
    cred = Path(cred)
    if cred.is_symlink() or cred.stat().st_mode & 0o077:
        sys.exit("Credential must be a private regular file")
    return cred.read_text().strip()


def check_grant(key, channel=None):
    who = http("GET", "/v2/auth/whoami", key, query={"ids": "full"})
    grant = who.get("grant") or {}
    spaces = grant.get("spaces") or []
    if grant.get("all_spaces") or not grant.get("restricted") or len(spaces) != 1 \
            or "write" not in str(grant.get("permission")):
        sys.exit("Expected exactly one read/write channel grant; nothing done")
    space = spaces[0]
    if channel and space.get("name") != channel:
        sys.exit("Granted channel name differs from %r; nothing done" % channel)
    return space["id"]


class Board:
    def __init__(self, cred):
        self.key = read_key(cred)
        self.space = check_grant(self.key)
        self.state = json.loads(STATE.read_text()) if STATE.exists() else {}

    def call(self, method, sub, body=None, query=None):
        return http(method, "/v2/spaces/%s/%s" % (self.space, sub), self.key, body, query)

    def rows(self, sub):
        out, offset = [], 0
        while True:
            page = self.call("GET", sub, query={"offset": offset, "limit": 100})
            data = page.get("data") or []
            out += data
            offset += len(data)
            if not data or not (page.get("pagination") or {}).get("has_more"):
                return out

    def set_props(self, obj, props):
        return self.call("PATCH", "objects/" + obj, {"ops": [{"op": "set_properties", "set": props}]})

    def save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True)
        self.state["space_id"] = self.space
        STATE.write_text(json.dumps(self.state, indent=2) + "\n")


def provision(board, schema):
    have = {p["key"] for p in board.rows("properties")}
    added = []
    for prop in schema["properties"]:
        if prop["key"] not in have:
            body = {k: prop[k] for k in ("key", "name", "format", "options") if k in prop}
            board.call("POST", "properties", body)
            added.append(prop)
            print("property created:", prop["key"])
    t = schema["type"]
    if t["key"] in {row["key"] for row in board.rows("types")}:
        for prop in added:
            board.call("PATCH", "types/" + t["key"], {"ops": [
                {"op": "add_property", "property": prop["key"], "section": prop.get("section", "hidden")}]})
            print("type field added:", prop["key"])
    else:
        board.call("POST", "types", {
            "api_key": t["key"], "name": t["name"], "plural_name": t["plural_name"],
            "icon": {"format": "emoji", "emoji": t["emoji"]}, "default_view": t["default_view"],
            "layout": "basic",
            "property_definitions": [{"property": p["key"], "section": p.get("section", "hidden")}
                                     for p in schema["properties"]]})
        print("type created:", t["key"])
    chats = {c["name"]: c["id"] for c in board.rows("chats")}
    board.state["chat"] = chats.get(schema["chat"]) or board.call("POST", "chats", {"name": schema["chat"]})["id"]
    board.save()


SEED = [
    {"name": "Capture agent in/out at agentgateway", "status": "In Progress", "priority": "High",
     "agent": "claude", "source": "anytype", "labels": ["mstack", "gateway"], "estimate": 5,
     "body": "Add an access-log/OTel sink on the MCP and LLM routes; forward each turn to the Agent Log chat and bump the task run count."},
    {"name": "Sync my Linear issues both ways", "status": "Todo", "priority": "High",
     "agent": "codex", "source": "anytype", "labels": ["mstack", "sync"], "estimate": 8,
     "body": "Windmill job: pull issues where assignee=me OR creator=me, upsert by Linear ID, push Anytype edits back."},
    {"name": "Dispatcher: pick next task and assign agent", "status": "Backlog", "priority": "Medium",
     "agent": "dispatcher", "source": "anytype", "labels": ["mstack"], "estimate": 3,
     "body": "Read the board, pick the highest-priority unblocked Todo, set Assigned Agent, launch the harness with the task as brief."},
    {"name": "Example Linear-mirrored issue", "status": "Todo", "priority": "Medium",
     "agent": "human", "source": "linear", "labels": ["illustration", "sync"], "estimate": 1,
     "linear_identifier": "DEMO-1", "linear_url": "https://linear.app/example/issue/DEMO-1",
     "body": "Placeholder showing how a synced issue looks. Not a real Linear issue; no Linear call was made."},
    {"name": "Write Task Board design doc", "status": "Done", "priority": "Low",
     "agent": "claude", "source": "agent-capture", "labels": ["mstack", "illustration"], "estimate": 1,
     "body": "Created from a captured agent turn: docs/design/005-AGENT-TASK-BOARD.md."},
]


def seed(board, schema):
    tasks = board.state.setdefault("tasks", {})
    for row in board.rows("objects"):
        if row.get("type") == schema["type"]["key"] and row.get("name") in {i["name"] for i in SEED}:
            tasks.setdefault(row["name"], row["id"])
    for item in SEED:
        if item["name"] in tasks:
            continue
        props = {"task_status": item["status"], "task_priority": item["priority"],
                 "task_agent": item["agent"], "task_source": item["source"],
                 "task_labels": item["labels"], "task_estimate": item["estimate"],
                 "agent_run_count": 0}
        for k in ("linear_identifier", "linear_url"):
            if k in item:
                props[k] = item[k]
        made = board.call("POST", "objects", {"type": schema["type"]["key"], "name": item["name"],
                                              "properties": props, "markdown": item["body"],
                                              "template": "none"})
        tasks[item["name"]] = made["id"]
        board.save()
        print("task created:", item["name"])
    names = list(tasks)
    blocked = tasks["Dispatcher: pick next task and assign agent"]
    board.set_props(blocked, {"task_blocked_by": [tasks[names[0]]]})
    if "collection" not in board.state:
        board.state["collection"] = board.call("POST", "collections", {
            "name": schema["collection"], "items": list(tasks.values())})["id"]
        print("collection created with", len(tasks), "tasks")
    board.save()
    if not board.state.get("seeded_chat"):
        for line in [
            "dispatcher → claude · Assigned: Capture agent in/out at agentgateway",
            "claude ← user · Extend mstack so agent messages become tasks in Anytype",
            "claude → user · Task Board provisioned; 5 illustrative tasks created",
        ]:
            board.call("POST", "chats/%s/messages" % board.state["chat"], {"text": line})
        board.state["seeded_chat"] = True
        board.save()


def board_view(board):
    sys.exit("Superseded: use `mstack board status --project <name>` (tables are per-project collections now).")


def capture(board, task, agent, direction, text):
    """Sample sink for gateway/hook capture: one chat line per turn, bump the task run count."""
    if text == "-":
        text = sys.stdin.read()
    props = board.call("GET", "objects/" + task).get("properties") or {}
    runs = (props.get("agent_run_count") or 0) + 1
    arrow = "→" if direction == "out" else "←"
    board.call("POST", "chats/%s/messages" % board.state["chat"],
               {"text": "%s %s · %s: %s" % (agent, arrow, props.get("name"), text[:1800])})
    board.set_props(task, {"agent_run_count": runs})
    print("captured; run count", runs)


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "challenge":
        print(json.dumps(http("POST", "/v2/auth/challenges", body={"app_name": "mstack-taskboard"})))
    elif cmd == "exchange":
        cred, challenge, code, channel = Path(argv[1]), argv[2], argv[3], argv[4]
        if cred.exists() or "secrets" not in cred.parts:
            sys.exit("New private target under a secrets directory required")
        made = http("POST", "/v2/auth/api_keys", body={"challenge_id": challenge, "code": code})
        check_grant(made["api_key"], channel)
        cred.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(cred), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(made["api_key"])
        print("Scoped key saved privately; single read/write channel grant verified; value omitted")
    elif cmd in ("provision", "seed"):
        board, schema = Board(argv[1]), json.loads(Path(argv[2]).read_text())
        (provision if cmd == "provision" else seed)(board, schema)
    elif cmd == "board":
        board_view(Board(argv[1]))
    elif cmd == "api":
        # Bridge for the Ubuntu orchestrator: one request, confined to the granted channel.
        board = Board(argv[1])
        body = sys.stdin.read() if len(argv) > 4 and argv[4] == "-" else ""
        query = dict(urllib.parse.parse_qsl(argv[3].split("?", 1)[1])) if "?" in argv[3] else None
        sub = argv[3].split("?", 1)[0].lstrip("/")
        if sub.startswith("v2") or ".." in sub.split("/"):
            sys.exit("Channel-relative path required")
        data = json.loads(body) if body else None
        if sub == ".":          # the granted channel itself (e.g. PATCH {"name": …} renames it)
            out = http(argv[2], "/v2/spaces/" + board.space, board.key, data, query)
        else:
            out = board.call(argv[2], sub, data, query)
        print(json.dumps({"space_id": board.space, "body": out}))
    elif cmd == "capture":
        capture(Board(argv[1]), *argv[2:6])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
