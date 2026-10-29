"""Local, source-bound receipts for deliberately executed integration exercises."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import project_state

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_digest(project):
    files = [project / '.mstack/stack.json']
    files += [project / name for name in ('.mstack/anytype/openapi.json', 'AGENTS.md',
                                         'CLAUDE.md', '.codex/config.toml', '.mcp.json')
              if (project / name).is_file()]
    files += sorted(p for p in (project / 'src').rglob('*')
                    if p.is_file() and '__pycache__' not in p.parts)
    skill = project / '.agents/skills/mstack/SKILL.md'
    if skill.exists():
        files.append(skill)
    values = [(str(p.relative_to(project)), digest(p)) for p in files]
    state = project_state.read(project)
    state.pop('proofs')
    values.append(('@mstack/state', hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()))
    cfg = json.loads((project / '.mstack/stack.json').read_text())
    catalog = json.loads((ROOT / 'infra/stack/presets.json').read_text())
    preset = catalog['presets'][cfg.get('preset', 'daily')]
    # Compact projects inherit live defaults: changing those must invalidate receipts.
    values.append(('@mstack/preset', hashlib.sha256(json.dumps(preset, sort_keys=True).encode()).hexdigest()))
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def artifact_path(project, name):
    path = (project / name).resolve()
    if not path.is_relative_to((project / '.mstack/evidence').resolve()):
        raise ValueError('Proof artifacts must be inside project .mstack/evidence')
    if not path.is_file():
        raise ValueError('Proof artifact missing')
    return path


def record(project, step, details, artifacts):
    project = Path(project).resolve()
    cfg = json.loads((project / '.mstack/stack.json').read_text())
    catalog = json.loads((ROOT / 'infra/stack/presets.json').read_text())
    if step not in catalog['presets'][cfg.get('preset', 'daily')].get('proof_steps', []):
        raise ValueError('Step is not selected by this proof preset')
    if not artifacts:
        raise ValueError('Real-use evidence artifacts are required')
    receipt = {'version': 1, 'project': cfg['project'], 'step': step,
               'recorded_at': datetime.now(timezone.utc).isoformat(),
               'source_sha256': source_digest(project), 'passed': True,
               'details': details, 'artifacts': {name: digest(artifact_path(project, name))
                                               for name in artifacts}}
    with project_state.edit(project) as state:
        state['proofs'][step] = receipt
    return receipt


def inspect_proof(project):
    project = Path(project).resolve()
    cfg = json.loads((project / '.mstack/stack.json').read_text())
    catalog = json.loads((ROOT / 'infra/stack/presets.json').read_text())
    steps = catalog['presets'][cfg.get('preset', 'daily')].get('proof_steps', [])
    results = {}
    current = source_digest(project)
    receipts = project_state.read(project)['proofs']
    for step in steps:
        if step not in receipts:
            results[step] = {'passed': False, 'reason': 'no live-use receipt'}
            continue
        try:
            item = receipts[step]
            if not isinstance(item, dict) or not isinstance(item.get('artifacts'), dict):
                raise ValueError('malformed receipt')
            if item.get('project') != cfg['project'] or item.get('step') != step:
                raise ValueError('receipt belongs to another project or step')
            if item.get('source_sha256') != current:
                raise ValueError('source/configuration changed since proof')
            if item.get('passed') is not True or not item.get('artifacts'):
                raise ValueError('receipt has no successful evidence')
            for name, expected in item['artifacts'].items():
                if digest(artifact_path(project, name)) != expected:
                    raise ValueError('evidence artifact changed: ' + name)
            results[step] = {'passed': True, 'recorded_at': item['recorded_at']}
        except (ValueError, OSError, KeyError, TypeError) as error:
            results[step] = {'passed': False, 'reason': str(error)}
    return {'project': cfg['project'], 'passed': bool(steps) and all(v['passed'] for v in results.values()),
            'kind': 'saved-live-use-evidence;no-new-remote-calls', 'steps': results,
            'note': 'Operator-recorded receipts; not a live uptime check or automatic end-to-end replay.'}
