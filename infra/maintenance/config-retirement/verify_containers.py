import json,subprocess,sys
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text())
ids=subprocess.check_output(['docker','ps','-aq'],text=True).split()
after=json.loads(subprocess.check_output(['docker','inspect',*ids]))
assert {r['Id'] for r in before}=={r['Id'] for r in after},'Container inventory changed'
old={r['Id']:r for r in before}
fields=['Image','Mounts','HostConfig','Config']
for row in after:
 prior=old[row['Id']]
 for field in fields:assert row[field]==prior[field],(row['Name'],field)
 for field in ('StartedAt','Status','Restarting'):
  assert row['State'][field]==prior['State'][field],(row['Name'],field)
 assert row['RestartCount']==prior['RestartCount']
report={'container_count':len(after),'all_ids_start_times_images_mounts_configuration_and_status_unchanged':True,
        'shared_services':{r['Name'].lstrip('/'):r['State'].get('Health',{}).get('Status',r['State']['Status'])
                           for r in after if r['Config'].get('Labels',{}).get('com.docker.compose.project')=='mstack'}}
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
