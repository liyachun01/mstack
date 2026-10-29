#!/usr/bin/python3
"""Repo-owned compatibility commands for the installed Linux mise toolchain.

The owner may symlink command names to this file. Resolution never installs tools
and uses the repository baseline instead of a user-global tool configuration.
The private child invocation restores the caller's cwd after mise selects a scope.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[2]
MISE = Path.home() / '.local/bin/mise'
PYTHON = Path('/usr/bin/python3')
BASELINE = ROOT / 'infra/toolchains/orb-devbox'
NODE_CLI = ROOT / 'infra/toolchains/node-cli'
PYTHON_SCOPE = ROOT / 'infra/toolchains/python'
DEEPSEEK = ROOT / 'infra/harnesses/deepseek'
COMMON = {'gh', 'bun', 'bunx', 'direnv',
          'fd', 'fdfind', 'fzf', 'jq', 'rg', 'shellcheck', 'shfmt', 'tmux'}
PROJECT_NODE = {'node', 'npm', 'npx', 'corepack', 'pnpm'}
NODE_BINARIES = {'node', 'npm', 'npx', 'corepack'}
NODE_COMMANDS = PROJECT_NODE | {'ve', 'vefaas', 've-tos-cli'}
PYTHON_COMMANDS = {'uv', 'uvx'}


def guarded_environment(environ):
    env = dict(environ)
    env.pop('MISE_CONFIG_FILE', None)
    env['MISE_GLOBAL_CONFIG_FILE'] = str(BASELINE / 'mise.toml')
    env['MISE_INSTALL_MISSING_TOOLS'] = '0'
    env['MISE_NOT_FOUND_AUTO_INSTALL'] = '0'
    return env


def mise_output(scope, arguments, env):
    try:
        result = subprocess.run([str(MISE), '-C', str(scope), *arguments],
                                env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        # Config/template diagnostics can contain private environment values.
        raise ValueError('mise could not resolve installed tools; check trusted configuration') from exc
    return result.stdout.strip()


def configured_override(records, tool_names, label):
    selected = [(name, entries) for name, entries in records.items()
                if name in tool_names and entries]
    if not selected:
        return None
    if len(selected) != 1 or len(selected[0][1]) != 1:
        raise ValueError(f'Expected one configured project {label} version')
    name, entries = selected[0]
    entry = entries[0]
    if not entry.get('installed') or not entry.get('version'):
        raise ValueError(f'Configured project {label} is missing; no fallback was selected')
    return f'{name}@{entry["version"]}'


def caller_overrides(alias, cwd, env):
    try:
        records = json.loads(mise_output(cwd, ['ls', '--current', '--json'], env))
    except json.JSONDecodeError as exc:
        raise ValueError('Invalid installed-tool information from mise') from exc
    if not isinstance(records, dict):
        raise ValueError('Invalid installed-tool information from mise')
    if alias in PYTHON_COMMANDS:
        python = configured_override(records, {'python'}, 'Python')
        return [python] if python else []
    overrides = []
    node = configured_override(records, {'node'}, 'Node')
    if node:
        overrides.append(node)
    if alias == 'pnpm':
        pnpm = configured_override(records, {'pnpm', 'npm:pnpm'}, 'pnpm')
        if pnpm:
            overrides.append(pnpm)
    return overrides


def installed_executable(scope, arguments, env):
    resolved = Path(mise_output(scope, arguments, env))
    if not resolved.is_absolute() or not resolved.is_file() or resolved.resolve() == SCRIPT:
        raise ValueError('Configured mise executable absent; no system/PATH fallback was selected')
    return resolved


def command_plan(alias, arguments, cwd, environ):
    """Return an exec argv/environment without changing cwd or starting a tool."""
    if alias in COMMON:
        scope = BASELINE
    elif alias in NODE_COMMANDS:
        scope = NODE_CLI
    elif alias in PYTHON_COMMANDS:
        scope = PYTHON_SCOPE
    elif alias == 'dsh':
        scope = DEEPSEEK
    else:
        raise ValueError('Unknown compatibility command')
    env = guarded_environment(environ)
    overrides = caller_overrides(alias, cwd, env) if alias in PROJECT_NODE | PYTHON_COMMANDS else []
    executable = 'fd' if alias == 'fdfind' else alias
    which = ['which', executable]
    requested = next((item for item in overrides
                      if (item.startswith('node@') and alias in NODE_BINARIES)
                      or (alias == 'pnpm' and item.startswith(('pnpm@', 'npm:pnpm@')))), None)
    if requested:
        which.extend(['--tool', requested])
    resolved = installed_executable(scope, which, env)
    if alias in PYTHON_COMMANDS and 'UV_PYTHON' not in env:
        python_which = ['which', 'python']
        if overrides:
            python_which.extend(['--tool', overrides[0]])
        env['UV_PYTHON'] = str(installed_executable(scope, python_which, env))
    command = [str(MISE), '-C', str(scope), 'exec', '--no-deps', *overrides, '--',
               str(PYTHON), str(SCRIPT), '--child', str(cwd), str(resolved), *arguments]
    return command, env


def child_exec(arguments):
    if len(arguments) < 2:
        raise ValueError('Incomplete internal toolchain invocation')
    cwd, executable, *user_arguments = arguments
    if not Path(cwd).is_absolute() or not Path(executable).is_absolute():
        raise ValueError('Internal invocation requires absolute paths')
    if not Path(executable).is_file() or Path(executable).resolve() == SCRIPT:
        raise ValueError('Internal executable absent or recursive')
    os.chdir(cwd)
    env = dict(os.environ)
    env['PWD'] = cwd
    os.execvpe(executable, [executable, *user_arguments], env)


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    invoked = Path(argv[0]).name
    arguments = argv[1:]
    if invoked == SCRIPT.name:
        if arguments[:1] == ['--child']:
            child_exec(arguments[1:])
            return
        if not arguments:
            raise ValueError('Specify a compatibility command or invoke its symlink')
        invoked, *arguments = arguments
    command, env = command_plan(invoked, arguments, Path.cwd(), os.environ)
    os.execvpe(str(MISE), command, env)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print(f'mcp-stack toolchain: {exc}', file=sys.stderr)
        sys.exit(1)
