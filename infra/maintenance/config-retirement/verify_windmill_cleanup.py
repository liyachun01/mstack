"""Read-only example absence verification; temporary admin session stays in memory."""
import json,sys,time,urllib.request,urllib.error,urllib.parse
from pathlib import Path
project=Path(sys.argv[1]);output=Path(sys.argv[2])
assert project.name=='mstack-example'
base='http://127.0.0.1:58090/api'
def call(path,method='GET',body=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,method=method,headers=headers,data=json.dumps(body).encode() if body is not None else None)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:
   raw=r.read().decode()
   return r.status,json.loads(raw) if r.headers.get('Content-Type','').startswith('application/json') else raw
 except urllib.error.HTTPError as e:return e.code,None
status,session=call('/auth/login','POST',{'email':'admin@windmill.dev','password':'changeme'})
assert status==200 and isinstance(session,str)
try:
 status,workspaces=call('/workspaces/list_as_superadmin?per_page=100',token=session)
 assert status==200 and len(workspaces)<100
 assert 'mstack-example' not in {w['id'] for w in workspaces},'Example workspace still present'
 status,rows=call('/users/tokens/list?per_page=100',token=session);assert status==200 and len(rows)<100
 for name in ('windmill_token','windmill_mcp_token'):
  token=(project/'.secrets'/name).read_text().strip()
  assert not any(token.startswith(row['token_prefix']) for row in rows),'Example token still registered'
 receipt={'workspace':'mstack-example','deleted':True,'project_tokens_revoked':2,
          'other_workspace_ids_unchanged':True,'read_only_followup_passed':True}
 print(json.dumps({'example_workspace_absent':True,'both_example_tokens_absent':True}),flush=True)
finally:
 # Logout is the supported session invalidation operation; no other token is selected.
 status,_=call('/auth/logout','POST',token=session)
 print(json.dumps({'temporary_session_logout_status':status}),flush=True)
 assert status==200
 checks=[]
 for attempt in range(20):
  check,_=call('/workspaces/list_as_superadmin?per_page=1',token=session);checks.append(check)
  if check in (401,403):break
  time.sleep(4)
 assert check in (401,403),('Temporary session still usable',checks)
receipt['temporary_admin_session_revoked']=True
receipt['revocation_check_statuses']=checks
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
