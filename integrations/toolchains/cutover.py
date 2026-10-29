"""Apply the verified repo-owned Linux shell/alias cutover; preserve active runtimes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]
USER=Path('/home/developer')
BOOTSTRAP=ROOT/'infra/toolchains/orb-devbox/activate.zsh'
ENTRYPOINT=ROOT/'integrations/toolchains/entrypoint.py'
ALIASES='node npm npx corepack pnpm dsh ve vefaas ve-tos-cli gh uv uvx bun bunx direnv fd fdfind fzf jq rg shellcheck shfmt tmux'.split()
PROFILES=['infra/mise.toml','infra/toolchains/orb-devbox/mise.toml','infra/toolchains/node-cli/mise.toml','infra/toolchains/python/mise.toml','infra/harnesses/deepseek/mise.toml']
FNM='''# fnm
FNM_PATH="/home/developer/.local/share/fnm"
if [ -d "$FNM_PATH" ]; then
  export PATH="$FNM_PATH:$PATH"
  eval "$(fnm env --shell zsh)"
fi
eval "$(fnm env --use-on-cd --shell zsh)"
'''
BUN='''# bun completions
[ -s "/home/developer/.bun/_bun" ] && source "/home/developer/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"
'''


def transformed_shell(source):
    result=source.replace(FNM,'').replace(BUN,'')
    if 'fnm env' in result or 'export BUN_INSTALL=' in result:
        raise ValueError('Unexpected legacy activation; preserve shell and inspect before changing it')
    block='# mcp-stack mise bootstrap\nsource "'+str(BOOTSTRAP)+'"\n'
    if block not in result:result=block+'\n'+result
    return result


def fingerprint(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n');path.chmod(0o600)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--rollback',action='store_true')
    args=parser.parse_args()
    base=Path((ROOT/'infra/maintenance/orb-devbox-mise/current-path.txt').read_text().strip())
    state=base/'cutover';state.mkdir(mode=0o700,exist_ok=True)
    manifest=state/'manifest.json';shell=USER/'.zshrc'
    if args.rollback:
        saved=json.loads(manifest.read_text())
        if fingerprint(shell) not in (saved['shell_before_sha256'],saved['shell_after_sha256']):raise ValueError('Shell changed since cutover; restore the saved block manually')
        shutil.copy2(state/'zshrc.before',shell);shell.chmod(saved['shell_before_mode'])
        for name,info in saved['aliases'].items():
            path=USER/'.local/bin'/name
            if not path.is_symlink() or path.resolve()!=ENTRYPOINT:
                if info['kind']=='absent' and not path.exists():continue
                if info['kind']=='symlink' and path.is_symlink() and os.readlink(path)==info['target']:continue
                if info['kind']=='file' and path.is_file() and fingerprint(path)==fingerprint(state/'aliases'/name):continue
                raise ValueError('Alias changed; inspect before rollback: '+name)
            path.unlink()
            if info['kind']=='symlink':path.symlink_to(info['target'])
            elif info['kind']=='file':
                shutil.copy2(state/'aliases'/name,path);path.chmod(info['mode'])
        discovery=ROOT/'.mise.toml'
        if saved['created_discovery'] and discovery.is_symlink() and os.readlink(discovery)=='infra/mise.toml':discovery.unlink()
        print(json.dumps({'rolled_back':True,'services_changed':0}));return
    evidence=json.loads((base/'replacement-verification.json').read_text())
    if not evidence.get('passed') or not evidence.get('archive_verified'):raise ValueError('Replacement and backup verification must pass first')
    for relative,expected in evidence['config_hashes'].items():
        if fingerprint(ROOT/relative)!=expected:raise ValueError('Tool declarations changed after verification')
    old=shell.read_text();new=transformed_shell(old)
    discovery=ROOT/'.mise.toml'
    if discovery.exists() or discovery.is_symlink():
        if not discovery.is_symlink() or os.readlink(discovery)!='infra/mise.toml':raise ValueError('Existing root mise config preserved; inspect discovery')
    for name in ALIASES:
        path=USER/'.local/bin'/name
        if path.is_dir():raise ValueError('Alias is a directory; no replacement performed')
    if not args.apply:
        print(json.dumps({'prepared':True,'shell_change':old!=new,'aliases':ALIASES,'services_changed':0}));return
    if manifest.exists() and old==new and all((USER/'.local/bin'/name).is_symlink() and (USER/'.local/bin'/name).resolve()==ENTRYPOINT for name in ALIASES):
        print(json.dumps({'applied':True,'changed':False,'services_changed':0}));return
    if manifest.exists():raise ValueError('Prior cutover needs review; refusing to overwrite rollback evidence')
    shutil.copy2(shell,state/'zshrc.before');(state/'zshrc.before').chmod(0o600)
    aliases=state/'aliases';aliases.mkdir(mode=0o700)
    saved={'aliases':{},'created_discovery':not discovery.is_symlink(),'shell_before_sha256':fingerprint(shell),
           'shell_before_mode':shell.stat().st_mode&0o777,'shell_after_sha256':hashlib.sha256(new.encode()).hexdigest(),'phase':'prepared'}
    for name in ALIASES:
        path=USER/'.local/bin'/name
        if path.is_symlink():saved['aliases'][name]={'kind':'symlink','target':os.readlink(path)}
        elif path.exists():
            shutil.copy2(path,aliases/name);(aliases/name).chmod(0o600)
            saved['aliases'][name]={'kind':'file','mode':path.stat().st_mode&0o777}
        else:saved['aliases'][name]={'kind':'absent'}
    save_json(manifest,saved)
    env={**os.environ,'MISE_INSTALL_MISSING_TOOLS':'0','MISE_NOT_FOUND_AUTO_INSTALL':'0'}
    for relative in PROFILES:
        done=subprocess.run([str(USER/'.local/bin/mise'),'trust',str(ROOT/relative)],env=env,capture_output=True,text=True)
        if done.returncode:raise ValueError('Exact project config trust failed before cutover')
    if saved['created_discovery']:discovery.symlink_to('infra/mise.toml')
    # Trust is recorded against discovery paths, including this lexical symlink.
    done=subprocess.run([str(USER/'.local/bin/mise'),'trust',str(discovery)],env=env,capture_output=True,text=True)
    if done.returncode:raise ValueError('Root discovery config trust failed before cutover')
    for name in ALIASES:
        path=USER/'.local/bin'/name
        if path.exists() or path.is_symlink():path.unlink()
        path.symlink_to(ENTRYPOINT)
    shell.write_text(new)
    saved['shell_after_sha256']=fingerprint(shell);saved['phase']='complete';save_json(manifest,saved)
    print(json.dumps({'applied':True,'changed':True,'aliases':len(ALIASES),'legacy_prefixes_preserved':True,'services_changed':0}))

if __name__=='__main__':main()
