"""Use this project's configured shared Anytype tenant; never borrow a channel."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations/stack'))
sys.path.insert(0,str(ROOT))
import project_state
from integrations.mcp.stdio import connect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--probe',action='store_true')
    actions.add_argument('--sync-documents',action='store_true')
    actions.add_argument('--call-file',type=Path)
    parser.add_argument('--call-file-sha256')
    args=parser.parse_args();project=args.project.resolve()
    binding=project_state.anytype(project)
    command=[sys.executable,str(ROOT/'integrations/tenants/launch.py'),'--project',str(project),'--tool','anytype']
    if not (args.probe or args.sync_documents or args.call_file):
        os.execv(command[0],command)
    call=None
    if args.call_file:
        content=args.call_file.read_bytes()
        if args.call_file_sha256 and hashlib.sha256(content).hexdigest()!=args.call_file_sha256:
            raise ValueError('Request file changed; no tool call made')
        call=json.loads(content)
        if call.get('arguments',{}).get('space_id',binding['space_id'])!=binding['space_id']:
            raise ValueError('Call outside project channel denied')
    with connect(command,cwd=project) as request:
        if args.sync_documents:
            from anytype_documents import sync
            sync(request,project)
        else:
            print(json.dumps(request('tools/call',call) if call else request('tools/list',{})))

if __name__=='__main__':main()
