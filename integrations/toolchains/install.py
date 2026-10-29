"""Install only the approved exact Linux toolchain profiles, with isolated config scope."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parents[2]
MISE=Path('/home/developer/.local/bin/mise')
PROFILES={'common':ROOT/'infra/toolchains/orb-devbox','node-cli':ROOT/'infra/toolchains/node-cli',
          'python':ROOT/'infra/toolchains/python','deepseek':ROOT/'infra/harnesses/deepseek','project':ROOT/'infra'}

def environment(scope):
    env={k:v for k,v in os.environ.items() if k in ('HOME','USER','LOGNAME','LANG','LC_ALL','TERM','SSL_CERT_FILE','SSL_CERT_DIR')}
    env.update({'PATH':'/home/developer/.local/share/mise/installs/node/24.19.0/bin:/home/developer/.local/bin:/usr/local/bin:/usr/bin:/bin',
        'MISE_INSTALL_MISSING_TOOLS':'0','MISE_NOT_FOUND_AUTO_INSTALL':'0','MISE_NO_ENV':'1','MISE_NO_HOOKS':'1',
        'MISE_GLOBAL_CONFIG_FILE':str(ROOT/'infra/toolchains/empty-global.toml'),
        'MISE_SYSTEM_CONFIG_FILE':str(ROOT/'infra/toolchains/empty-system.toml'),
        'MISE_CEILING_PATHS':str(scope.parent),'MISE_TRUSTED_CONFIG_PATHS':str(scope/'mise.toml'),
        'MISE_NODE_DEFAULT_PACKAGES_FILE':'/dev/null','MISE_PYTHON_DEFAULT_PACKAGES_FILE':'/dev/null',
        'NPM_CONFIG_IGNORE_SCRIPTS':'true','NPM_CONFIG_AUDIT':'false','NPM_CONFIG_FUND':'false',
        'NPM_CONFIG_REGISTRY':'https://registry.npmjs.org','NPM_CONFIG_USERCONFIG':'/dev/null',
        'COREPACK_ENABLE_NETWORK':'0','NODE_DISABLE_COMPILE_CACHE':'1','NO_COLOR':'1'})
    return env

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('profile',choices=PROFILES)
    parser.add_argument('--lock-only',action='store_true');args=parser.parse_args()
    scope=PROFILES[args.profile];env=environment(scope)
    private=Path((ROOT/'infra/maintenance/orb-devbox-mise/current-path.txt').read_text().strip())
    tools=tomllib.loads((scope/'mise.toml').read_text())['tools']
    for action,flags in [('lock',['lock','--platform','linux-arm64']),('install',['--locked','install','--jobs','2'])]:
        if args.lock_only and action=='install':break
        logfile=private/(args.profile+'-'+action+'.log')
        with logfile.open('w') as out:
            logfile.chmod(0o600)
            result=subprocess.run([str(MISE),'-C',str(scope),*flags],env=env,stdout=out,stderr=out)
        if result.returncode:
            print(json.dumps({'profile':args.profile,'step':action,'passed':False,'private_log':str(logfile)}))
            raise SystemExit(result.returncode)
        print(json.dumps({'profile':args.profile,'step':action,'passed':True,'tools':len(tools)}),flush=True)

if __name__=='__main__':main()
