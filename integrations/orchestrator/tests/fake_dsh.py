"""Fake DeepSeek Harness for tests (no model): speaks the headless NDJSON stream mstack's `dsh` manifest expects
(a non-JSON banner line, `session`, `text`, `final`), resumes with --session-id, and commits one line per turn.

Env knobs: FAKE_DSH_ARGV (append each argv as a JSON line), FAKE_DSH_SLEEP (seconds mid-turn),
FAKE_DSH_DONE (state file: record a `board done` report for MSTACK_TASK, as a worker that reported itself would),
FAKE_DSH_QUEUE (state file: queue an owner comment on the run during the first turn, as a forward would)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

args = sys.argv[1:]
if os.environ.get('FAKE_DSH_ARGV'):
    with open(os.environ['FAKE_DSH_ARGV'], 'a') as log:
        log.write(json.dumps(args) + '\n')
resumed = '--session-id' in args
session = args[args.index('--session-id') + 1] if resumed else 'fake-' + uuid.uuid4().hex[:8]
prompt = args[-1]


def emit(**event):
    print(json.dumps(event), flush=True)


print('dsh 0.2.0-rc.2 (fake) headless', flush=True)
emit(type='session', session_id=session)
emit(type='text', text='working on it')
time.sleep(float(os.environ.get('FAKE_DSH_SLEEP') or 0))
with open('dsh-turns.md', 'a') as notes:
    notes.write('- %s\n' % (prompt.splitlines() or [''])[0][:80])
subprocess.run(['git', 'add', 'dsh-turns.md'], check=True)
subprocess.run(['git', '-c', 'user.name=fake dsh', '-c', 'user.email=dsh@mstack.local', 'commit', '-q', '-m',
                'fake dsh turn'], check=True)
task = os.environ.get('MSTACK_TASK')
for knob in ('FAKE_DSH_DONE', 'FAKE_DSH_QUEUE'):
    if os.environ.get(knob) and not (knob == 'FAKE_DSH_QUEUE' and resumed):
        path = Path(os.environ[knob])
        state = json.loads(path.read_text())
        run = state['runs'][task]
        if knob == 'FAKE_DSH_DONE':
            run['report'] = {'kind': 'done', 'ts': time.time(), 'text': 'reported by the worker itself'}
        else:
            run.setdefault('queued', []).append({'text': 'Also add a test please', 'at': 'now'})
        path.write_text(json.dumps(state))
emit(type='final', text='Fake dsh finished: ' + (prompt.splitlines() or [''])[0][:80])
