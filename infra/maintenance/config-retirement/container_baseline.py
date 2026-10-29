import hashlib,json,subprocess,sys
from pathlib import Path
ids=subprocess.check_output(['docker','ps','-aq'],text=True).split()
rows=json.loads(subprocess.check_output(['docker','inspect',*ids]))
result={r['Name'].lstrip('/'):{'id':r['Id'],'started':r['State']['StartedAt'],
        'status':r['State']['Status'],'restarts':r['RestartCount'],
        'configuration_sha256':hashlib.sha256(json.dumps({k:r[k] for k in ('Image','Mounts','Config','HostConfig')},sort_keys=True).encode()).hexdigest()} for r in rows}
p=Path(sys.argv[1])
if len(sys.argv)>2 and sys.argv[2]=='verify':
 assert json.loads(p.read_text())==result,'Container inventory or settings changed'
 print(json.dumps({'containers':len(rows),'unchanged':True}))
else:
 p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
 print(json.dumps({'containers_snapshotted':len(rows)}))
