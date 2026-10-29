"""Bound manual job runner. No schedule, broad token, arbitrary URL or script selection."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stack'))
import project_state
import config as intent


def request(base, token, route, body=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + route, data=data, method=method,
                                 headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read().decode()
        try: return json.loads(raw)
        except ValueError: return raw


def run(project, arguments):
    cfg = intent.project_config(project)['windmill']
    binding=project_state.read(project)['bindings'].get('windmill',{})
    if binding.get('status')!='qualified' or binding.get('connection_fingerprint')!=project_state.connection_fingerprint(project,'windmill'):
        raise ValueError('Windmill connection needs qualification')
    qualified = project_state.read(project)['runtime']['windmill']
    credential = project_state.credential(project,cfg['credential_file'],exists=True)
    token = credential.read_text().strip()
    prefix = '/w/'+cfg['workspace']
    script = request(cfg['api_url'], token, prefix+'/scripts/get/p/'+cfg['script'])
    if script['hash'] != qualified['script_hash'] or hashlib.sha256(script['content'].encode()).hexdigest() != qualified['source_sha256']:
        raise ValueError('Remote script changed; review and requalify before execution')
    job = request(cfg['api_url'], token, prefix+'/jobs/run/p/'+cfg['script'], arguments)
    deadline = time.monotonic()+75
    while time.monotonic() < deadline:
        try:
            complete = request(cfg['api_url'], token, prefix+'/jobs_u/completed/get/'+job)
        except urllib.error.HTTPError as error:
            if error.code != 404: raise
            time.sleep(.5)
            continue
        if not complete.get('success'):
            raise RuntimeError('Windmill job failed: '+str(complete.get('result')))
        evidence = {'project': project_state.identity(project), 'tool': 'windmill', 'provider': 'container',
                    'workspace': cfg['workspace'], 'script': cfg['script'], 'script_hash': qualified['script_hash'],
                    'job_id': job, 'success': True, 'result': complete['result'],
                    'duration_ms': complete.get('duration_ms'), 'schedule_created': False}
        (project/'.mstack/evidence').mkdir(parents=True,exist_ok=True)
        (project/'.mstack/evidence/windmill-run.json').write_text(json.dumps(evidence,indent=2)+'\n')
        return evidence
    raise TimeoutError('Windmill job did not complete before deadline; job ID '+job)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path);parser.add_argument('action',choices=['run']);parser.add_argument('--arguments',required=True)
    a=parser.parse_args()
    print(json.dumps(run(a.project.resolve(),json.loads(a.arguments))))
