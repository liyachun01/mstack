"""Fake DeepSeek Harness for tests (no model). It speaks the headless NDJSON stream that dsh 0.2.0-rc.2 printed in
qualification (MST-56; doc 015): a `session` line with `sessionId`, `status` phases with per-step `usage`,
`tool_call`/`tool_result`, `status/turn_end` with `reason.kind`, then `final`. It resumes with --session-id, and it
behaves like the sandbox: it edits files but never commits or calls `mstack board`. On SIGTERM it does what the real
one does: an empty `final`, no `turn_end`, exit 0.

Env knobs: FAKE_DSH_ARGV (append each argv as a JSON line), FAKE_DSH_BLOCKED (try an action the sandbox refuses),
FAKE_DSH_TERM (state file: mark the run stopped, as `board stop` would, then SIGTERM itself), FAKE_DSH_DONE (state
file: record a `board done` report for MSTACK_TASK, as an unsandboxed worker that reported itself would),
FAKE_DSH_QUEUE (state file: queue an owner comment on the run during the first turn, as a forward would)."""
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid

args = sys.argv[1:]
if os.environ.get('FAKE_DSH_ARGV'):
    with open(os.environ['FAKE_DSH_ARGV'], 'a') as log:
        log.write(json.dumps(args) + '\n')
resumed = '--session-id' in args
session = args[args.index('--session-id') + 1] if resumed else 'session-' + str(uuid.uuid4())
prompt = args[-1]
task = os.environ.get('MSTACK_TASK')


def emit(**event):
    print(json.dumps(event), flush=True)


def terminated(*_):
    emit(type='final', text='')
    sys.exit(0)


def edit_run(knob, change):
    path = Path(os.environ[knob])
    state = json.loads(path.read_text())
    change(state['runs'][task])
    path.write_text(json.dumps(state))


signal.signal(signal.SIGTERM, terminated)
emit(type='session', sessionId=session, cwd=os.getcwd())
emit(type='status', phase='turn_start', turn=1)
emit(type='status', phase='step_start', turn=1, step=1)
emit(type='tool_call', callId='call_1', tool='bash', input={'command': 'edit dsh-turns.md'})
with open('dsh-turns.md', 'a') as notes:
    notes.write('- %s\n' % (prompt.splitlines() or [''])[0][:80])
emit(type='tool_result', callId='call_1', status='completed', result='ok')
emit(type='status', phase='step_end', turn=1, step=1, usage={'inputTokens': 100, 'outputTokens': 20, 'cacheReadTokens': 900})
if os.environ.get('FAKE_DSH_BLOCKED'):
    emit(type='tool_call', callId='call_2', tool='bash', input={'command': 'git commit -m x', 'sandbox_permissions': 'danger-full-access'})
    emit(type='tool_result', callId='call_2', status='error',
         result='Error: sandbox escalation to "danger-full-access" requires approval, but no approval channel is available')
if os.environ.get('FAKE_DSH_TERM'):
    edit_run('FAKE_DSH_TERM', lambda run: run.update(stopped='by test', live=False))
    os.kill(os.getpid(), signal.SIGTERM)
    time.sleep(5)
for knob in ('FAKE_DSH_DONE', 'FAKE_DSH_QUEUE'):
    if os.environ.get(knob) and not (knob == 'FAKE_DSH_QUEUE' and resumed):
        edit_run(knob, (lambda run: run.update(report={'kind': 'done', 'ts': time.time(), 'text': 'reported itself'}))
                 if knob == 'FAKE_DSH_DONE' else
                 (lambda run: run.setdefault('queued', []).append({'text': 'Also add a test please', 'at': 'now'})))
emit(type='status', phase='turn_end', turn=1, reason={'kind': 'completed'})
emit(type='final', text='Fake dsh finished: ' + (prompt.splitlines() or [''])[0][:80])
