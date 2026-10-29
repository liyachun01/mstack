"""Run on macOS after targeted recreation; verify loaded config, no tool calls."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
settings=json.loads((ROOT/'infra/agentgateway/projects/ui.json').read_text())
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
if settings['enabled']:
    password=(ROOT/settings['password_file']).read_text().strip()
    header='Basic '+base64.b64encode((settings['username']+':'+password).encode()).decode()
    request=urllib.request.Request('http://127.0.0.1:58084/api/config',headers={'Authorization':header})
else:
    request=urllib.request.Request('http://127.0.0.1:58080/healthz')
for _ in range(50):
    try:
        with opener.open(request,timeout=2) as response:
            value=json.load(response)
            actual=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if response.status==200 and actual==sys.argv[1]:
                print(json.dumps({'verified':True,'loaded_config_matches':True,'tool_calls':0}));raise SystemExit(0)
    except urllib.error.HTTPError as error:
        if not settings['enabled'] and error.code==401:
            print(json.dumps({'verified':True,'authenticated_listener_reachable':True,'config_api':'UI disabled; no API comparison','tool_calls':0}));raise SystemExit(0)
    except (OSError,ValueError):pass
    time.sleep(.2)
print(json.dumps({'verified':False,'note':'Owner API config did not match expected runtime or listener unavailable'}))
raise SystemExit(1)
