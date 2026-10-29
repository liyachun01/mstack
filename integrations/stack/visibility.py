"""Local visibility: keep a project's mstack files out of its codebase.

Uses this clone's `.git/info/exclude`, never the team's `.gitignore`, so teammates
who do not use mstack see no change. Nothing is untracked automatically: files
already committed are reported for the owner to remove with `git rm --cached`.
"""
from pathlib import Path
import subprocess

# Personal mstack files. Team files (AGENTS.md, .gitignore, .claude/settings.json) are never listed.
LOCAL_PATHS = ('.mstack/', '.agents/skills/mstack/', 'CLAUDE.local.md', '.claude/settings.local.json',
               '.agents/skills/mstack-*', '.claude/skills/mstack-*')
# mstack's only when the team does not track it (worktree MCP wiring); a tracked one is a team file.
OPTIONAL_PATHS = ('.mcp.json',)
BEGIN, END = '# >>> mstack local (managed) >>>', '# <<< mstack local <<<'


def git(project, *args):
    result = subprocess.run(['git', '-C', str(project), *args], capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def repository(project):
    code, top = git(project, 'rev-parse', '--show-toplevel')
    if code:
        return None
    code, exclude = git(project, 'rev-parse', '--git-path', 'info/exclude')
    exclude = Path(exclude)
    return Path(top).resolve(), exclude if exclude.is_absolute() else (Path(project)/exclude).resolve()


def owned_paths(project):
    """mstack's local paths for this repo: the core set plus optional ones the team does not track."""
    tracked = set(git(project, 'ls-files', '--', *OPTIONAL_PATHS)[1].splitlines())
    return LOCAL_PATHS + tuple(p for p in OPTIONAL_PATHS if p not in tracked)


def rules(project, top):
    prefix = Path(project).resolve().relative_to(top).as_posix()
    return ['/' + (prefix + '/' if prefix != '.' else '') + path for path in owned_paths(project)]


def apply(project, local):
    """Write (local) or remove (shared) the managed block in .git/info/exclude."""
    repo = repository(project)
    if not repo:
        return {'git': False, 'changed': False}
    top, exclude = repo
    text = exclude.read_text() if exclude.exists() else ''
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        text = head.rstrip('\n') + ('\n' if head.strip() else '') + rest.split(END, 1)[1].lstrip('\n')
    if local:
        text = text.rstrip('\n') + ('\n' if text.strip() else '') + '\n'.join([BEGIN, *rules(project, top), END]) + '\n'
    before = exclude.read_text() if exclude.exists() else ''
    if text != before:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text(text)
    return {'git': True, 'exclude_file': str(exclude), 'changed': text != before}


def status(project):
    """Tracked or unignored mstack files that would leak into the codebase."""
    repo = repository(project)
    if not repo:
        return {'git': False, 'tracked': [], 'unignored': []}
    project = Path(project).resolve()
    paths = owned_paths(project)
    _, tracked = git(project, 'ls-files', '--', *paths)
    unignored = [path for path in paths
                 if (project/path).exists() and git(project, 'check-ignore', '-q', '--', path)[0] != 0]
    return {'git': True, 'tracked': tracked.splitlines(), 'unignored': unignored}
