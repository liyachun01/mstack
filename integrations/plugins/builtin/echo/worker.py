"""Model-free test worker: records the brief as a work note and commits it on the task branch."""
from pathlib import Path
import re
import subprocess
import sys

brief = sys.argv[1]
title = re.search(r'^Task: (.+)$', brief, re.M)
slug = re.sub(r'[^a-z0-9]+', '-', (title.group(1) if title else 'task').lower()).strip('-')[:48]
note = Path('work-notes')/(slug + '.md')
note.parent.mkdir(exist_ok=True)
note.write_text('# ' + (title.group(1) if title else 'Task') + '\n\nEcho worker received this brief:\n\n' + brief + '\n')
subprocess.run(['git', 'add', str(note)], check=True)
subprocess.run(['git', '-c', 'user.name=mstack echo worker', '-c', 'user.email=echo@mstack.local',
                'commit', '-q', '-m', 'echo worker: ' + slug], check=True)
print('Wrote and committed', note)
