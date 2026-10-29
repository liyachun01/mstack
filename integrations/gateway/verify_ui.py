"""Native macOS owner UI verification; credentials read privately, never printed.

--restart additionally recreates only agentgateway to test persistence. The bounded
probe adds a no-backend HTTP route, then restores the original owner configuration.
Do not run concurrently with owner edits. No real tools or models are called.
"""
import argparse
import base64
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart',action='store_true')
    args=parser.parse_args()
    settings=json.loads((ROOT/'infra/agentgateway/projects/ui.json').read_text())
    password=(ROOT/settings['password_file']).read_text().strip()
    valid='Basic '+base64.b64encode((settings['username']+':'+password).encode()).decode()
    def fetch(path,auth=None,data=None,port=58084):
        headers={}
        if auth:headers['Authorization']=auth
        if data is not None:headers['Content-Type']='application/json'
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,headers=headers,
                                   data=None if data is None else json.dumps(data).encode())
        try:response=OPENER.open(req,timeout=10)
        except urllib.error.HTTPError as error:response=error
        with response:return response.status,dict(response.headers),response.read(4*1024*1024)
    def wait_for(path,auth,status,port=58084):
        for _ in range(50):
            try:
                if fetch(path,auth,port=port)[0]==status:return
            except (OSError,urllib.error.URLError):pass
            time.sleep(.2)
        raise AssertionError('Expected status not reached for '+path)
    def wait_for_file_marker(present):
        path=ROOT/'infra/agentgateway/state/projects/runtime/config.yaml'
        for _ in range(50):
            if ('owner-ui-verification' in path.read_text())==present:return
            time.sleep(.2)
        raise AssertionError('Saved runtime file did not converge')
    status,headers,_=fetch('/ui')
    assert status==401 and any(k.lower()=='www-authenticate' for k in headers)
    assert fetch('/api/runtime')[0]==401
    wrong='Basic '+base64.b64encode((settings['username']+':wrong').encode()).decode()
    assert fetch('/ui',wrong)[0]==401
    status,_,html=fetch('/ui',valid)
    assert status==200 and b'<html' in html.lower()
    assets=re.findall(r'(?:src|href)=["\'](/ui/[^"\']+\.(?:js|css))["\']',html.decode())
    assert assets,'Missing application assets'
    for asset in assets:assert fetch(asset,valid)[0]==200
    status,_,body=fetch('/api/runtime',valid)
    runtime=json.loads(body)
    expected='file' if settings['mode']=='read-write' else 'readOnly'
    assert status==200 and runtime['build']['version']=='1.5.0'
    assert runtime['ui']['configStoreMode']==expected
    assert fetch('/api/config/effective',valid)[0]==200
    assert fetch('/api/config/resources',valid)[0]==200
    checks=['missing/wrong UI login 401','HTML and JS/CSS assets 200',
            'runtime/effective config/resources API 200']
    if expected=='file':
        original=json.loads(fetch('/api/config',valid)[2])
        marker_name='owner-ui-verification'
        assert not any(r.get('name')==marker_name for r in original['routes'])
        changed=copy.deepcopy(original)
        changed['routes'].insert(0,{'name':marker_name,'gateways':['projects'],
            'matches':[{'path':{'exact':'/owner-ui-verification'}}],
            'policies':{'directResponse':{'status':204}}})
        backup=ROOT/'infra/agentgateway/state/projects/owner-ui-probe-original.json'
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as handle:json.dump(original,handle)
        key=(ROOT/'.secrets/agentgateway/projects/project-a/codex-token').read_text().strip()
        caller='Bearer '+key
        try:
            assert fetch('/api/config',valid,changed)[0]==200,'Owner save failed'
            wait_for('/owner-ui-verification',caller,204,58080)
            wait_for_file_marker(True)
            checks.append('owner save 200; config file and active route read-back passed')
            if args.restart:
                subprocess.run([shutil.which('docker') or '/usr/local/bin/docker','compose','-p','mstack',
                    '--project-directory',str(ROOT),'-f','infra/agentgateway/compose.yaml',
                    '-f','infra/agentgateway/projects/compose.yaml','up','-d','--no-deps',
                    '--pull','never','--force-recreate','agentgateway'],check=True,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                wait_for('/api/runtime',valid,200)
                wait_for('/owner-ui-verification',caller,204,58080)
                assert any(r.get('name')==marker_name for r in json.loads(fetch('/api/config',valid)[2])['routes'])
                checks.append('saved owner change survived targeted container recreation')
        finally:
            wait_for('/api/runtime',valid,200)
            assert fetch('/api/config',valid,original)[0]==200,'Restore original from private probe backup'
            wait_for('/owner-ui-verification',caller,404,58080)
            wait_for_file_marker(False)
            restored=json.loads(fetch('/api/config',valid)[2])
            assert restored==original,'Original config restore mismatch'
            backup.unlink()
        checks.append('original owner configuration restored; temporary route removed')
    else:
        assert fetch('/api/config',valid,{})[0]==403
        checks.append('explicit read-only mode rejects save')
    assert fetch('/quitquitquit',valid,{})[0]==404
    assert fetch('/config_dump',valid)[0]==404
    checks.append('raw admin debug/shutdown paths 404')
    print(json.dumps({'passed':True,'ui_url':'http://127.0.0.1:58084/ui',
        'version':runtime['build']['version'],'mode':expected,'assets_checked':len(assets),
        'checks':checks,'real_tool_calls':0,'model_calls':0}))


if __name__=='__main__':main()
