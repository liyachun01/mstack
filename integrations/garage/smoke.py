"""Synthetic Garage acceptance using existing client runtimes; no packages.

Reads private Garage connection files. Signs requests in memory and supplies
them to docker exec on stdin, never command arguments. Does not create app
resources, workflows, model requests or touch pre-existing objects.
"""
import base64
import datetime
import hashlib
import hmac
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import uuid

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "infra/garage/state"
ENDPOINT = "http://mcp-stack-garage:3900"
GARAGE = ["macctl", "run", "docker", "exec", "mcp-stack-garage", "./garage"]
PY_FETCH = """import sys,json,base64,urllib.request,urllib.error
r=json.load(sys.stdin)
q=urllib.request.Request(r['url'],data=base64.b64decode(r['body']) if r['body'] is not None else None,headers=r['headers'],method=r['method'])
try:
 s=urllib.request.build_opener(urllib.request.ProxyHandler({})).open(q,timeout=10)
except urllib.error.HTTPError as e:s=e
with s:print(json.dumps({'status':s.code,'body':base64.b64encode(s.read()).decode()}))
"""
JS_FETCH = """let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',s=>input+=s);process.stdin.on('end',async()=>{try{const r=JSON.parse(input);const s=await fetch(r.url,{method:r.method,headers:r.headers,body:r.body===null?undefined:Buffer.from(r.body,'base64'),redirect:'error',signal:AbortSignal.timeout(10000)});console.log(JSON.stringify({status:s.status,body:Buffer.from(await s.arrayBuffer()).toString('base64')}));}catch(e){console.error('S3 smoke transport failed');process.exitCode=1;}});"""


def cli(*args):
    p = subprocess.run(GARAGE + list(args), capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise RuntimeError("Garage CLI stage failed: " + " ".join(args[:2]))
    return p.stdout


def connection(service):
    p = STATE / f"{service}-s3.json"
    if p.is_symlink() or p.stat().st_mode & 0o077:
        raise RuntimeError("Connection must be a private regular file")
    c = json.loads(p.read_text())
    if c["endpoint"] != ENDPOINT or c["region"] != "garage":
        raise RuntimeError("Unexpected target")
    return c


def signed(c, method, bucket, key="", body=None, query=""):
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    path = "/" + bucket + ("/" + urllib.parse.quote(key, safe="/-_.~") if key else "")
    payload = hashlib.sha256(body or b"").hexdigest()
    headers = {"host": "mcp-stack-garage:3900", "x-amz-content-sha256": payload, "x-amz-date": stamp}
    names = ";".join(sorted(headers))
    canonical_headers = "".join(f"{h}:{headers[h]}\n" for h in sorted(headers))
    canonical = "\n".join((method, path, query, canonical_headers, names, payload))
    scope = f"{day}/garage/s3/aws4_request"
    string = f"AWS4-HMAC-SHA256\n{stamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
    signing = ("AWS4" + c["secret_key"]).encode()
    for part in (day, "garage", "s3", "aws4_request"):
        signing = hmac.new(signing, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(signing, string.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = f"AWS4-HMAC-SHA256 Credential={c['access_key']}/{scope}, SignedHeaders={names}, Signature={signature}"
    return {"method": method, "url": ENDPOINT + path + ("?" + query if query else ""), "headers": headers, "body": None if body is None else base64.b64encode(body).decode()}


def request(service, record):
    cmd = (["macctl", "run", "docker", "exec", "-i", "mcp-stack-windmill-worker", "python3", "-c", PY_FETCH]
           if service == "windmill" else
           ["macctl", "run", "docker", "exec", "-i", "mcp-stack-n8n-1", "node", "-e", JS_FETCH])
    p = subprocess.run(cmd, input=json.dumps(record), capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise RuntimeError("Client transport failed: " + service)
    return json.loads(p.stdout)


def expect(service, c, method, bucket, key="", body=None, query="", status=200):
    r = request(service, signed(c, method, bucket, key, body, query))
    if r["status"] != status:
        raise RuntimeError(f"{service} {method} expected{status}, got{r['status']}")
    return base64.b64decode(r["body"])


def main():
    wm, n8n = connection("windmill"), connection("n8n")
    bucket = wm["bucket"]
    assert bucket == n8n["bucket"] == "project-mcp-stack-demo-artifacts"
    run = uuid.uuid4().hex[:12]
    keys = [f"acceptance/{run}/windmill.txt", f"acceptance/{run}/n8n.txt"]
    payload = b"Garage synthetic cross-service acceptance\n"
    other = "project-garage-acceptance-" + run
    other_key = "garage-acceptance-" + run
    created_bucket = created_key = False
    checks = []
    try:
        expect("windmill", wm, "PUT", bucket, keys[0], payload)
        assert expect("n8n", n8n, "GET", bucket, keys[0]) == payload
        expect("n8n", n8n, "PUT", bucket, keys[1], payload)
        assert expect("windmill", wm, "GET", bucket, keys[1]) == payload
        checks.append("bidirectional client PUT/GET and byte comparison")
        listed = expect("n8n", n8n, "GET", bucket, query="list-type=2&prefix=acceptance%2F" + run + "%2F")
        assert all(k.encode() in listed for k in keys)
        checks.append("authenticated object listing")
        anonymous = {"method": "GET", "url": ENDPOINT + "/" + bucket + "/" + keys[0], "headers": {}, "body": None}
        assert request("n8n", anonymous)["status"] == 403
        checks.append("anonymous read denied403")
        cli("bucket", "create", other)
        created_bucket = True
        out = cli("key", "create", other_key)
        created_key = True
        second = dict(wm, access_key=re.search(r"^Key ID:\s*(\S+)", out, re.M).group(1), secret_key=re.search(r"^Secret key:\s*(\S+)", out, re.M).group(1))
        cli("bucket", "allow", "--read", "--write", other, "--key", other_key)
        expect("windmill", second, "GET", other, query="list-type=2")
        expect("windmill", wm, "GET", other, query="list-type=2", status=403)
        expect("n8n", n8n, "GET", other, query="list-type=2", status=403)
        expect("windmill", second, "GET", bucket, query="list-type=2", status=403)
        checks.append("project bucket access succeeds; cross-project requests denied403")
    finally:
        for key in keys:
            expect("windmill", wm, "DELETE", bucket, key, status=204)
        if created_key:
            cli("key", "delete", "--yes", other_key)
        if created_bucket:
            cli("bucket", "delete", "--yes", other)
    for key in keys:
        expect("n8n", n8n, "GET", bucket, key, status=404)
    checks.append("exact synthetic objects and temporary bucket/key removed")
    print(json.dumps({"checks": checks, "app_workflows_verified": False}, indent=2))


if __name__ == "__main__":
    main()
