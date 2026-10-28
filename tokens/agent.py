"""Explicit-permission CLI for the local running inventory. Never launches a model."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['discover','scan','summary','review','assign','prepare','context','reply','transcript','revoke'])
    parser.add_argument('--url',default='http://127.0.0.1:58631')
    for scope in ['counters','attribution','folders','summary','assignment','reply','transcript','revoke']:
        parser.add_argument('--allow-'+scope,action='store_true')
    parser.add_argument('--claude');parser.add_argument('--codex',action='append')
    parser.add_argument('--harness',action='append',choices=['Claude Code','Codex']);parser.add_argument('--session');parser.add_argument('--row-id')
    parser.add_argument('--project');parser.add_argument('--category',choices=['Project work','Admin','Agent-to-agent','Unknown','Mixed'])
    parser.add_argument('--reply-file',type=Path)
    args=parser.parse_args();url=urlsplit(args.url)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost') or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
        parser.error('Use the printed http://127.0.0.1:PORT loopback address only')
    required={'scan':'counters','summary':'summary','review':'summary','assign':'assignment','prepare':'summary','context':'summary','reply':'reply','transcript':'transcript','revoke':'revoke'}.get(args.action)
    if required and not getattr(args,'allow_'+required):parser.error('This action requires --allow-'+required)
    if args.action=='scan' and not args.harness:parser.error('scan requires at least one explicit --harness')
    base=args.url.rstrip('/')
    local_open=build_opener(ProxyHandler({})).open
    try:
        page=local_open(base+'/',timeout=10).read().decode()
        match=re.search("const scanToken='([^']+)'",page)
        if not match:raise ValueError('This is not the standalone local inventory')
        capability=match[1]
        def request(path,body=None):
            headers={'X-Inventory-Token':capability}
            data=None
            if body is not None:headers['Content-Type']='application/json';data=json.dumps(body).encode()
            return json.load(local_open(Request(base+path,data,headers),timeout=120))
        if args.action=='discover':result=request('/api/discovery')
        elif args.action=='scan':
            options={'consent':True,'agents':args.harness,'auto_attribution':args.allow_attribution,'folder_hints':args.allow_folders}
            roots={}
            if args.claude:roots['Claude Code']=[args.claude]
            if args.codex:roots['Codex']=args.codex
            if roots:options['roots']=roots
            result=request('/api/scan',options)
        elif args.action in ('summary','review','context'):
            result=request({'summary':'/api/summary','review':'/api/review','context':'/api/agent-context'}[args.action])
        elif args.action=='assign':
            if not args.row_id or not args.project or not args.category:parser.error('assign needs --row-id, --project and --category')
            result=request('/api/assign',{'consent':True,'scope':'counter_interval','row_id':args.row_id,'project':args.project,'work_category':args.category})
        elif args.action=='prepare':result=request('/api/agent-context',{'consent':True,'from_inventory':True})
        elif args.action=='reply':
            if not args.reply_file:parser.error('reply needs --reply-file containing plain text')
            text=args.reply_file.read_text()
            if len(text)>12000:parser.error('Reply exceeds 12000 characters')
            result=request('/api/agent-reply',{'consent':True,'reply':text})
        elif args.action=='transcript':
            if not args.session:parser.error('transcript needs --session from the consented scan')
            result=request('/api/transcript',{'consent':True,'session':args.session})
        else:result=request('/api/revoke',{'consent':True})
        print(json.dumps(result,indent=2))
    except (HTTPError,URLError,OSError,ValueError) as error:
        print('Local inventory action failed: '+str(error),file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
