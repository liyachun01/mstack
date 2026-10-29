"""Run on macOS: synthetic concurrency/scope checks or pending production checks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(port, path, key=None, payload=None, session=None):
    headers = {'Accept':'application/json, text/event-stream'}
    if key: headers['Authorization']='Bearer '+key
    if session: headers['Mcp-Session-Id']=session
    if payload is not None:
        headers['Content-Type']='application/json'
        headers['MCP-Protocol-Version']='2025-11-25'
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request('http://127.0.0.1:'+str(port)+path, data=data, headers=headers)
    try:
        response=OPENER.open(req,timeout=10)
    except urllib.error.HTTPError as error:
        response=error
    with response:
        status=response.status; hdr=dict(response.headers); raw=response.read(1048577).decode()
    assert len(raw)<=1048576,'Oversized response'
    message=None
    if raw and status==200:
        if 'text/event-stream' in hdr.get('content-type', hdr.get('Content-Type','')):
            messages=[json.loads(line[5:].strip()) for line in raw.splitlines() if line.startswith('data:')]
            message=next((m for m in messages if m.get('id')==payload.get('id')),None)
        elif raw.lstrip().startswith('{'):message=json.loads(raw)
    return status,{k.lower():v for k,v in hdr.items()},message


class Client:
    def __init__(self,project,key,port):
        self.path='/mcp/projects/'+project;self.key=key;self.port=port;self.session=None;self.counter=0

    def rpc(self,method,params=None):
        self.counter+=1
        msg={'jsonrpc':'2.0','id':self.counter,'method':method}
        if params is not None:msg['params']=params
        status,headers,body=request(self.port,self.path,self.key,msg,self.session)
        if method=='initialize':self.session=headers.get('mcp-session-id')
        return status,body


def run(mode):
    port=58083 if mode=='synthetic' else 58080
    keys={(p,c):(ROOT/'.secrets/agentgateway/projects'/p/(c+'-token')).read_text().strip()
          for p in ('project-a','project-b') for c in ('codex','claude')}
    assert request(port,'/healthz')[0]==401
    assert request(port,'/healthz','wrong')[0]==401
    for key in keys.values():assert request(port,'/healthz',key)[0]==200
    payload={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'scope-probe','version':'1'}}}
    for (project,caller),key in keys.items():
        other='project-b' if project=='project-a' else 'project-a'
        for method in ('initialize','tools/list','tools/call'):
            attack={**payload,'method':method}
            if method=='tools/call':attack['params']={'name':'slack_read_channel','arguments':{'channel_id':'channel-'+other[-1]}}
            assert request(port,'/mcp/projects/'+other,key,attack)[0]==403,(project,caller,method)
        if mode=='pending':assert request(port,'/mcp/projects/'+project,key,payload)[0]==503
    if mode=='pending':
        print(json.dumps({'passed':True,'mode':mode,'checks':['missing/wrong key 401','four distinct caller keys accepted',
            'cross-project initialize/list/call 403','all own pending routes 503'],'live_connections':0}))
        return
    clients={p:Client(p,keys[(p,'codex')],port) for p in ('project-a','project-b')}
    for client in clients.values():
        status,body=client.rpc('initialize',payload['params'])
        assert status==200 and body and 'result' in body and client.session
        status,body=client.rpc('tools/list')
        assert status==200 and [t['name'] for t in body['result']['tools']]==['slack_read_channel']
        for method,field in [('prompts/list','prompts'),('resources/list','resources')]:
            status,body=client.rpc(method)
            assert status==200 and body['result'][field]==[]
        status,body=client.rpc('tools/call',{'name':'slack_blocked','arguments':{'channel_id':'channel-a'}})
        assert status!=200 or 'error' in body or body.get('result',{}).get('isError'), 'Blocked tool permitted'
    def exercise(project):
        client=clients[project];suffix=project[-1]
        for _ in range(5):
            status,body=client.rpc('tools/call',{'name':'slack_read_channel','arguments':{'channel_id':'channel-'+suffix}})
            assert status==200 and not body['result'].get('isError')
            assert body['result']['content'][0]['text']=='synthetic project '+suffix
        status,body=client.rpc('tools/call',{'name':'slack_read_channel','arguments':{'channel_id':'channel-'+('b' if suffix=='a' else 'a')}})
        assert status==200 and body['result']['isError'],'Adapter resource restriction failed'
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(exercise,clients))
    for project,client in clients.items():
        other='project-b' if project=='project-a' else 'project-a'
        assert request(port,client.path,keys[(other,'codex')],payload,client.session)[0]==403
        replay={'jsonrpc':'2.0','id':99,'method':'tools/list'}
        status,_,body=request(port,'/mcp/projects/'+other,keys[(other,'codex')],replay,client.session)
        assert status==404,(status,body)
    _,_,counts=request(58082,'/stats')
    assert counts=={'a':5,'b':5,'blocked':0},counts
    print(json.dumps({'passed':True,'mode':mode,'checks':['parallel A/B calls','route authorization',
        'filtered tool/resource/prompt discovery','blocked tool never dispatched',
        'fixed-scope adapter denies other channel before data read','cross-key session use denied',
        'cross-route session replay denied'],'allowed_reads':counts,'real_service_calls':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['synthetic','pending'])
    run(parser.parse_args().mode)
