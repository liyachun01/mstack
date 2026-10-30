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


def dsh_patch(servers, cache):
    """Per-run `--patch` overlay for DeepSeek Harness: one dsh-mcp-client row per stdio server, written into the
    worktree's .mstack/cache/ (never ~/.dsh). JSON is valid YAML, so no YAML writer is needed. The stdio row keys
    (command/args) mirror the streamable-http rows in infra/harnesses/deepseek; qualification confirms them (doc 015)."""
    if not servers:
        return []
    rows = [{'id': 'mstack-' + s['name'], 'name': '@deepseek-ai/dsh-mcp-client',
             'config': {'serverName': s['name'], 'transport': 'stdio', 'command': s['command'][0],
                        'args': s['command'][1:], 'failOnStartupError': False, 'reconnect': {'enabled': False}}}
            for s in servers]
    path = Path(cache)/'dsh-mcp.patch.yml'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('# Written by mstack for this run only (mcp_style: dsh-patch).\n'
                    + json.dumps([{'insert': rows}], indent=2) + '\n')
    return ['--patch', str(path)]


def command(runner, brief, worktree, project=None, servers=(), session=None, cache=None):
    """argv for one non-interactive spawn session; the brief is the whole instruction. With `session`, a host
    that has `resume` arguments continues that session and `brief` is the new turn's prompt."""
    host = hosts(project).get(runner)
    if not host or host['kind'] != 'spawn':
        raise ValueError('Not a spawn host: ' + runner)
    style = host.get('mcp_style')
    mcp = codex_mcp_args(servers) if style == 'codex-config' else \
        dsh_patch(servers, cache or Path(worktree)/'.mstack/cache') if style == 'dsh-patch' else []
    if session and not host.get('resume'):
        raise ValueError('%s cannot resume a session' % runner)
    resume = registry.fill(host['resume'], {'session': session}) if session else []
    return registry.render(host, mcp=mcp, resume=resume, brief=brief, cwd=worktree, notify=NOTIFY)


def can_resume(runner, project=None):
    return bool((hosts(project).get(runner) or {}).get('resume'))


STREAM = {'kind_keys': ['type', 'event', 'kind'], 'session_events': ['session'],
          'session_keys': ['session_id', 'sessionId', 'id', 'session.id'], 'final_events': ['final'],
          'text_keys': ['text', 'content', 'message'], 'error_events': ['error']}


class Stream:
    """Reads a host's NDJSON event stream (manifest `stream`), line by line: the session id, the final text and
    errors. Lines that aren't JSON objects (stderr, banners) are kept as plain output. Field names come from the
    manifest, so a harness that renames an event needs a manifest edit, not code."""
    def __init__(self, runner, project=None):
        host = hosts(project).get(runner) or {}
        self.on = 'stream' in host
        self.conf = {**STREAM, **(host.get('stream') or {})}
        self.session, self.final, self.errors, self.plain, self.exit = None, None, [], [], None

    def _get(self, event, keys):
        for key in keys:
            value = event
            for part in key.split('.'):
                value = value.get(part) if isinstance(value, dict) else None
            if isinstance(value, (str, int)) and str(value):
                return str(value)
        return None

    def feed(self, line):
        """One output line; returns the session id when this line first reveals it."""
        try:
            event = json.loads(line) if self.on else None
        except ValueError:
            event = None
        if not isinstance(event, dict):
            if line.strip():
                self.plain.append(line.rstrip())
            return None
        kind = self._get(event, self.conf['kind_keys'])
        if kind in self.conf['final_events']:
            self.final = self._get(event, self.conf['text_keys']) or self.final
        elif kind in self.conf['error_events']:
            self.errors.append(self._get(event, self.conf['text_keys']) or json.dumps(event)[:300])
        elif kind in self.conf['session_events'] and not self.session:
            self.session = self._get(event, self.conf['session_keys'])
            return self.session
        return None

    def summary(self):
        """What the run said last: its final text, else its errors, else the tail of its plain output."""
        if self.final:
            return self.final
        return '\n'.join(self.errors or self.plain)


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
