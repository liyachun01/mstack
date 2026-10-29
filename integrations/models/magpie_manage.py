"""Manage the existing Mac Magpie process without Docker or inference calls."""
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'infra/magpie'
STATE = BASE / 'state'
CFG = json.loads((BASE / 'config.json').read_text())
HOME_DIR = Path.home()
BINARY = Path(CFG['binary'])


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    text = value if isinstance(value, str) else json.dumps(value, indent=2) + '\n'
    with path.open('w') as handle:
        os.chmod(path, 0o600)
        handle.write(text)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def start():
    assert sys.platform == 'darwin'
    assert (STATE / 'providers.json').is_file() and (STATE / 'web-key').is_file()
    assert (HOME_DIR / '.config/magpie').resolve() == STATE.resolve()
    assert digest(BINARY) == CFG['binary_sha256']
    for port in (3425, 3430):
        check = subprocess.run(['lsof', '-nP', '-iTCP:' + str(port), '-sTCP:LISTEN'], capture_output=True)
        assert not check.stdout, 'Gateway or management port already occupied'
    log = STATE / 'service.log'
    write_private(log, '')
    with log.open('a') as handle:
        process = subprocess.Popen(['/usr/bin/python3', str(ROOT / 'integrations/models/magpie_service.py')],
            cwd=HOME_DIR, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
            start_new_session=True, close_fds=True)
    write_private(STATE / 'process.json', {'pid': process.pid, 'binary': str(BINARY),
                                         'started_by': 'mstack-magpie-migration'})
    print(json.dumps({'stage': 'background-started', 'pid': process.pid,
                      'gateway': CFG['gateway'], 'management': CFG['management']}))


def stop():
    record = json.loads((STATE / 'process.json').read_text())
    pid = record['pid']
    command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'command='], text=True).strip()
    assert command == str(BINARY) + ' web --no-open --addr 127.0.0.1:3430', 'Process identity changed'
    os.kill(pid, signal.SIGTERM)
    print(json.dumps({'stage': 'stopped-owned-magpie-process', 'pid': pid}))


def models():
    req = urllib.request.Request(CFG['gateway'] + '/v1/models', headers={
        'Authorization': 'Bearer magpie-claude-desktop', 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)['data']

def verify():
    assert sys.platform == 'darwin'
    library = HOME_DIR / 'Library/Application Support/Claude-3p/configLibrary'
    meta = json.loads((library / '_meta.json').read_text())
    assert meta['appliedId'] == '00000000-0000-4000-8000-6d6167706965'
    profile = json.loads((library / (meta['appliedId'] + '.json')).read_text())
    assert profile['inferenceGatewayBaseUrl'].rstrip('/') == CFG['gateway']
    assert profile['inferenceGatewayApiKey'] == 'magpie-claude-desktop'
    catalog = models()
    assert len(catalog) == 1 and catalog[0]['display_name'] == 'DeepSeek Flash (official)'
    try:
        urllib.request.urlopen(CFG['management'], timeout=10)
        raise AssertionError('Unauthenticated management request unexpectedly accepted')
    except urllib.error.HTTPError as error:
        assert error.code == 401
    browser = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    key = (STATE / 'web-key').read_text().strip()
    with browser.open(CFG['management'] + '/?k=' + key, timeout=10) as response:
        assert response.status == 200 and 'magpie' in response.read().decode().lower()
    print(json.dumps({'claude_profile':'magpie','catalog':'DeepSeek Flash (official)',
        'management_authenticated':200,'management_unauthenticated':401,'inference_calls':0}))


if __name__ == '__main__':
    try:
        {'start': start, 'stop': stop, 'verify': verify}[sys.argv[1]]()
    except Exception as error:
        raise SystemExit('Magpie operation failed (' + type(error).__name__ + '); details suppressed to protect credentials')
