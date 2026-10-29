"""Secret-free portable workflow contracts and synthetic routing tests; no installs."""
import copy
import itertools
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / 'integrations/n8n/workflows/task-start-router.json'
SOURCE = ROOT / 'integrations/n8n/workflows/router.expression.js'
HARNESS = Path(__file__).with_name('router_harness.cjs')


def payload():
    workflow = json.loads(WORKFLOW.read_text())
    example = dict(json.loads(workflow['nodes'][1]['parameters']['jsonOutput'])['tasks'][0],
                   broader_relationships=False)
    cases = []
    for profile, implementation, broader, durable in itertools.product(
            ['coding', 'documentation-research', 'pkm-personal'], [False, True], [False, True], [False, True]):
        item = dict(example, task_profile=profile, implementation_question=implementation,
                    broader_relationships=broader, durable_decisions=durable,
                    task='SYNTHETIC_PRIVATE_MARKER', password='SYNTHETIC_PRIVATE_MARKER',
                    access_token='SYNTHETIC_PRIVATE_MARKER', harness_session_id='SYNTHETIC_PRIVATE_MARKER')
        candidates, deferred = [], []
        if profile == 'coding' or (profile == 'documentation-research' and implementation):
            candidates.append('codegraph')
        if broader:
            (deferred if profile == 'pkm-personal' else candidates).append('graphify')
        if durable or profile != 'coding':
            deferred.append('basic-memory')
        cases.append(dict(name=f'{profile}-{implementation}-{broader}-{durable}', input=item,
                          status='preview', candidates=candidates, deferred=deferred))
    invalid = {
        'project_id': [None, '', '{{mstack:CLIENT_REPO}}'],
        'repository': [None, '/tmp/other', '/home/developer/workspaces/mcp-stack'],
        'execution_domain': [None, 'macos-host'],
        'index_scope': [None, 'whole-repository'],
        'memory_writes': [None, 'automatic'],
        'pkm_sync': [None, 'on'],
        'session_id': [None, '', '../escape', 'space id', 'x' * 81, 7],
        'task_id': [None, '', 'with/slash', 7],
        'task': [None, '', '  ', 'x' * 2001, {}],
        'task_profile': [None, '', 'unknown', 'Coding'],
        'harness': [None, 'mimo', 'opencode'],
        'dry_run': [None, False, 'true', 1],
        'implementation_question': [None, 'true', 1],
        'broader_relationships': [None, 'false', 0],
        'durable_decisions': [None, 'true', 1],
    }
    for field, values in invalid.items():
        missing = copy.deepcopy(example)
        del missing[field]
        cases.append(dict(name=f'missing-{field}', input=missing, status='rejected', candidates=[], deferred=[]))
        for index, value in enumerate(values):
            cases.append(dict(name=f'invalid-{field}-{index}', input=dict(example, **{field: value}),
                              status='rejected', candidates=[], deferred=[]))
    cases.append(dict(name='deepseek-and-unicode', input=dict(example, harness='deepseek-harness',
                      task='检查已批准的源代码范围', session_id='session_2026.10-04'),
                      status='preview', candidates=['codegraph'], deferred=[]))
    cases.append(dict(name='expression-looking-task-is-data', input=dict(example, task='{{ $env.KEY }}'),
                      status='preview', candidates=['codegraph'], deferred=[]))
    return dict(workflow=workflow, example=example, source=SOURCE.read_text(), cases=cases)


def run_harness(installed=False):
    data = payload()
    if installed:
        command = ['macctl', 'run', 'docker', 'exec', '-i', 'mcp-stack-n8n-1',
                   # macctl translates slash-prefixed arguments, even a JS comment.
                   'node', '-e', 'void 0;\n' + HARNESS.read_text(), '--', '--installed']
    else:
        command = ['node', str(HARNESS)]
    result = subprocess.run(command, input=json.dumps(data), text=True,
                            capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError('Synthetic router check failed: ' + result.stderr.strip())
    report = json.loads(result.stdout)
    assert report['passed'] == len(data['cases'])
    assert report['batchPassed'] == 4
    return report


class RouterContracts(unittest.TestCase):
    def test_only_four_builtin_manual_nodes(self):
        workflow = payload()['workflow']
        self.assertFalse(workflow['active'])
        self.assertEqual([n['type'] for n in workflow['nodes']],
                         ['n8n-nodes-base.manualTrigger', 'n8n-nodes-base.set',
                          'n8n-nodes-base.splitOut', 'n8n-nodes-base.set'])
        self.assertEqual([n['typeVersion'] for n in workflow['nodes']], [1, 3.5, 1, 3.5])
        self.assertEqual(workflow['pinData'], {})
        self.assertFalse(any('credentials' in node for node in workflow['nodes']))
        self.assertEqual(workflow['connections'], {
            'Manual start': {'main': [[{'node': 'Task input', 'type': 'main', 'index': 0}]]},
            'Task input': {'main': [[{'node': 'Split tasks', 'type': 'main', 'index': 0}]]},
            'Split tasks': {'main': [[{'node': 'Route preview', 'type': 'main', 'index': 0}]]},
        })

    def test_input_is_fixed_synthetic_and_output_drops_unmapped_fields(self):
        workflow = payload()['workflow']
        for node in (workflow['nodes'][1], workflow['nodes'][3]):
            self.assertEqual(node['parameters']['mode'], 'raw')
            self.assertFalse(node['parameters']['includeOtherFields'])
        self.assertTrue(payload()['example']['dry_run'])
        self.assertFalse(workflow['nodes'][1]['parameters']['jsonOutput'].startswith('='))
        split = workflow['nodes'][2]['parameters']
        self.assertEqual(split['fieldToSplitOut'], 'tasks')
        self.assertEqual(split['include'], 'noOtherFields')
        self.assertFalse(split['options']['includeBinary'])

    def test_no_saved_payloads_or_unknown_runtime_identity(self):
        workflow = payload()['workflow']
        settings = workflow['settings']
        self.assertEqual(settings['executionTimeout'], 60)
        self.assertFalse(settings['saveManualExecutions'])
        self.assertFalse(settings['saveExecutionProgress'])
        self.assertEqual(settings['saveDataSuccessExecution'], 'none')
        self.assertEqual(settings['saveDataErrorExecution'], 'none')
        self.assertNotIn('id', workflow)
        self.assertNotIn('versionId', workflow)
        self.assertNotIn('staticData', workflow)

    def test_embedded_expression_equals_source(self):
        data = payload()
        self.assertEqual(data['workflow']['nodes'][3]['parameters']['jsonOutput'],
                         '={{ ' + data['source'].strip() + ' }}')
        for forbidden in ('$env', '$credentials', 'require(', 'fetch(', 'process.', 'eval(', '$workflow'):
            self.assertNotIn(forbidden, data['source'])

    def test_synthetic_policy_matrix_in_local_node(self):
        self.assertFalse(run_harness()['installed'])


if __name__ == '__main__':
    if sys.argv[1:] == ['--installed-n8n']:
        # Explicit opt-in: ephemeral in-memory checks in the existing container, no import/auth.
        print(json.dumps(run_harness(installed=True)))
    else:
        unittest.main()
