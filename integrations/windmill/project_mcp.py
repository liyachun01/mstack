"""Transport-only stdio bridge to Windmill's native container MCP, using a project token."""
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stack'))
import project_state
import config as intent


def main():
    root=Path(sys.argv[1]).resolve()
    cfg=intent.project_config(root)['windmill']
    binding=project_state.read(root)['bindings'].get('windmill',{})
    if binding.get('status')!='qualified' or binding.get('connection_fingerprint')!=project_state.connection_fingerprint(root,'windmill'):
        raise ValueError('Windmill connection needs qualification')
    key=project_state.credential(root,cfg['mcp_credential_file'],exists=True)
    url=cfg['api_url']+'/mcp/w/'+cfg['workspace']+'/mcp'
    headers={'Authorization':'Bearer '+key.read_text().strip(),'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    for line in sys.stdin:
        message=json.loads(line)
        req=urllib.request.Request(url,data=json.dumps(message).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=90) as response:
                if response.headers.get('Mcp-Session-Id'):headers['Mcp-Session-Id']=response.headers['Mcp-Session-Id']
                if response.status==202:continue
                raw=response.read().decode()
                if response.headers.get('Content-Type','').startswith('text/event-stream'):
                    rows=[json.loads(row[6:]) for row in raw.splitlines() if row.startswith('data: ')]
                else:rows=[json.loads(raw)] if raw else []
                for row in rows:
                    print(json.dumps(row),flush=True)
        except urllib.error.HTTPError as error:
            if 'id' in message:
                # Never include request headers, token, or response body in transport errors.
                print(json.dumps({'jsonrpc':'2.0','id':message['id'],'error':{'code':-32000,'message':'Windmill HTTP '+str(error.code)}}),flush=True)

if __name__=='__main__':main()
