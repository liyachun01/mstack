"""One-shot retirement: execute only after explicit approval of initial admin login."""
import json,sys,urllib.request,urllib.error,urllib.parse
from pathlib import Path
base='http://127.0.0.1:58090/api'
project=Path(sys.argv[1]); output=Path(sys.argv[2])
assert project.name=='mstack-example'
def call(path,method='GET',body=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 request=urllib.request.Request(base+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None)
 try:
  with urllib.request.urlopen(request,timeout=30) as response:
   raw=response.read().decode()
   return response.status,json.loads(raw) if response.headers.get('Content-Type','').startswith('application/json') else raw
 except urllib.error.HTTPError as error:return error.code,None
status,session=call('/auth/login','POST',{'email':'admin@windmill.dev','password':'changeme'})
assert status==200 and isinstance(session,str),'Initial owner login unavailable; no reset attempted'
session_prefix=None
try:
 status,before=call('/workspaces/list_as_superadmin?per_page=100',token=session);assert status==200 and len(before)<100
 ids={w['id'] for w in before};assert 'mstack-example' in ids
 status,rows=call('/users/tokens/list?per_page=100',token=session);assert status==200 and len(rows)<100
 own=[r['token_prefix'] for r in rows if session.startswith(r['token_prefix'])]
 assert len(own)==1,'Temporary session must match exactly one token'
 session_prefix=own[0]
 selected=[]
 for name in ('windmill_token','windmill_mcp_token'):
  token=(project/'.secrets'/name).read_text().strip()
  matches=[r for r in rows if token.startswith(r['token_prefix'])]
  assert len(matches)==1,'Example token must match exactly one owner token'
  selected.append((token,matches[0]['token_prefix']))
 status,_=call('/workspaces/delete/mstack-example','DELETE',token=session);assert status==200,('workspace deletion status',status)
 for token,prefix in selected:
  status,_=call('/users/tokens/delete/'+urllib.parse.quote(prefix,safe=''),'DELETE',token=session);assert status==200
 status,after=call('/workspaces/list_as_superadmin?per_page=100',token=session);assert status==200
 assert {w['id'] for w in after}==ids-{'mstack-example'}
 status,remaining=call('/users/tokens/list?per_page=100',token=session);assert status==200
 assert not any(r['token_prefix']==prefix for r in remaining for _,prefix in selected)
 receipt={'workspace':'mstack-example','deleted':True,'project_tokens_revoked':2,'other_workspace_ids_unchanged':True}
finally:
 if session_prefix:
  status,_=call('/users/tokens/delete/'+urllib.parse.quote(session_prefix,safe=''),'DELETE',token=session)
 else:
  status,_=call('/auth/logout','POST',token=session)
 check,_=call('/users/whoami',token=session)
 assert check==401,'Temporary cleanup session must be revoked'
receipt['temporary_admin_session_revoked']=True
output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
