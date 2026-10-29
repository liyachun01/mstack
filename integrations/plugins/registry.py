"""mstack plugin registry: discover, validate and resolve joint plugins.

Built-in plugins live in integrations/plugins/builtin/<name>/plugin.json. A project
can add its own in <project>/.mstack/plugins/<name>/plugin.json (kept out of git by
local visibility); a project plugin may not shadow a built-in name. Discovery reads
files only: nothing is installed, started or registered.

  python3 registry.py list [--project P] [--joint J]
  python3 registry.py validate [--project P]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

HERE = Path(__file__).resolve().parent
STACK_ROOT = HERE.parents[1]
sys.path.insert(0, str(STACK_ROOT/'integrations/stack'))
SCHEMA = json.loads((HERE/'schemas/plugin.schema.json').read_text())
Draft202012Validator.check_schema(SCHEMA)


def _load(path, origin):
    manifest = json.loads(path.read_text())
    error = best_match(Draft202012Validator(SCHEMA).iter_errors(manifest))
    if error:
        where = '.'.join(map(str, error.absolute_path)) or '<root>'
        raise ValueError('%s: %s: %s' % (path, where, error.message))
    if manifest['name'] != path.parent.name:
        raise ValueError('%s: name must match its folder' % path)
    return {**manifest, 'origin': origin, 'dir': str(path.parent)}


def discover(project=None):
    plugins = {}
    for path in sorted((HERE/'builtin').glob('*/plugin.json')):
        plugin = _load(path, 'builtin')
        plugins[plugin['name']] = plugin
    if project:
        folder = Path(project)/'.mstack/plugins'
        if folder.is_symlink():
            raise ValueError('Project plugin folder cannot be a symlink')
        for path in sorted(folder.glob('*/plugin.json')):
            plugin = _load(path, 'project')
            if plugin['name'] in plugins:
                raise ValueError('Project plugin %s shadows a built-in' % plugin['name'])
            plugins[plugin['name']] = plugin
    return plugins


def joint(name, project=None):
    return {k: v for k, v in discover(project).items() if v['joint'] == name}


def available(plugin, project=None):
    """Usable at runtime: implemented, required binaries already on PATH (never installed) and,
    for tenant plugins, the project registered with that shared service."""
    if plugin['status'] != 'implemented':
        return False
    requires = plugin.get('requires', {})
    if not all(shutil.which(b) for b in requires.get('binaries', [])):
        return False
    for ref in requires.get('credentials', []):
        if ref.startswith('.mstack/secrets/') and not (project and (Path(project)/ref).is_file()):
            return False
    if requires.get('tenant'):
        if not project:
            return False
        import project_state
        return requires['tenant'] in (project_state.tenants(Path(project)).get('tools') or {})
    return True


def fill(template, values, lists=None):
    """Fill an argv template. An argument that is exactly {name} of a list value expands in place;
    other placeholders are plain substrings. Values are never shell-parsed."""
    out = []
    for part in template:
        name = part[1:-1] if part.startswith('{') and part.endswith('}') else None
        if lists and name in lists:
            out += list(lists[name])
            continue
        for key, value in values.items():
            part = part.replace('{%s}' % key, str(value))
        out.append(part)
    return out


def render(plugin, mcp=(), **values):
    return fill(plugin['command'], {'python': sys.executable, 'plugin_dir': plugin['dir'], **values},
                {'mcp': mcp})


def selected(project, cfg=None):
    """{joint: plugin} chosen in the project's `joints` config; unknown or mismatched names fail."""
    import config
    cfg = cfg or config.project_config(Path(project))
    plugins = discover(project)
    out = {}
    for joint_name, name in (cfg.get('joints') or {}).items():
        plugin = plugins.get(name)
        if not plugin or plugin['joint'] != joint_name:
            raise ValueError('joints.%s: %s is not a %s plugin' % (joint_name, name, joint_name))
        out[joint_name] = plugin
    return out


def worker_servers(project):
    """Stdio MCP servers a worker session of this project gets: selected, available, worker-mcp plugins.
    Returns ([{name, command}], [skipped reasons])."""
    servers, skipped = [], []
    for joint_name, plugin in selected(project).items():
        if 'worker-mcp' not in plugin.get('expose', []):
            continue
        if not available(plugin, project):
            skipped.append('%s (%s): not available for this project' % (plugin['name'], joint_name))
            continue
        command = fill(plugin['mcp']['command'], {'python': 'python3', 'stack': STACK_ROOT,
                                                  'project': Path(project).resolve()})
        servers.append({'name': plugin['mcp']['name'], 'command': command, 'hint': plugin['mcp'].get('hint', '')})
    return servers, skipped


def load(plugin):
    """Import a python-transport plugin's adapter module."""
    if plugin['transport'] != 'python':
        raise ValueError(plugin['name'] + ' is not a python plugin')
    path = (Path(plugin['dir'])/plugin['entry']).resolve()
    spec = importlib.util.spec_from_file_location('mstack_plugin_' + plugin['name'].replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    p = argparse.ArgumentParser(prog='mstack plugin', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    for name in ('list', 'validate'):
        s = sub.add_parser(name)
        s.add_argument('--project', type=Path)
        if name == 'list':
            s.add_argument('--joint')
    args = p.parse_args(argv)
    try:
        plugins = discover(args.project)
    except (ValueError, OSError) as error:
        print('mstack plugin: ' + str(error), file=sys.stderr)
        return 1
    if args.command == 'validate':
        print(json.dumps({'valid': len(plugins), 'plugins': sorted(plugins)}, indent=2))
        return 0
    rows = [{'name': n, 'joint': m['joint'], 'transport': m['transport'], 'status': m['status'],
             'available': available(m, args.project), 'origin': m['origin'], 'summary': m.get('summary', '')}
            for n, m in sorted(plugins.items(), key=lambda kv: (kv[1]['joint'], kv[0]))
            if not args.joint or m['joint'] == args.joint]
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
