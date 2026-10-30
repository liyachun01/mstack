"""Launch DeepSeek Harness (dsh) for an mstack agent, with MST-56's qualified settings.

  python3 dsh_launch.py [--dry-run | --check] [--profile headless|acp|sdk] [dsh args...]

The `dsh` agent plugin calls this for every worker turn (`--profile headless ... --json <brief>`); a long-lived
agent (ACP/SDK over stdio, MST-64) uses the same launcher with another profile. It never installs or updates
anything and never reads or writes `~/.dsh`:

- pinned Node and dsh, resolved from the existing mise installs (`deepseek_launch.installed_tool_root`);
- a clean environment (`env -i` style): PATH, HOME, LANG, `DSH_HOME` = `infra/harnesses/deepseek/state/worker-home`
  of the mstack checkout, telemetry off, `DEEPSEEK_API_KEY` from `.secrets/deepseek-worker.key`, and the caller's
  `MSTACK_*` task binding;
- the worker overlay `infra/harnesses/deepseek/worker/worker.cordis.yml` (session-log upload off, web tools off)
  as the first `--patch`, before any per-run patch (mstack's MCP rows).

`--dry-run` prints the exact argv and environment (the key as `<redacted>`) and starts nothing. `--check` runs
dsh's own `--dump-config` (no model call) and verifies the composed tree: session-log upload and web tools off.
Otherwise the process is replaced by dsh (exec), so signals sent to it reach dsh directly.

Tests set MSTACK_DSH_FAKE to a fake executable that runs in place of `node <dsh>/lib/bin.js` with the same
environment (FAKE_DSH_* knobs pass through only then) and MSTACK_DSH_STATE_ROOT to a synthetic key and DSH_HOME.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deepseek_launch

CODE_ROOT = HERE.parents[1]
OVERLAY = CODE_ROOT/'infra/harnesses/deepseek/worker/worker.cordis.yml'
PROFILES = ('headless', 'acp', 'sdk')
PASS_PREFIXES = ('MSTACK_',)


def state_root():
    """Where private state lives: the main mstack checkout, also when this code runs from a task worktree (its
    `.secrets/` and `infra/.../state/` are ignored, so they exist only in the main checkout). Tests point
    MSTACK_DSH_STATE_ROOT at a synthetic one."""
    if os.environ.get('MSTACK_DSH_STATE_ROOT'):
        return Path(os.environ['MSTACK_DSH_STATE_ROOT'])
    try:
        common = subprocess.run(['git', '-C', str(CODE_ROOT), 'rev-parse', '--path-format=absolute',
                                 '--git-common-dir'], capture_output=True, text=True, check=True, timeout=10)
        return Path(common.stdout.strip()).parent
    except (OSError, subprocess.SubprocessError):
        return CODE_ROOT


def worker_key(root):
    path = root/'.secrets/deepseek-worker.key'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Worker key absent: %s' % path)
    if path.stat().st_mode & 0o077:
        raise ValueError('Worker key must be 0600: %s' % path)
    key = path.read_text().strip()
    if not key.startswith('sk-') or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError('Unexpected DeepSeek key format in %s' % path)
    return key


def entry():
    """[node, <dsh>/lib/bin.js] of the pinned installs, or the test fake."""
    fake = os.environ.get('MSTACK_DSH_FAKE')
    if fake:
        return [fake], Path(fake).parent
    node_root = deepseek_launch.installed_tool_root('node', deepseek_launch.NODE_VERSION)
    prefix = deepseek_launch.installed_tool_root('npm:@deepseek-ai/dsh', deepseek_launch.HARNESS_VERSION)
    found = [prefix/rel for rel in ('node_modules/@deepseek-ai/dsh', 'lib/node_modules/@deepseek-ai/dsh')
             if (prefix/rel/'package.json').is_file()]
    if len(found) != 1:
        raise ValueError('Expected one installed dsh package in the mise prefix')
    meta = json.loads((found[0]/'package.json').read_text())
    if meta.get('version') != deepseek_launch.HARNESS_VERSION:
        raise ValueError('Installed dsh version changed; requalify before launch')
    return [str(node_root/'bin/node'), str(found[0]/'lib/bin.js')], node_root/'bin'


def build(profile, args, root=None, caller_env=None):
    """(argv, env) for one dsh process. `args` follow the profile and the worker overlay unchanged."""
    if profile not in PROFILES:
        raise ValueError('Unknown dsh profile: %s' % profile)
    root = root or state_root()
    caller_env = os.environ if caller_env is None else caller_env
    home = root/'infra/harnesses/deepseek/state/worker-home'
    if not home.is_dir():
        raise ValueError('Worker DSH_HOME absent (created by the MST-56 qualification): %s' % home)
    if not OVERLAY.is_file():
        raise ValueError('Worker overlay absent: %s' % OVERLAY)
    program, bin_dir = entry()
    env = {'PATH': '%s:/usr/bin:/bin' % bin_dir, 'HOME': str(Path.home()), 'LANG': 'C.UTF-8',
           'DSH_HOME': str(home), 'DSH_TELEMETRY_DISABLED': '1', 'DSH_TELEMETRY_MODE': 'DISABLED',
           'NODE_DISABLE_COMPILE_CACHE': '1', 'DEEPSEEK_API_KEY': worker_key(root)}
    prefixes = PASS_PREFIXES + (('FAKE_DSH_',) if 'MSTACK_DSH_FAKE' in caller_env else ())
    env.update({k: v for k, v in caller_env.items() if k.startswith(prefixes) and k not in env})
    return [*program, '--profile', profile, '--patch', str(OVERLAY), *args], env


def shown(argv, env):
    return {'argv': argv, 'env': {k: '<redacted>' if k == 'DEEPSEEK_API_KEY' else v for k, v in sorted(env.items())},
            'cwd': os.getcwd(), 'model_requests': 0}


def check(argv, env):
    """dsh --dump-config on the composed profile (no model call): the qualified switches are in effect."""
    out = subprocess.run([*argv, '--dump-config'], env=env, capture_output=True, text=True, timeout=120,
                         stdin=subprocess.DEVNULL)
    if out.returncode:
        raise ValueError('dsh --dump-config failed (exit %d): %s' % (out.returncode, out.stderr[-500:]))
    tree = out.stdout
    blocks = {}
    for block in tree.split('\n- id: ')[1:]:
        blocks[block.split('\n', 1)[0].strip()] = block
    failed = [name for name in ('tool-web', 'web', 'web-search-deepseek', 'web-fetch-http')
              if name in blocks and 'disabled: true' not in blocks[name]]
    if 'enabled: false' not in blocks.get('session-log-deepseek', 'enabled: false'):
        failed.append('session-log-deepseek')
    return {'check': 'fail' if failed else 'pass', 'not_off': failed, 'patches': argv.count('--patch'),
            'mcp_rows': sorted(n for n in blocks if n.startswith('mstack-')), 'model_requests': 0}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    mode = args.pop(0) if args and args[0] in ('--dry-run', '--check') else None
    profile = 'headless'
    if args[:1] == ['--profile']:
        profile = args[1]
        args = args[2:]
    cmd, env = build(profile, args)
    if mode == '--dry-run':
        print(json.dumps(shown(cmd, env), indent=2))
        return 0
    if mode == '--check':
        result = check(cmd, env)
        print(json.dumps(result, indent=2))
        return 0 if result['check'] == 'pass' else 1
    os.execve(cmd[0], cmd, env)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except ValueError as exc:
        print('dsh launch refused: %s' % exc, file=sys.stderr)
        sys.exit(2)
