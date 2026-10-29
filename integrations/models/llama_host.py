"""Run with macctl on macOS. Runtime paths/options belong to infra/llama.cpp."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('runtime_root', type=Path)
parser.add_argument('action', choices=['version', 'help', 'devices', 'start'])
args = parser.parse_args()
root = args.runtime_root.resolve()
config = json.loads((root/'runtime.json').read_text())
if config.get('status', '').startswith('removed'):
    sys.exit('Standalone llama.cpp was removed. Use /Applications/Llama.app; see infra/llama-app/runtime.json.')
binary = root/config['binary']
if args.action in ['version', 'help', 'devices']:
    option = '--list-devices' if args.action == 'devices' else '--'+args.action
    raise SystemExit(subprocess.call([str(binary), option], cwd=binary.parent))
if not config.get('model_file'):
    sys.exit('llama.cpp is installed; choose and qualify model weights before starting')
model = root/config['model_file']
if not model.is_file():
    sys.exit('Configured model file is missing')
command = [str(binary), '--model', str(model), '--alias', config['model_alias'],
           '--host', config['host'], '--port', str(config['port']),
           '--ctx-size', str(config['context_size']), '--parallel', str(config['parallel']),
           '--n-gpu-layers', '99', '--jinja']
raise SystemExit(subprocess.call(command, cwd=binary.parent))
