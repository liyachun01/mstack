"""Explicit October 21 OpenCodex removal, executed on macOS through macctl.

Deletes only the identified stopped container, its two unshared volumes/image,
and its obsolete native Claude profile. Never starts a service or calls a model.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'infra/maintenance/opencodex-retirement'
NAME = 'mcp-stack-opencodex'
IDENTITY = '8165bf21056865f51b26ebcde301136008c9f2b634edacfc5dc2b46d4c1d862e'
IMAGE = 'sha256:2220a07c35556757ba7d06aee42e7c3966bab463878c0b3e09a9dabf48184791'
VOLUMES = {'mcp-stack_opencodex_state', 'mcp-stack_opencodex_codex_state'}
OLD = 'caad58fd-df2b-4f21-a04e-f9bc798adb76'
ACTIVE = '00000000-0000-4000-8000-6d6167706965'
LIBRARY = Path.home() / 'Library/Application Support/Claude-3p/configLibrary'


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Docker operation failed: ' + args[0])
    return result.stdout


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def snapshot():
    ids = docker('ps', '-aq').split()
    rows = json.loads(docker('inspect', *ids)) if ids else []
    return rows, {r['Id']: {'name': r['Name'], 'state': r['State']['Status'],
        'started': r['State']['StartedAt'], 'restarts': r['RestartCount'],
        'settings': hashlib.sha256(json.dumps({k:r[k] for k in
            ('Image','Config','HostConfig','Mounts')},sort_keys=True).encode()).hexdigest()}
        for r in rows}


def protected():
    paths = [Path.home()/'.codex'/n for n in ('config.toml','auth.json','magpie-models.json')]
    paths += [LIBRARY/(ACTIVE+'.json'), ROOT/'infra/magpie/state/providers.json',
        ROOT/'infra/magpie/state/settings.json', ROOT/'infra/magpie/state/web-key',
        ROOT/'infra/magpie/state/process.json', ROOT/'.secrets/agents.csv']
    return {str(p):sha(p) for p in paths}


def catalog():
    request=urllib.request.Request('http://127.0.0.1:3425/v1/models', headers={
        'Authorization':'Bearer magpie-claude-desktop', 'anthropic-version':'2023-06-01'})
    with urllib.request.urlopen(request,timeout=10) as response:
        data=json.load(response)['data']
    assert len(data)==1 and data[0]['display_name']=='DeepSeek Flash (official)'
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with path.open('w') as handle:
        os.chmod(path,0o600)
        json.dump(value,handle,indent=2); handle.write('\n')


def prepare():
    assert sys.platform=='darwin'
    assert not (OUT/'.state/before.json').exists(), 'Existing removal baseline preserved'
    rows, state=snapshot()
    target=next(r for r in rows if r['Name']=='/'+NAME)
    assert target['Id']==IDENTITY and target['Image']==IMAGE and target['State']['Status']=='exited'
    assert {m['Name'] for m in target['Mounts']}==VOLUMES
    assert all(r['Image']!=IMAGE and not any(m.get('Name') in VOLUMES for m in r['Mounts'])
               for r in rows if r['Id']!=IDENTITY)
    image=json.loads(docker('image','inspect',IMAGE))[0]
    assert image['RepoTags']==['mcp-stack-opencodex:2.79.0']
    meta=json.loads((LIBRARY/'_meta.json').read_text())
    assert meta['appliedId']==ACTIVE and (LIBRARY/(OLD+'.json')).is_file()
    profile=json.loads((LIBRARY/(OLD+'.json')).read_text())
    assert profile['inferenceGatewayBaseUrl']=='http://127.0.0.1:10100'
    assert profile['inferenceGatewayApiKey']==(ROOT/'.secrets/opencodex/data-plane-token').read_text().strip()
    write(OUT/'.state/before.json', {'containers':state,'protected':protected(),
        'catalog':catalog(), 'volumes':docker('volume','ls','-q').split(),
        'networks':docker('network','ls','-q','--no-trunc').split()})
    print(json.dumps({'ready':True,'container':NAME,'dedicated_volumes':sorted(VOLUMES),
                      'other_containers':len(rows)-1,'magpie_catalog':'passed'}))


def verify():
    before=json.loads((OUT/'.state/before.json').read_text())
    _, after=snapshot()
    expected={k:v for k,v in before['containers'].items() if k!=IDENTITY}
    assert after==expected, 'Unrelated container inventory changed'
    assert protected()==before['protected'], 'Protected files changed'
    assert catalog()==before['catalog']
    assert set(docker('volume','ls','-q').split())==set(before['volumes'])-VOLUMES
    assert set(docker('network','ls','-q','--no-trunc').split())==set(before['networks'])
    assert subprocess.run(['docker','image','inspect',IMAGE],capture_output=True).returncode!=0
    meta=json.loads((LIBRARY/'_meta.json').read_text())
    assert meta['appliedId']==ACTIVE and all(e['id']!=OLD for e in meta['entries'])
    assert not (LIBRARY/(OLD+'.json')).exists()
    stash=json.loads((ROOT/'infra/magpie/state/stash.json').read_text())
    assert stash.get('claude-desktop.applied')!=OLD
    report={'date':'2026-10-21','removed_container':NAME,'removed_image':IMAGE,
        'removed_volumes':sorted(VOLUMES),'removed_native_claude_profile':OLD,
        'other_containers_unchanged':len(after),'other_volumes_unchanged':True,
        'networks_unchanged':True,'native_codex_unchanged':True,
        'magpie_provider_settings_key_and_active_profile_unchanged':True,
        'magpie_catalog':'passed;DeepSeek Flash (official)', 'inference_calls':0,
        'codex_integration':'pending-explicit-user-request'}
    write(OUT/'qualification.json',report)
    print(json.dumps(report))


def remove():
    before=json.loads((OUT/'.state/before.json').read_text())
    _, now=snapshot()
    assert now==before['containers'] and protected()==before['protected']
    assert catalog()==before['catalog']
    docker('rm',IDENTITY)
    docker('volume','rm',*sorted(VOLUMES))
    docker('image','rm','mcp-stack-opencodex:2.79.0')
    if subprocess.run(['docker','image','inspect',IMAGE],capture_output=True).returncode==0:
        docker('image','rm',IMAGE)
    meta_path=LIBRARY/'_meta.json'; meta=json.loads(meta_path.read_text())
    assert meta['appliedId']==ACTIVE
    meta['entries']=[e for e in meta['entries'] if e['id']!=OLD]
    temporary=LIBRARY/'_meta.mstack-retirement.tmp'
    assert not temporary.exists()
    write(temporary,meta); temporary.replace(meta_path)
    (LIBRARY/(OLD+'.json')).unlink()
    stash_path=ROOT/'infra/magpie/state/stash.json'; stash=json.loads(stash_path.read_text())
    assert stash.get('claude-desktop.applied')==OLD
    del stash['claude-desktop.applied']; write(stash_path,stash)
    verify()


if __name__=='__main__':
    {'prepare':prepare,'remove':remove,'verify':verify}[sys.argv[1]]()
