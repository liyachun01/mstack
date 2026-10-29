"""Read installed manifests/assets without importing or executing vendor code."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def browser_contract(shell: str, plugin: str) -> dict:
    """Fail closed when the inspected minified shell format no longer matches."""
    factory = re.search(
        r"function ([$\w]+)\(\)\{return\{react:[^}]+\}\}", shell
    )
    if factory is None:
        raise ValueError("React browser seed factory was not found")
    if "staticModules:" + factory[1] + "()" not in shell:
        raise ValueError("React seed factory is not passed to staticModules")
    seeds = set(re.findall(r'(?:\{|,)(?:"([^"]+)"|([\w$-]+)):', factory[0]))
    seeds = {quoted or bare for quoted, bare in seeds}
    versions = set(re.findall(r'\.version="(18\.[0-9]+\.[0-9]+)"', shell))
    if versions != {"18.3.1"}:
        raise ValueError("Bundled React version markers need fresh qualification")
    if not plugin.startswith("window.__ModuleLoader__.load({ id: "):
        raise ValueError("Vision client does not use the native factory registry")
    if "factory: (require) => {" not in plugin:
        raise ValueError("Vision client factory format needs fresh qualification")
    required = set(re.findall(r'''\brequire\(["']([^"']+)["']\)''', plugin))
    if not {"react", "react/jsx-runtime"}.issubset(required):
        raise ValueError("Expected React imports disappeared; review this client format")
    missing = required - seeds
    if missing:
        raise ValueError("Browser imports absent from shell seed: " + ", ".join(sorted(missing)))
    return {
        "bundled_react_version_marker": "18.3.1",
        "required_browser_imports": sorted(required),
        "all_imports_are_shell_seeds": True,
        "native_factory_registration": True,
        "runtime_execution_tested": False,
    }


def inspect(cli_root: Path, vision_root: Path) -> dict:
    cli = json.loads((cli_root / "package.json").read_text())
    vision = json.loads((vision_root / "package.json").read_text())
    if (cli.get("name"), cli.get("version")) != ("@deepseek-ai/dsh", "0.2.0-rc.2"):
        raise ValueError("CLI identity changed; review instead of auto-upgrading")
    if (vision.get("name"), vision.get("version")) != ("@anionex/dsh-vision-toolkit", "0.1.46"):
        raise ValueError("Vision plugin identity changed; review instead of auto-upgrading")
    frontend = cli_root / "node_modules/@deepseek-ai/dsh-web-frontend"
    metadata = json.loads((frontend / "package.json").read_text())
    if metadata.get("version") != cli["version"]:
        raise ValueError("Frontend/CLI version mismatch")
    dist = (frontend / "dist").resolve()
    html = (dist / "index.html").read_text()
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
    if len(scripts) != 1:
        raise ValueError("Expected one shell entry script")
    asset = (dist / scripts[0]).resolve()
    if not asset.is_relative_to(dist) or not asset.is_file():
        raise ValueError("Shell script must be a local frontend asset")
    client = vision_root / "lib/client.js"
    contract = browser_contract(asset.read_text(), client.read_text())
    if vision.get("peerDependencies", {}).get("react") != "^18.2.0":
        raise ValueError("React peer range changed; fresh compatibility review required")
    return {
        "cli_version": cli["version"],
        "vision_version": vision["version"],
        "react_peer_range": "^18.2.0",
        "frontend_asset": str(asset.relative_to(dist)),
        "frontend_asset_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        "vision_client_sha256": hashlib.sha256(client.read_bytes()).hexdigest(),
        **contract,
        "limitation": "Static source contract only; no profile, browser, model or Python execution",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli-root", required=True, type=Path)
    parser.add_argument("--vision-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.cli_root, args.vision_root)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Static qualification failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
