"""Create private rollback copies and narrow host/container baseline; no mutation outside backup."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
USER=Path('/home/developer')

def main():
    stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
    base=ROOT/'infra/maintenance/orb-devbox-mise/.secrets'/stamp
    base.mkdir(parents=True,mode=0o700)
    os.chmod(base.parent,0o700);os.chmod(base,0o700)
    configs=['.zshrc','.bashrc','.profile','.config/mise/config.toml']
    hashes={}
    for relative in configs:
        path=USER/relative
        if path.is_file():
            destination=base/'configs'/relative;destination.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
            shutil.copy2(path,destination);destination.chmod(0o600)
            hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    paths=['.local/share/fnm','.bun/bin','.bun/_bun','.local/bin/uv','.local/bin/uvx']
    archive=base/'legacy-runtimes.tar'
    with tarfile.open(archive,'w') as tar:
        for relative in paths:
            path=USER/relative
            if path.exists() or path.is_symlink():tar.add(path,arcname=relative,recursive=True)
    archive.chmod(0o600)
    with tarfile.open(archive) as tar:members=len(tar.getmembers())
    apt=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True)
    (base/'apt.tsv').write_text(apt);(base/'apt.tsv').chmod(0o600)
    marks=subprocess.check_output(['apt-mark','showmanual'],text=True)
    (base/'apt-manual.txt').write_text(marks);(base/'apt-manual.txt').chmod(0o600)
    ids=subprocess.check_output(['macctl','run','docker','ps','-aq'],text=True).split()
    rows=subprocess.check_output(['macctl','run','docker','inspect','--format','{{.Name}} {{.Id}} {{.State.StartedAt}}',*ids],text=True).splitlines()
    result={'date':stamp,'config_hashes':hashes,'archive':str(archive),'archive_members':members,
            'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'containers':rows}
    (base/'baseline.json').write_text(json.dumps(result,indent=2)+'\n');(base/'baseline.json').chmod(0o600)
    pointer=ROOT/'infra/maintenance/orb-devbox-mise/current-path.txt';pointer.write_text(str(base)+'\n')
    print(json.dumps({'backup_path':str(base),'archive_verified_members':members,'containers_recorded':len(rows),'services_changed':0}))

if __name__=='__main__':main()
