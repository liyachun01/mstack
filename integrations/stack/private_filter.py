"""Keep private names out of the mstack repository while the checkout keeps the real ones.

A git clean/smudge filter (`.gitattributes`: `filter=mstack-private`):
- clean (on `git add`): every private value becomes its placeholder, e.g. `{{mstack:MAC_USER}}`;
- smudge (on checkout): every placeholder becomes the private value again.

So commits and GitHub hold placeholders, and your working tree holds real paths and names.
Values come from `.mstack/private.json`, which is never committed; `.mstack/private.example.json`
lists the keys. Clean fails without the values file, so nothing is committed unfiltered by accident.

  python3 private_filter.py clean|smudge < in > out
  python3 private_filter.py clean-tree DIR      (rewrite the text files under DIR in place)
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
VALUES = ROOT/'.mstack/private.json'
# Every file goes through the filter; anything that isn't UTF-8 text passes through untouched.


def placeholder(key):
    return '{{mstack:%s}}' % key


def pairs(path=None):
    """(real, placeholder) pairs, longest real value first so no value eats part of another."""
    path = path or VALUES
    if not path.is_file():
        raise SystemExit('mstack private filter: %s is missing; copy .mstack/private.example.json and fill it in '
                         '(or run `mstack hydrate`)' % path)
    values = json.loads(path.read_text())['values']
    out = [(real, placeholder(key)) for key, real in values.items() if real]
    return sorted(out, key=lambda p: -len(p[0]))


def clean(text, table):
    for real, mark in table:
        text = text.replace(real, mark)
    return text


def smudge(text, table):
    for real, mark in table:
        text = text.replace(mark, real)
    return text


def clean_tree(folder, table):
    changed = 0
    for path in Path(folder).rglob('*'):
        if '.git' in path.parts or not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        new = clean(text, table)
        if new != text:
            path.write_text(new)
            changed += 1
    return changed


def main(argv):
    mode = argv[0] if argv else ''
    if mode == 'clean-tree':
        print('cleaned %d files' % clean_tree(argv[1], pairs()), file=sys.stderr)
        return 0
    if mode not in ('clean', 'smudge'):
        print(__doc__, file=sys.stderr)
        return 2
    data = sys.stdin.buffer.read()
    try:
        text = data.decode()
    except UnicodeDecodeError:
        sys.stdout.buffer.write(data)              # binary: pass through untouched
        return 0
    if mode == 'smudge' and not VALUES.is_file():
        sys.stdout.buffer.write(data)              # not hydrated yet: keep the placeholders
        return 0
    table = pairs()
    sys.stdout.buffer.write((clean(text, table) if mode == 'clean' else smudge(text, table)).encode())
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
