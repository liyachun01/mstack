"""Generated project records. Editable intent lives only in .mstack/stack.json."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile

RELATIVE = Path('.mstack/state.json')
SECTIONS = ('bindings', 'tenants', 'documents', 'runtime', 'launch', 'proofs')
# Generated or private files inside .mstack/ (its own .gitignore); sync adds rules new mstack versions need.
IGNORED = ('/state.json', '/.lock', '/secrets/', '/cache/', '/evidence/', '/worktrees/', '/journal.json', '/journal.lock',
           '/private.json')


def identity(project):
    value=json.loads((Path(project)/'.mstack/stack.json').read_text())
    slug=value['project']
    if not isinstance(slug,str):raise ValueError('Invalid project identity')
    return slug


def read(project):
    project=Path(project).resolve();slug=identity(project);path=project/RELATIVE
    if path.parent.is_symlink() or path.is_symlink():raise ValueError('Generated state cannot be a symlink')
    value=json.loads(path.read_text()) if path.exists() else {'version':1,'project':slug}
    if not isinstance(value,dict):raise ValueError('Generated state must be an object')
    if value.get('version')!=1 or value.get('project')!=slug:raise ValueError('Generated state belongs to another project')
    if set(value)-{'version','project',*SECTIONS}:raise ValueError('Unknown generated state section')
    for name in SECTIONS:
        if not isinstance(value.setdefault(name,{}),dict):raise ValueError('Invalid generated state section')
    return value


def ignored(project):
    folder=Path(project)/'.mstack'
    if folder.is_symlink():raise ValueError('Project .mstack cannot be a symlink')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=folder/'.gitignore'
    if path.is_symlink():raise ValueError('Mstack .gitignore cannot be a symlink')
    prior=path.read_text() if path.exists() else ''
    rules=[x for x in IGNORED if x not in prior.splitlines()]
    if rules:path.write_text(prior+('\n' if prior and not prior.endswith('\n') else '')+'\n'.join(rules)+'\n')
    return rules


def credential(project,ref,exists=False):
    """A project credential belongs inside its own .mstack folder."""
    if not ref:return None
    root=Path(project).resolve();folder=root/'.mstack/secrets';path=root/ref
    if not ref.startswith('.mstack/secrets/') or '..' in Path(ref).parts or folder.is_symlink() or (root/'.mstack').is_symlink() or not path.resolve().is_relative_to(folder.resolve()) or path.is_symlink():
        raise ValueError('Credential must stay within project .mstack/secrets')
    if path.exists() and (not path.is_file() or path.stat().st_mode&0o077):
        raise ValueError('Private project credential required')
    if exists and not path.is_file():raise ValueError('Private project credential missing')
    return path


def save(project,value):
    project=Path(project).resolve()
    if value.get('project')!=identity(project) or value.get('version')!=1:raise ValueError('Generated state identity mismatch')
    path=project/RELATIVE
    if path.parent.is_symlink() or path.is_symlink():raise ValueError('Generated state cannot be a symlink')
    ignored(project);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    encoded=json.dumps(value,indent=2)+'\n'
    if path.exists() and path.read_text()==encoded:return
    fd,name=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:f.write(encoded);f.flush();os.fsync(f.fileno())
        os.chmod(name,0o600);os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


@contextmanager
def edit(project):
    """Serialize read/modify/write; preserve other generated sections."""
    project=Path(project).resolve();folder=project/RELATIVE.parent
    if folder.is_symlink():raise ValueError('Generated state cannot be a symlink')
    ignored(project);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=folder/'.lock'
    if lock.is_symlink():raise ValueError('State lock cannot be a symlink')
    with lock.open('a') as handle:
        os.chmod(lock,0o600);fcntl.flock(handle,fcntl.LOCK_EX)
        value=read(project)
        yield value
        save(project,value)


def bindings(project):
    value=read(project)
    return {'version':1,'project':value['project'],'tools':value['bindings']}


def tenants(project):
    value=read(project)
    return {'version':1,'project':value['project'],'tools':value['tenants']}


def anytype(project):
    """Join desired document definitions with observed IDs without changing intent."""
    project=Path(project);cfg=json.loads((project/'.mstack/stack.json').read_text())
    selected=cfg.get('anytype',{})
    if not selected:raise ValueError('Anytype project connection is unconfigured')
    state=read(project)
    documents={}
    for key,doc in selected.get('documents',{}).items():
        observed=state['documents'].get('anytype',{}).get(key,{})
        documents[key]={**doc,**({'object_id':observed['object_id']} if observed.get('object_id') else {})}
    return {**selected,'document_objects':documents}


def connection_fingerprint(project,tool):
    import hashlib
    cfg=json.loads((Path(project)/'.mstack/stack.json').read_text())
    settings=dict(cfg.get(tool,{}));settings.pop('documents',None)
    if not settings:return None
    for name in ('credential_file','mcp_credential_file'):
        if ref:=settings.get(name):
            path=credential(project,ref)
            settings[name+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'missing'
    return hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()
