"""Agent hosts for the orchestrator: the `agent` joint of the plugin registry.

Two kinds, one contract. Every host starts in the task worktree with the brief, has
the task bound (env or `.mstack/cache/current-task`), and reports back through the
board (`mstack board note` / `done`), never through the host itself:

- argv (spawn): a headless CLI the orchestrator starts from the manifest's command.
- handoff:      a desktop app the orchestrator cannot start from a shell. `dispatch`
                returns a launch spec; the orchestrator agent starts it with its own
                host tool (Claude Desktop: start_session) or the owner opens it.

A new agent is a manifest (integrations/plugins/builtin or the project's
.mstack/plugins), not code here. Nothing is installed.
"""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'plugins'))
import registry

HOOK = HERE.parent/'agents/capture_hook.py'
NOTIFY = json.dumps(['python3', str(HOOK), '--codex'])


def hosts(project=None):
    return {name: {**m, 'kind': 'spawn' if m['transport'] == 'argv' else m['transport']}
            for name, m in registry.joint('agent', project).items()}


HOSTS = hosts()


def mcp_style(runner, project=None):
    return hosts(project)[runner].get('mcp_style', 'none')


def codex_mcp_args(servers):
    """Per-run `-c` overrides; values are TOML (JSON strings/arrays are valid TOML)."""
    args = []
    for server in servers:
        key = 'mcp_servers.' + server['name']
        args += ['-c', '%s.command=%s' % (key, json.dumps(server['command'][0])),
                 '-c', '%s.args=%s' % (key, json.dumps(server['command'][1:]))]
    return args


def command(runner, brief, worktree, project=None, servers=()):
    """argv for one non-interactive spawn session; the brief is the whole instruction."""
    host = hosts(project).get(runner)
    if not host or host['kind'] != 'spawn':
        raise ValueError('Not a spawn host: ' + runner)
    mcp = codex_mcp_args(servers) if host.get('mcp_style') == 'codex-config' else []
    return registry.render(host, mcp=mcp, brief=brief, cwd=worktree, notify=NOTIFY)


def handoff(runner, title, worktree, brief, project=None):
    """Launch spec for a desktop host. The brief also sits in the worktree for hosts that can't take a prompt."""
    host = hosts(project)[runner]
    spec = {'host': runner, 'via': host['via'], 'cwd': str(worktree), 'title': title[:58],
            'prompt': brief + '\n\n(The same brief is in .mstack/cache/brief.md in this folder.)'}
    if host['via'] == 'owner':
        spec['instructions'] = ('Open %s in %s and send: "Read .mstack/cache/brief.md and do the task."'
                                % (worktree, runner.replace('-', ' ').title()))
    return spec


def kind(runner, project=None):
    return hosts(project)[runner]['kind']


def available(runner, project=None):
    host = hosts(project).get(runner)
    return bool(host) and registry.available(host, project)


def choose(preferred, allowed, project=None):
    """The task's assigned agent if allowed and available, else the first available allowed host."""
    for runner in [preferred, *allowed]:
        if runner in allowed and available(runner, project):
            return runner
    raise ValueError('No allowed worker host is available: ' + ', '.join(allowed))
