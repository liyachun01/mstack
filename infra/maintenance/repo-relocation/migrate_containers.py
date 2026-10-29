#!/usr/bin/python3
"""Run the explicitly approved, stopped-only, six-container path migration."""
import argparse
import copy
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
STATE = Path(__file__).resolve().parent / ".state"
HOST_ROOT = "/Users/{{mstack:MAC_USER}}/OrbStack/devbox/home/developer/workspace/mstack"
OLD_ROOT = HOST_ROOT.replace("/workspace/mstack", "/workspace/mcp-stack")
GROUPS = {
    "shared": (["-f", HOST_ROOT + "/infra/services/compose.yaml"],
               ["headroom", "anytype-mcp", "graphify"]),
    "gateway": (["--project-directory", HOST_ROOT,
                 "-f", HOST_ROOT + "/infra/agentgateway/compose.yaml",
                 "-f", HOST_ROOT + "/infra/agentgateway/projects/compose.yaml"],
                ["agentgateway"]),
    "garage": (["--env-file", HOST_ROOT + "/infra/garage/state/runtime.env",
                "-f", HOST_ROOT + "/infra/garage/compose.yaml"], ["garage"]),
    "postgres": (["-f", HOST_ROOT + "/compose.yaml"], ["postgres"]),
}


def docker(*args):
    return subprocess.check_output(["macctl", "run", "docker", *args], text=True)


def private_json(name, value):
    p = STATE / name
    p.write_text(json.dumps(value, indent=2) + "\n")
    p.chmod(0o600)


def relocate(value):
    if isinstance(value, str):
        return value.replace(OLD_ROOT + "/", HOST_ROOT + "/")
    if isinstance(value, list):
        return [relocate(x) for x in value]
    if isinstance(value, dict):
        return {k: relocate(v) for k, v in value.items()}
    return value


def normalized(container):
    x = copy.deepcopy(container)
    config = x["Config"]
    if config.get("Hostname") == x["Id"][:12]:
        config["Hostname"] = "<generated-container-id>"
    config["Labels"].pop("com.docker.compose.config-hash", None)
    config["Labels"].pop("com.docker.compose.replace", None)
    if config.get("Env"):
        config["Env"].sort()
    host = x["HostConfig"]
    # Docker's unset and explicit false both leave the OOM killer enabled.
    if host.get("OomKillDisable") is None:
        host["OomKillDisable"] = False
    for key in ("Binds", "CapAdd", "CapDrop", "GroupAdd", "SecurityOpt"):
        if host.get(key):
            host[key].sort()
    if host.get("Mounts"):
        host["Mounts"].sort(key=lambda m: m["Target"])
    networks = {}
    for name, net in x["NetworkSettings"]["Networks"].items():
        networks[name] = {k: net.get(k) for k in
                          ("IPAMConfig", "Links", "DriverOpts", "GwPriority")}
        networks[name]["Aliases"] = sorted(a for a in (net.get("Aliases") or [])
                                           if a not in (x["Id"], x["Id"][:12]))
    return {"Name": x["Name"], "Image": x["Image"], "Config": config,
            "HostConfig": host,
            "Mounts": sorted(x["Mounts"], key=lambda m: m["Destination"]),
            "Networks": networks}


def changed_paths(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        return [p for k in sorted(set(before) | set(after))
                for p in changed_paths(before.get(k), after.get(k), path + "/" + k)]
    return [] if before == after else [path]


def verify(original, current):
    replacement = current["Config"]["Labels"].get("com.docker.compose.replace")
    assert replacement in (None, original["Id"], original["Id"][:12],
                           original["Name"], original["Name"].lstrip("/"))
    expected = relocate(normalized(original))
    if original["Config"]["Labels"].get("com.docker.compose.service") in ("agentgateway", "postgres"):
        # These definitions resolve paths from the repository root, via an
        # explicit --project-directory or the root Compose entry point.
        expected["Config"]["Labels"]["com.docker.compose.project.working_dir"] = HOST_ROOT
    changes = changed_paths(expected, normalized(current))
    if changes:
        # Report keys only, never environment values or credentials.
        raise RuntimeError(original["Name"] + " unexpected changes: " + ", ".join(changes))
    assert not current["State"]["Running"] and current["State"]["Status"] == "created"
    assert current["Id"] != original["Id"]
    assert not any(OLD_ROOT in m["Source"] for m in current["Mounts"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=GROUPS)
    args = parser.parse_args()
    baseline = json.loads((STATE / "containers-before-apply.json").read_text())
    flags, services = GROUPS[args.group]
    selected = [x for x in baseline if
                x["Config"].get("Labels", {}).get("com.docker.compose.project") == "mstack"
                and x["Config"]["Labels"].get("com.docker.compose.service") in services]
    assert len(selected) == len(services)
    current = json.loads(docker("inspect", *(x["Name"].lstrip("/") for x in selected)))
    for old, now in zip(selected, current):
        assert old["Id"] == now["Id"], "Container already changed; inspect before retrying"
        assert normalized(old) == normalized(now)
        assert not now["State"]["Running"]
    result = subprocess.run(["macctl", "run", "docker", "compose", "-p", "mstack",
                             *flags, "create", "--force-recreate", "--no-build",
                             "--pull", "never", *services], text=True, capture_output=True)
    private_json(args.group + "-create-result.json", {
        "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        raise RuntimeError("Scoped create failed; inspect private log before continuing")
    after = json.loads(docker("inspect", *(x["Name"].lstrip("/") for x in selected)))
    private_json(args.group + "-after.json", after)
    for old, now in zip(selected, after):
        verify(old, now)
        print(json.dumps({"name": now["Name"], "status": now["State"]["Status"],
                          "same_image_data_and_settings": True,
                          "mounts_use_mstack": True}), flush=True)


if __name__ == "__main__":
    main()
