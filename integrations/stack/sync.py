"""Bring projects that use mstack up to date with mstack itself.

mstack keeps growing: new skills, new ignore rules, a changed project skill, config
fields that move. `mstack sync` updates what mstack owns inside each project. It is
idempotent; run it as often as you like:

- **config migrations:** ordered, versioned edits to `.mstack/stack.json` (MIGRATIONS);
- **`.mstack/.gitignore`:** rules for generated or private files;
- **skill links:** the mstack skill group in `.agents/skills` and `.claude/skills`, for
  projects that already link them: new skills are linked, dangling ones removed;
- **the generated project skill:** `.agents/skills/mstack/SKILL.md`, only while it is
  unedited (a locally edited copy is reported, never overwritten);
- **local visibility:** the `.git/info/exclude` block.

Team files (AGENTS.md, .gitignore, tracked .mcp.json, …) are never touched, nothing is
committed, and no service, tenant or credential changes. Each project records what it
was synced to in `.mstack/state.json` (`runtime.mstack_sync`).

Known projects are registered in mstack's `.mstack/projects.json` by `init`, `skills`
and `sync --project`, plus every project with a board table.

  mstack sync --project PATH [--check]
  mstack sync --all [--check]
  mstack sync --hook        # run `sync --all` after every mstack commit or merge
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import cli
import config as intent
import project_state
import visibility

STACK_ROOT = cli.STACK_ROOT
REGISTRY = STACK_ROOT/'.mstack/projects.json'
BOARD_STATE = STACK_ROOT/'.mstack/evidence/taskboard-test.json'


# (version, what it does, fn(config dict) -> list of changes). Append only; never edit a shipped one.
# Version 1 is the baseline: projects synced before any migration existed.
MIGRATIONS = [
    (1, 'baseline', lambda config: []),
]
VERSION = MIGRATIONS[-1][0]
HOOK = '#!/bin/sh\n# mstack: keep projects that use mstack up to date (installed by `mstack sync --hook`)\n' \
       '"%s/mstack" sync --all --quiet >/dev/null 2>&1 &\n'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def code_version():
    head = subprocess.run(['git', '-C', str(STACK_ROOT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True)
    return head.stdout.strip() or None


def projects():
    """Every project known to use mstack: the registry plus board tables, existing ones only."""
    found = []
    if REGISTRY.exists():
        found += json.loads(REGISTRY.read_text()).get('projects', [])
    if BOARD_STATE.exists():
        found += [t.get('path') for t in json.loads(BOARD_STATE.read_text()).get('tables', {}).values()]
    out = []
    for path in found:
        if path and Path(path).resolve() not in out and (Path(path)/'.mstack/stack.json').is_file():
            out.append(Path(path).resolve())
    return out


def register(project):
    project = str(Path(project).resolve())
    if project == str(STACK_ROOT):
        return
    known = json.loads(REGISTRY.read_text()).get('projects', []) if REGISTRY.exists() else []
    if project not in known:
        REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY.write_text(json.dumps({'projects': sorted(known + [project])}, indent=2) + '\n')


def sync_project(project, check=False):
    """Bring one project up to date; with check=True only report what would change."""
    project = Path(project).resolve()
    stack = project/'.mstack/stack.json'
    if not stack.is_file():
        raise ValueError('%s does not use mstack (no .mstack/stack.json)' % project)
    changes, notes = [], []
    synced = project_state.read(project)['runtime'].get('mstack_sync') or {}
    done = synced.get('version', 0)

    # 1. Config migrations, in order.
    config = json.loads(stack.read_text())
    for version, what, migrate in MIGRATIONS:
        if version > done:
            changes += ['config: ' + c for c in migrate(config)]
    if any(c.startswith('config: ') for c in changes) and not check:
        stack.write_text(json.dumps(config, indent=2) + '\n')

    # 2. .mstack/.gitignore rules.
    ignore = project/'.mstack/.gitignore'
    prior = ignore.read_text().splitlines() if ignore.exists() else []
    missing = [r for r in project_state.IGNORED if r not in prior]
    if missing:
        changes.append('.mstack/.gitignore: + ' + ' '.join(missing))
        if not check:
            project_state.ignored(project)

    # 3. Skill links (only where the project already links the skill group).
    if project != STACK_ROOT:
        for folder in ('.agents/skills', '.claude/skills'):
            base = project/folder
            links = {p.name: p for p in base.glob('mstack-*')} if base.is_dir() else {}
            if not any(l.is_symlink() for l in links.values()):
                continue
            for name, link in links.items():
                if link.is_symlink() and not link.exists():
                    changes.append('%s/%s: removed (no longer in mstack)' % (folder, name))
                    if not check:
                        link.unlink()
            for name in cli.SKILLS:
                target, source = base/name, STACK_ROOT/'.agents/skills'/name
                if target.is_symlink() and target.resolve() == source.resolve():
                    continue
                if target.exists() and not target.is_symlink():
                    notes.append('%s/%s is a real folder, not an mstack link; left alone' % (folder, name))
                    continue
                changes.append('%s/%s: linked' % (folder, name))
                if not check:
                    if target.is_symlink():
                        target.unlink()
                    target.symlink_to(source)

    # 4. The generated project skill, while unedited.
    skill = project/'.agents/skills/mstack/SKILL.md'
    if project == STACK_ROOT:
        pass                                  # mstack's own skill is the source, not a generated copy
    elif skill.is_file():
        now, fresh = skill.read_text(), cli.skill_text()
        if now != fresh:
            if digest(now) == synced.get('skill'):
                changes.append('.agents/skills/mstack/SKILL.md: updated')
                if not check:
                    skill.write_text(fresh)
            else:
                notes.append('.agents/skills/mstack/SKILL.md was edited here; not updated (compare with `mstack sync`'
                             ' template, or delete it and re-run sync)')
    elif project != STACK_ROOT and (project/'.agents/skills').is_dir():
        changes.append('.agents/skills/mstack/SKILL.md: created')
        if not check:
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text(cli.skill_text())

    # 5. Local visibility block.
    if config.get('visibility') == 'local' and visibility.repository(project):
        top, exclude = visibility.repository(project)
        want = visibility.rules(project, top)
        text = exclude.read_text() if exclude.exists() else ''
        block = text.split(visibility.BEGIN, 1)[1].split(visibility.END, 1)[0].split() if visibility.BEGIN in text else []
        if block != want:
            changes.append('.git/info/exclude: mstack block updated')
            if not check:
                visibility.apply(project, True)

    # 6. Role-card hook, for projects with a task board (personal Claude settings only).
    if project != STACK_ROOT and config.get('taskboard'):
        sys.path.insert(0, str(STACK_ROOT/'integrations/agents'))
        import roles
        settings = project/'.claude/settings.local.json'
        present = settings.exists() and roles.MARK in settings.read_text()
        if not present:
            changes.append('.claude/settings.local.json: role-card hook added')
            if not check:
                roles.install(project)
        # Worker worktrees inside the project are their own Claude project folders: give them the hook too.
        runs = json.loads(BOARD_STATE.read_text()).get('runs', {}).values() if BOARD_STATE.exists() else []
        for run in runs:
            tree = Path(run.get('tree') or '')
            if not run.get('tree') or not tree.is_dir() or project not in tree.resolve().parents:
                continue
            local = tree/'.claude/settings.local.json'
            if not (local.exists() and roles.MARK in local.read_text()):
                changes.append('%s: role-card hook added (worker %s)' % (tree.relative_to(project)/'.claude/settings.local.json',
                                                                          run.get('issue') or '?'))
                if not check:
                    roles.install(tree)

    # 7. The config still validates against the current schema.
    try:
        intent.project_config(project)
    except (ValueError, KeyError) as error:
        notes.append('config does not validate against this mstack: %s' % error)

    record = {'version': VERSION, 'code': code_version(),
              'skill': digest(skill.read_text()) if skill.is_file() and not check and project != STACK_ROOT
              else synced.get('skill')}
    if not check:
        with project_state.edit(project) as state:
            state['runtime']['mstack_sync'] = {**record, 'at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        register(project)
    return {'project': str(project), 'changes': changes, 'notes': notes,
            'up_to_date': not changes, 'checked_only': check, 'synced_to': record['version']}


def pending(project):
    """Cheap preflight for doctor: what `sync` would change, without writing anything."""
    try:
        return sync_project(project, check=True)['changes']
    except (ValueError, OSError) as error:
        return ['sync check failed: %s' % error]


def install_hook():
    written = []
    hooks = Path(subprocess.run(['git', '-C', str(STACK_ROOT), 'rev-parse', '--git-path', 'hooks'],
                                capture_output=True, text=True, check=True).stdout.strip())
    hooks = hooks if hooks.is_absolute() else STACK_ROOT/hooks
    for name in ('post-commit', 'post-merge'):
        path = hooks/name
        if path.exists() and 'mstack sync' not in path.read_text():
            raise ValueError('%s already exists and is not mstack\'s; add `mstack sync --all` to it yourself' % path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(HOOK % STACK_ROOT)
        path.chmod(0o755)
        written.append(str(path))
    return {'hooks': written}


def main(argv):
    p = argparse.ArgumentParser(prog='mstack sync', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    which = p.add_mutually_exclusive_group(required=True)
    which.add_argument('--project', type=Path)
    which.add_argument('--all', action='store_true')
    which.add_argument('--hook', action='store_true', help='install git hooks in mstack that run `sync --all`')
    p.add_argument('--check', action='store_true', help='only report what would change')
    p.add_argument('--quiet', action='store_true')
    args = p.parse_args(argv)
    try:
        if args.hook:
            result = install_hook()
        elif args.all:
            result = []
            for project in projects():
                try:
                    result.append(sync_project(project, args.check))
                except (ValueError, OSError) as error:
                    result.append({'project': str(project), 'error': str(error)})
        else:
            result = sync_project(args.project, args.check)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('mstack sync: %s' % error, file=sys.stderr)
        return 1
    if not args.quiet:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
