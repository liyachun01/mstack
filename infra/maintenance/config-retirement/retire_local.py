"""One-shot exact-scope local retirement; no service lifecycle or provider calls."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'integrations/tenants'))
from manage import locked,save,STATE
sys.path.insert(0,str(ROOT/'integrations/stack'))
import reconcile,config
slug='mstack-example';project=ROOT.parent/slug
removed=[]
with locked(STATE):
 for tool in ('graphify','anytype','headroom'):
  path=STATE/tool/'registry.json';registry=json.loads(path.read_text())
  tenant=registry['tenants'].get(slug)
  if tenant:
   assert Path(tenant['project_root'])==project
   del registry['tenants'][slug];save(path,registry)
  target=STATE/tool/'tenants'/slug
  if target.exists():shutil.rmtree(target);removed.append(str(target.relative_to(ROOT)))
# Preserve shared connections and owner UI additions; revoke only placeholder routes/keys.
retired={'project-a','project-b'}
for relative in ('infra/stack/project-index.json','infra/agentgateway/projects.bindings.json'):
 path=ROOT/relative;value=json.loads(path.read_text())
 for name in retired|{'clock'}:value['projects'].pop(name,None)
 reconcile.atomic(path,value,0o644)
path=ROOT/'infra/stack/connections.json';catalog=json.loads(path.read_text())
for name in ('anytype-project-a','anytype-project-b'):catalog['connections'].pop(name,None)
reconcile.atomic(path,catalog,0o644)
registry,_=config.registry(ROOT)
reconcile.atomic(ROOT/'infra/agentgateway/projects.json',registry,0o644)
current=reconcile.runtime_config(ROOT)
current['routes']=[r for r in current['routes'] if r.get('name') not in retired]
keys=current['gateways']['projects']['apiKey']['keys']
current['gateways']['projects']['apiKey']['keys']=[k for k in keys if k.get('metadata',{}).get('project') not in retired]
reconcile.atomic(ROOT/'infra/agentgateway/state/projects/runtime/config.yaml',current,0o660)
reconcile.atomic(ROOT/'infra/agentgateway/state/projects/config.json',current,0o644)
path=ROOT/'infra/stack/state/reconcile.json'
if path.exists():
 state=json.loads(path.read_text());state['runtime_hash']=reconcile.digest(current)
 for key in ('projects','project_hashes'):
  if isinstance(state.get(key),dict):
   for name in retired|{'clock'}:state[key].pop(name,None)
 reconcile.atomic(path,state)
for relative in ('examples/project-a','examples/project-b','integrations/examples/portfolio-demo',
                 'integrations/example','infra/projects/mstack-example',
                 'infra/services/state/migration-20261016/project',
                 'infra/services/state/headroom-20261016/project',
                 'infra/services/state/namespace-mstack-20261016/example-before',
                 'infra/services/state/namespace-mstack-20261016/config-backup/infra/projects/mstack-example',
                 '.secrets/agentgateway/projects/project-a','.secrets/agentgateway/projects/project-b'):
 path=ROOT/relative
 if path.exists():
  assert not path.is_symlink();shutil.rmtree(path);removed.append(relative)
for name in ('examples','integrations/examples','infra/projects'):
 p=ROOT/name
 if p.exists() and not any(p.iterdir()):p.rmdir()
result={'removed_paths':removed,'shared_tenants_removed':['graphify','anytype','headroom'],
        'gateway_placeholder_routes_and_keys_revoked':sorted(retired),
        'stale_clock_index_entry_removed':True,'other_anytype_grants_preserved':True,
        'shared_services_restarted':False}
(ROOT/'infra/maintenance/config-retirement/local.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
