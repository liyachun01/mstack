"""Make a checkout of the private mstack repo usable on this machine, and guard what leaves it.

  mstack hydrate          install the private-name filter, put real names back into the
                          checkout, and list secret files that still need restoring
  mstack hydrate --check  verify that no private value is in any commit or the index
                          (run before every push; exits 2 if something leaked)

The repo stores `{{mstack:KEY}}` placeholders (see integrations/stack/private_filter.py and
docs/PRIVATE-REPO.md). Real values live in `.mstack/private.json`, secrets in `.secrets/` and
the other files listed in infra/secrets-inventory.json. None of these are ever committed.
"""
import argparse
import json
import subprocess
import sys

import private_filter

ROOT = private_filter.ROOT
FILTER = 'mstack-private'


def git(*args, check=True):
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True, check=check)


def install_filter():
    script = 'python3 "%s"' % (ROOT/'integrations/stack/private_filter.py')
    for key, value in (('clean', script + ' clean'), ('smudge', script + ' smudge'), ('required', 'true')):
        git('config', 'filter.%s.%s' % (FILTER, key), value)


def rehydrate():
    """Rewrite checked-out files that still show placeholders (a fresh clone), if unmodified."""
    found = git('grep', '-l', '-F', '{{mstack:', '--', '.', ':!integrations/stack/private_filter.py',
                ':!integrations/stack/hydrate.py', ':!docs/PRIVATE-REPO.md', ':!.gitattributes', check=False).stdout.split()
    if not found:
        return []
    dirty = set(git('diff', '--name-only', '--', *found).stdout.split())
    redo = [f for f in found if f not in dirty]
    for name in redo:
        (ROOT/name).unlink()
    if redo:
        git('checkout', '--', *redo)
    return redo


def missing_secrets():
    inventory = json.loads((ROOT/'infra/secrets-inventory.json').read_text())
    return [f['path'] for f in inventory['files'] if not (ROOT/f['path']).is_file()]


def leaks():
    """Private values anywhere git would push: every commit on every branch, and the index."""
    values = [real for real, _ in private_filter.pairs()]
    commits = git('rev-list', '--all', check=False).stdout.split()
    found = {}
    for value in values:
        hits = set()
        for start in range(0, len(commits), 200):
            out = git('grep', '-l', '-F', '-e', value, *commits[start:start + 200], check=False).stdout
            hits |= {line.split(':', 1)[1] for line in out.splitlines() if ':' in line}
        cached = git('grep', '--cached', '-l', '-F', '-e', value, check=False).stdout.split()
        hits |= set(cached)
        if hits:
            found[value[:3] + '…'] = sorted(hits)[:10]
    return found


def main(argv):
    p = argparse.ArgumentParser(prog='mstack hydrate', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true', help='only verify nothing private is committed')
    args = p.parse_args(argv)
    if not private_filter.VALUES.is_file():
        print('mstack hydrate: %s is missing. Copy .mstack/private.example.json there and fill in the values.'
              % private_filter.VALUES, file=sys.stderr)
        return 1
    if args.check:
        found = leaks()
        print(json.dumps({'clean': not found, 'leaks': found}, indent=2, ensure_ascii=False))
        return 2 if found else 0
    install_filter()
    result = {'filter': FILTER, 'rehydrated': rehydrate(), 'missing_secrets': missing_secrets()}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
