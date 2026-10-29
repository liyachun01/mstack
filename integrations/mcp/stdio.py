"""Small bounded stdio MCP qualification client; runs an explicitly supplied binding."""
from contextlib import contextmanager
import json
import select
import subprocess
import time

@contextmanager
def connect(command, cwd=None):
    process=subprocess.Popen(command,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    sequence=0
    buffer=b''
    def send(value):
        process.stdin.write(json.dumps(value).encode()+b'\n');process.stdin.flush()
    def request(method,params):
        nonlocal sequence,buffer
        sequence+=1; wanted=sequence
        send({'jsonrpc':'2.0','id':wanted,'method':method,'params':params})
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            if b'\n' not in buffer:
                if not select.select([process.stdout],[],[],max(0,deadline-time.monotonic()))[0]:break
                chunk=process.stdout.read1(65536)
                if not chunk:raise RuntimeError('MCP server ended before responding')
                buffer+=chunk
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1)
                item=json.loads(line)
                if item.get('id')==wanted:
                    if 'error' in item:raise RuntimeError(item['error'])
                    return item['result']
        raise TimeoutError('MCP response timed out')
    try:
        request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'mstack-qualification','version':'1'}})
        send({'jsonrpc':'2.0','method':'notifications/initialized'})
        yield request
    finally:
        process.terminate()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait()
