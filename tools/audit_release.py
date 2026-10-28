"""Inspect public source, nested archives, static files and Git history.

Optional private deny terms come from an external local file, never shipped.
This is a content guard, not proof of arbitrary data provenance.
"""
import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def entries(name,content,depth=0):
    yield name,content
    if depth>4:raise ValueError('Archive nesting limit exceeded')
    if name.endswith(('.zip','.whl')):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for item in archive.infolist():
                path=Path(item.filename)
                if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive path')
                if not item.is_dir():yield from entries(name+'!'+item.filename,archive.read(item),depth+1)
    elif name.endswith(('.tar.gz','.tgz')):
        with tarfile.open(fileobj=io.BytesIO(content),mode='r:gz') as archive:
            for item in archive:
                path=Path(item.name)
                if path.is_absolute() or '..' in path.parts or item.issym() or item.islnk():raise ValueError('Unsafe archive member')
                if item.isfile():yield from entries(name+'!'+item.name,archive.extractfile(item).read(),depth+1)


def inspect(name,content,terms):
    failures=[]
    # Archive bytes themselves are compressed; their members are scanned separately.
    if name.endswith(('.zip','.whl','.tar.gz','.tgz')):return failures
    text=content.decode('utf-8','replace')
    for term in terms:
        if term.casefold() in text.casefold():failures.append((name,'private deny term'))
    for pattern in (r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----\n', r'(?i)(?:sk-ant-|sk-proj-)[A-Za-z0-9_-]{30,}'):
        if re.search(pattern,text):failures.append((name,'credential-shaped value'))
    if name.lower().endswith(('.png','.jpg','.jpeg','.mp4','.sqlite','.db','.jsonl')):failures.append((name,'unapproved binary/raw-data file'))
    return failures


def audit(output,terms=(),history=False):
    checked=0;failures=[]
    try:
        git_root=subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        if Path(git_root).resolve()!=ROOT.resolve():raise ValueError('Source folder is not its own Git repository')
        tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).splitlines()
        has_git=True
    except (subprocess.CalledProcessError,FileNotFoundError,ValueError):
        tracked=[];has_git=False
    if history and not has_git:
        raise ValueError('--history requires the source folder to be a Git repository; extracted source archives contain no Git history')
    # Plain source folders and pre-commit candidates use the shipped allowlist.
    if not tracked:
        from build_release import FILES
        tracked=FILES
    for filename in tracked:
        for name,content in entries(filename,(ROOT/filename).read_bytes()):
            checked+=1;failures.extend(inspect(name,content,terms))
    for path in Path(output).rglob('*'):
        if path.is_symlink():failures.append((str(path.relative_to(output)),'symlink in release output'))
        elif path.is_file():
            for name,content in entries(str(path.relative_to(output)),path.read_bytes()):
                checked+=1;failures.extend(inspect(name,content,terms))
    commits=[]
    if history:
        commits=subprocess.check_output(['git','rev-list','--all'],cwd=ROOT,text=True).splitlines()
        for commit in commits:
            meta=subprocess.check_output(['git','show','-s','--format=fuller',commit],cwd=ROOT)
            failures.extend(inspect('commit metadata '+commit,meta,terms))
            for filename in subprocess.check_output(['git','ls-tree','-r','--name-only',commit],cwd=ROOT,text=True).splitlines():
                content=subprocess.check_output(['git','show',commit+':'+filename],cwd=ROOT)
                checked+=1;failures.extend(inspect('history '+commit+':'+filename,content,terms))
    return {'checked_entries':checked,'commits':len(commits),'failures':failures}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--deny-file',type=Path);parser.add_argument('--history',action='store_true');args=parser.parse_args()
    terms=[s.strip() for s in args.deny_file.read_text().splitlines() if s.strip()] if args.deny_file else []
    try:result=audit(args.output,terms,args.history)
    except (ValueError,OSError,subprocess.CalledProcessError) as error:parser.error(str(error))
    print(json.dumps(result,indent=2));return bool(result['failures'])

if __name__=='__main__':raise SystemExit(main())
