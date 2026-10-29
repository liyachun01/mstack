"""One-time, explicitly authorized Compose namespace migration. No pulls or volume removal.

prepare: private canonical configs and a PostgreSQL logical recovery copy.
apply: identity-checked replacement, compare before start, retain old stopped containers.
verify: compare every migrated service and every unrelated container.
finish: remove only the stopped, identity-checked original containers (without -v).
rollback: stop/remove replacements, restore original container names and running states.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT/'infra/services/state/namespace-mstack-20261016'
SPECS = {
 'postgres': (['compose.yaml'], None, True),
 'windmill-server': (['infra/windmill/compose.yaml'], 'infra/windmill/state/shared.env', False),
 'windmill-worker': (['infra/windmill/compose.yaml'], 'infra/windmill/state/shared.env', False),
 'whodb': (['infra/whodb/compose.yaml'], 'infra/whodb/state/runtime.env', False),
 'garage': (['infra/garage/compose.yaml'], 'infra/garage/state/runtime.env', False),
 'opencodex': (['infra/opencodex/compose.yaml'], None, False),
 'agentgateway': (['infra/agentgateway/compose.yaml','infra/agentgateway/projects/compose.yaml'], None, True),
 'ai-memory': (['infra/ai-memory/compose.yaml'], 'infra/ai-memory/state/runtime.env', False),
 'graphify': (['infra/services/compose.yaml'], None, False),
 'anytype-mcp': (['infra/services/compose.yaml'], None, False),
 'headroom': (['infra/services/compose.yaml'], None, False),
}
ORDER = list(SPECS)


def save(name, value):
    p=STATE/name
    with open(p,'w',opener=lambda path,flags:os.open(path,flags,0o600)) as f: json.dump(value,f,indent=2)


def run(args, label):
    r=subprocess.run(['macctl','run','docker',*args],cwd=ROOT,capture_output=True,text=True)
    if r.returncode:
        save('last-error.json',{'operation':label,'stderr':r.stderr,'stdout':r.stdout})
        raise RuntimeError(label+' failed; private diagnostic saved')
    return r.stdout


def inspect(name): return json.loads(run(['inspect',name.lstrip('/')], 'inspect'))[0]


def all_containers():
    ids=run(['ps','-aq'],'inventory').split()
    return json.loads(run(['inspect',*ids],'inventory inspect'))


def before(): return json.loads((STATE/'before.json').read_text())


def owned():
    result={c['Config']['Labels']['com.docker.compose.service']:c for c in before()
            if c['Config']['Labels'].get('com.docker.compose.project')=='mcp-stack'}
    assert set(result)==set(SPECS), 'Unexpected source service inventory'
    return result


def compose(service):
    files,env,root=SPECS[service]
    args=['compose','-p','mstack']
    if root:args+=['--project-directory','.']
    if env:args+=['--env-file',env]
    for file in files:args+=['-f',file]
    return args


def compare(a,b):
    """Operational equivalence, allowing generated IDs/labels and obsolete PG network-mode repair."""
    errors=[]
    for key in ['Image','Mounts']:
        av=a[key];bv=b[key]
        if key=='Mounts':
            fields=['Type','Name','Source','Destination','RW','Propagation']
            av=sorted([{k:m.get(k) for k in fields} for m in av],key=lambda x:x['Destination'])
            bv=sorted([{k:m.get(k) for k in fields} for m in bv],key=lambda x:x['Destination'])
        if av!=bv:errors.append(key)
    for key in ['Cmd','Entrypoint','User','WorkingDir','Healthcheck','ExposedPorts','StopSignal','StopTimeout']:
        if a['Config'].get(key)!=b['Config'].get(key):errors.append('Config.'+key)
    if sorted(a['Config'].get('Env',[]))!=sorted(b['Config'].get('Env',[])):errors.append('Config.Env')
    # Docker assigns IDs, log paths, sandbox addresses and default-network ordering anew.
    for key in ['Privileged','ReadonlyRootfs','CapAdd','CapDrop','SecurityOpt','Init','Memory','MemorySwap',
                'NanoCpus','PidsLimit','ShmSize','PortBindings','RestartPolicy','LogConfig','Tmpfs','ExtraHosts',
                'GroupAdd','Dns','DnsSearch','DnsOptions','Devices','DeviceRequests','Ulimits']:
        av=a['HostConfig'].get(key);bv=b['HostConfig'].get(key)
        if key in ('Dns','DnsSearch','DnsOptions'):av=av or [];bv=bv or []
        if av!=bv:errors.append('HostConfig.'+key)
    an=a['NetworkSettings']['Networks'];bn=b['NetworkSettings']['Networks']
    if set(an)!=set(bn):errors.append('networks')
    for name in set(an)&set(bn):
        if set(an[name].get('Aliases') or [])!=set(bn[name].get('Aliases') or []):errors.append('aliases:'+name)
    for key,value in a['Config']['Labels'].items():
        if not key.startswith('com.docker.compose.') and b['Config']['Labels'].get(key)!=value:errors.append('label:'+key)
    return errors


def prepare():
    originals=owned()
    assert not any(c['Config']['Labels'].get('com.docker.compose.project')=='mstack' for c in all_containers())
    volumes=set(run(['volume','ls','--format','{{.Name}}'],'volumes').splitlines())
    networks=set(run(['network','ls','--format','{{.Name}}'],'networks').splitlines())
    for service,c in originals.items():
        assert inspect(c['Id'])['Name']==c['Name']
        cfg=json.loads(run(compose(service)+['config','--format','json'],'render '+service))
        assert cfg['name']=='mstack'
        selected=cfg['services'][service]
        assert selected.get('container_name')==c['Name'].lstrip('/')
        image=json.loads(run(['image','inspect',selected['image']],'image '+service))[0]
        assert image['Id']==c['Image'], 'Pinned image differs: '+service
        for volume in cfg.get('volumes',{}).values(): assert volume.get('external') and volume['name'] in volumes
        for network in cfg.get('networks',{}).values(): assert network.get('external') and network['name'] in networks
        save('compose-'+service+'.json',cfg)
        print('prepared '+service,flush=True)
    # Recovery SQL contains role credentials: never print or include it in public evidence.
    dump=STATE/'postgres-before.sql'
    if not dump.exists():
        with open(dump,'wb',opener=lambda p,f:os.open(p,f,0o600)) as f:
            r=subprocess.run(['macctl','run','docker','exec','mcp-stack-postgres-1','pg_dumpall','-U','postgres'],stdout=f,stderr=subprocess.PIPE)
        assert r.returncode==0 and dump.stat().st_size>0, 'PostgreSQL recovery copy failed'
    save('prepared.json',{'services':list(originals),'postgres_recovery_copy':True,'images_existing':True})


def wait_healthy(c):
    deadline=time.monotonic()+120
    while True:
        now=inspect(c['Id'])
        if not now['State']['Running']:raise RuntimeError('Replacement exited: '+c['Name'])
        health=now['State'].get('Health',{}).get('Status')
        if health in (None,'healthy'):return
        if health=='unhealthy' or time.monotonic()>deadline:raise RuntimeError('Health failed: '+c['Name'])
        time.sleep(2)


def recover_postgres():
    """Repair the recorded partial migration without clearing/bypassing its journal.

    The old PG container cannot restart: its NetworkMode names a deleted mail
    network. Recreate only PG from the already-prepared current definition, then
    restore the original Windmill containers. Never recreate the retired network.
    """
    journal=json.loads((STATE/'journal.json').read_text())
    assert len(journal)==1 and journal[0]['service']=='postgres'
    entry=journal[0];old=owned()['postgres'];current=inspect(old['Id'])
    assert not current['State']['Running']
    assert entry['old_id']==old['Id']
    assert current['HostConfig']['NetworkMode']=='mcp-stack-inbox-zero-db'
    cfg=json.loads(run(compose('postgres')+['config','--format','json'],'recovery render'))
    assert cfg==json.loads((STATE/'compose-postgres.json').read_text())
    if not entry.get('new_id'):
        assert current['Name']==old['Name']
        assert not any(c['Config']['Labels'].get('com.docker.compose.project')=='mstack' for c in all_containers())
        run(['rename',old['Id'],entry['backup_name']],'retain original PostgreSQL')
        run(compose('postgres')+['create','--no-build','--pull','never','postgres'],'recover PostgreSQL create')
        new=inspect(entry['original_name']);entry['new_id']=new['Id'];save('journal.json',journal)
    else:
        assert current['Name']=='/'+entry['backup_name']
        new=inspect(entry['new_id'])
        assert new['Name']==old['Name'] and not new['State']['Running']
        assert new['Config']['Labels'].get('com.docker.compose.project')=='mstack'
    differences=compare(old,new);save('comparison-postgres.json',{'differences':differences})
    assert not differences, differences
    assert new['HostConfig']['NetworkMode'] in ('mcp-stack-memory','mcp-stack-n8n-db')
    run(['start',new['Id']],'recover PostgreSQL start');wait_healthy(new)
    for service in ['windmill-server','windmill-worker']:
        original=owned()[service];current=inspect(original['Id'])
        assert current['Name']==original['Name'] and not compare(original,current)
        if original['State']['Running'] and not current['State']['Running']:
            run(['start',original['Id']],'restore '+service);wait_healthy(original)
    save('recovered.json',{'postgres_healthy':True,'original_windmill_running':True,
                           'obsolete_network_reference_removed':True,'journal_preserved':True})
    print('PostgreSQL healthy in mstack; original Windmill services restored; journal preserved.',flush=True)


def apply():
    assert (STATE/'prepared.json').exists()
    assert not (STATE/'journal.json').exists(), 'Migration journal exists; inspect or rollback, never replay blindly'
    originals=owned();journal=[];save('journal.json',journal)
    try:
        # Quiesce the only known shared-PG worker/server before replacing their database.
        for service in ['windmill-worker','windmill-server']:
            old=originals[service];assert inspect(old['Id'])['Name']==old['Name']
            if old['State']['Running']:run(['stop','--time','45',old['Id']],'quiesce '+service)
        for service in ORDER:
            old=originals[service];current=inspect(old['Id'])
            assert current['Name']==old['Name']
            assert current['Config']['Labels'].get('com.docker.compose.project')=='mcp-stack'
            if current['State']['Running']:run(['stop','--time','45',old['Id']],'stop '+service)
            backup='mstack-rollback-'+service+'-20261016'
            run(['rename',old['Id'],backup],'retain '+service)
            journal.append({'service':service,'old_id':old['Id'],'original_name':old['Name'].lstrip('/'),'backup_name':backup})
            save('journal.json',journal)
            run(compose(service)+['create','--no-build','--pull','never',service],'create '+service)
            new=inspect(old['Name']);journal[-1]['new_id']=new['Id'];save('journal.json',journal)
            differences=compare(old,new)
            save('comparison-'+service+'.json',{'differences':differences})
            assert not differences, service+': unexpected differences '+repr(differences)
            if old['State']['Running']:
                run(['start',new['Id']],'start '+service);wait_healthy(new)
            print('migrated '+service+(' running' if old['State']['Running'] else ' stopped'),flush=True)
        verify()
    except Exception:
        print('Migration stopped; restoring original containers.',flush=True)
        rollback()
        raise


def resume():
    """Continue only after the recorded PG recovery is healthy; never restart PG."""
    assert (STATE/'recovered.json').exists() and not (STATE/'finished.json').exists()
    journal=json.loads((STATE/'journal.json').read_text());originals=owned()
    assert journal and journal[0]['service']=='postgres' and journal[0].get('new_id')
    completed={entry['service'] for entry in journal}
    assert len(completed)==len(journal)
    for entry in journal:
        new=inspect(entry['new_id']);old=originals[entry['service']]
        assert new['Name']==old['Name'] and not compare(old,new)
        assert new['Config']['Labels'].get('com.docker.compose.project')=='mstack'
        assert new['State']['Running']==old['State']['Running']
        if new['State']['Running']:wait_healthy(new)
    for service in ORDER:
        if service in completed:continue
        old=originals[service];current=inspect(old['Id'])
        assert current['Name']==old['Name'] and not compare(old,current)
        assert current['State']['Running']==old['State']['Running']
        cfg=json.loads(run(compose(service)+['config','--format','json'],'revalidate '+service))
        assert cfg==json.loads((STATE/('compose-'+service+'.json')).read_text())
        entry={'service':service,'old_id':old['Id'],'original_name':old['Name'].lstrip('/'),
               'backup_name':'mstack-rollback-'+service+'-20261016'}
        if current['State']['Running']:run(['stop','--time','45',old['Id']],'stop '+service)
        run(['rename',old['Id'],entry['backup_name']],'retain '+service)
        journal.append(entry);save('journal.json',journal)
        try:
            run(compose(service)+['create','--no-build','--pull','never',service],'create '+service)
            new=inspect(entry['original_name']);entry['new_id']=new['Id'];save('journal.json',journal)
            differences=compare(old,new);save('comparison-'+service+'.json',{'differences':differences})
            assert not differences,(service,differences)
            if old['State']['Running']:
                run(['start',new['Id']],'start '+service);wait_healthy(new)
            print('migrated '+service+(' running' if old['State']['Running'] else ' stopped'),flush=True)
        except Exception:
            # Restore just this service. Previously verified replacements stay running.
            candidates=[c for c in all_containers() if c['Name']==old['Name']]
            for c in candidates:
                assert c['Config']['Labels'].get('com.docker.compose.project')=='mstack'
                assert c['Config']['Labels'].get('com.docker.compose.service')==service
                if c['State']['Running']:run(['stop','--time','45',c['Id']],'restore stop')
                run(['rm',c['Id']],'restore remove replacement')
            run(['rename',old['Id'],entry['original_name']],'restore original name')
            if old['State']['Running']:
                run(['start',old['Id']],'restore original');wait_healthy(old)
            save('failed-'+service+'.json',entry);journal.pop();save('journal.json',journal)
            raise
    verify()


def verify():
    current=all_containers();byname={c['Name']:c for c in current};originals=owned();checks={}
    for service,old in originals.items():
        new=byname[old['Name']]
        assert new['Config']['Labels']['com.docker.compose.project']=='mstack'
        assert new['State']['Running']==old['State']['Running']
        errors=compare(old,new);assert not errors,(service,errors)
        if old['State']['Running']:wait_healthy(new)
        checks[service]={'old_id':old['Id'],'new_id':new['Id'],'running':new['State']['Running'],'equivalent':True}
    untouched=[]
    for old in before():
        if old['Config']['Labels'].get('com.docker.compose.project')=='mcp-stack':continue
        new=byname[old['Name']]
        assert new['Id']==old['Id'] and new['State']['StartedAt']==old['State']['StartedAt']
        assert new['State']['Status']==old['State']['Status'] and new['RestartCount']==old['RestartCount']
        assert not compare(old,new)
        untouched.append(old['Name'])
    save('after.json',current)
    receipt={'namespace':'mstack','services':checks,'unrelated_unchanged':untouched,'unrelated_count':len(untouched),
             'volumes_credentials_ports_images_preserved':True,'passed':True}
    save('verification.json',receipt)
    print(json.dumps({'namespace':'mstack','services':len(checks),'unrelated_unchanged':len(untouched),'passed':True}),flush=True)


def rollback():
    assert not (STATE/'recovered.json').exists(), 'PG recovery supersedes the broken original; use targeted service recovery'
    assert not (STATE/'finished.json').exists(), 'Original containers retired; recovery requires the saved definitions'
    originals=owned()
    journal=json.loads((STATE/'journal.json').read_text())
    # Stop all replacements before restoring PG. No two instances may write a shared volume.
    for entry in reversed(journal):
        if not entry.get('new_id'):
            # Compose may have created the replacement before a subsequent check failed.
            candidates=[c for c in all_containers() if c['Name']=='/'+entry['original_name']]
            if candidates:
                c=candidates[0]
                assert c['Config']['Labels'].get('com.docker.compose.project')=='mstack'
                assert c['Config']['Labels'].get('com.docker.compose.service')==entry['service']
                entry['new_id']=c['Id']
        if entry.get('new_id'):
            c=inspect(entry['new_id'])
            assert c['Config']['Labels'].get('com.docker.compose.project')=='mstack'
            if c['State']['Running']:run(['stop','--time','45',c['Id']],'rollback stop')
            run(['rm',c['Id']],'rollback remove replacement')
    for entry in journal:
        old=inspect(entry['old_id']);assert old['Name']=='/'+entry['backup_name']
        run(['rename',old['Id'],entry['original_name']],'rollback name')
    for service in ORDER:
        old=originals[service]
        if old['State']['Running'] and not inspect(old['Id'])['State']['Running']:
            run(['start',old['Id']],'rollback start');wait_healthy(old)
    save('rolled-back.json',{'restored':True})


def finish():
    verify()
    journal=json.loads((STATE/'journal.json').read_text())
    assert len(journal)==len(SPECS)
    for entry in journal:
        c=inspect(entry['old_id'])
        assert not c['State']['Running'] and c['Name']=='/'+entry['backup_name']
        run(['rm',c['Id']],'remove stopped original')  # Deliberately no -v.
    assert not run(['ps','-aq','--filter','label=com.docker.compose.project=mcp-stack'],'old namespace').strip()
    save('finished.json',{'old_namespace_empty':True,'old_containers_removed_without_volumes':True})
    print('Old namespace empty; persistent volumes retained.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','apply','resume','verify','finish','rollback','recover_postgres'])
    args=parser.parse_args();globals()[args.action]()
