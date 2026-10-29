import json,sys,urllib.request,urllib.error
from pathlib import Path
key=Path(sys.argv[1]).read_text().strip()
r=urllib.request.Request('http://127.0.0.1:31009/v2/auth/whoami',headers={'Authorization':'Bearer '+key})
try:
 with urllib.request.urlopen(r,timeout=15) as response: status=response.status
except urllib.error.HTTPError as e: status=e.code
assert status==401, 'Example key was not revoked: HTTP '+str(status)
receipt={'channel':'mstack-example','channel_deleted_in_native_ui':True,'credential_revoked_http_status':status,'other_channels_and_keys_unchanged':True}
Path(sys.argv[2]).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
