import subprocess,json
rows=subprocess.check_output(['ps','-axo','pid,ppid,command'],text=True).splitlines()
for row in rows:
 if 'mstack-example' in row and not any(x in row for x in ('inspect_processes','macctl run','ssh -o')):
  print(row)
