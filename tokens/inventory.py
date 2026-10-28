"""Local token inventory. Run: python3 -m tokens.inventory [--demo]. No dependencies."""
import argparse
import hashlib
import json
import secrets
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def read_usage(roots, attribute=False):
    """Read chosen counters; structural attribution and folder hints require opt-in."""
    from .attribution import structural_context, assignment, display_basename
    rows, issues, session_index, pending = [], 0, {}, []
    for harness, root in roots:
        for path in sorted(Path(root).expanduser().rglob('*.jsonl')):
            if path.is_symlink():
                issues += 1
                continue
            buckets, seen, previous, bounds = {}, {}, {}, {}
            last_signature, interval_index = None, 0
            current_model = 'Unknown model'
            folder = 'Unknown folder' if attribute else 'Hidden folder'
            context = {'project':'Unknown','uncertain':True}
            session = hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:12]
            try:
                with path.open(errors='replace') as source:
                    for line in source:
                        try:
                            event = json.loads(line)
                            if attribute:structural_context(event, context)
                            payload = event.get('payload') or {}
                            if isinstance(payload,dict) and payload.get('model'):current_model=str(payload['model'])[:120]
                            cwd = event.get('cwd') or (payload.get('cwd') if event.get('type') == 'session_meta' else None)
                            if attribute and cwd:folder = display_basename(str(cwd))[:80] or 'Root folder'
                            stamp = str(event.get('timestamp', ''))[:10]
                            if len(stamp) != 10:continue
                            message = event.get('message') or {}
                            if harness == 'Claude Code':
                                usage = message.get('usage')
                                if event.get('type') != 'assistant' or not isinstance(usage, dict):continue
                                model = str(message.get('model') or 'Unknown model')
                                values = [max(0,int(usage.get(k,0) or 0)) for k in ('input_tokens','output_tokens','cache_read_input_tokens','cache_creation_input_tokens')]
                                identity = (message.get('id'), event.get('requestId'))
                                if identity != (None,None):
                                    old = seen.get(identity,[0,0,0,0])
                                    seen[identity] = [max(a,b) for a,b in zip(old,values)]
                                    values = [max(0,b-a) for a,b in zip(old,values)]
                            else:
                                if event.get('type') != 'event_msg' or payload.get('type') != 'token_count':continue
                                info = payload.get('info') or {};usage = info.get('total_token_usage')
                                if not isinstance(usage,dict):continue
                                model = str(info.get('model') or current_model)
                                current = {k:max(0,int(usage.get(k,0) or 0)) for k in ('input_tokens','output_tokens','cached_input_tokens')}
                                delta = {k:max(0,current[k]-previous.get(k,0)) if current[k]>=previous.get(k,0) else current[k] for k in current}
                                previous=current
                                values=[max(0,delta['input_tokens']-delta['cached_input_tokens']),delta['output_tokens'],delta['cached_input_tokens'],0]
                            if not sum(values):continue
                            label = assignment(context) if attribute else dict(project='Unknown',work_category='Unknown',project_evidence='metadata attribution not permitted',category_evidence='metadata attribution not permitted',review_required=True,attribution_scope='counter records only')
                            signature=(label['project'],label['work_category'],label['project_evidence'],label['category_evidence'],folder)
                            if signature != last_signature:interval_index+=1;last_signature=signature
                            key=(stamp,model,*signature[:4],label['review_required'],folder,interval_index)
                            bounds.setdefault(key,[str(event.get('timestamp')),str(event.get('timestamp'))])[1]=str(event.get('timestamp'))
                            old=buckets.setdefault(key,[0,0,0,0])
                            for i,value in enumerate(values):old[i]+=value
                        except (ValueError,TypeError,AttributeError):issues+=1
                file_rows=[]
                for key,values in buckets.items():
                    day,model,project,category,pe,ce,review,row_folder,interval=key
                    file_rows.append(dict(session=session,folder=row_folder,interval_index=interval,interval_start=bounds[key][0],interval_end=bounds[key][1],day=day,model=model,harness=harness,project=project,work_category=category,project_evidence=pe,category_evidence=ce,review_required=review,attribution_scope='recorded counter interval metadata; heuristic, not exact billing' if attribute else 'counter records only',input=values[0],output=values[1],cache_read=values[2],cache_write=values[3]))
                projects={r['project'] for r in file_rows if r['project']!='Unknown'}
                mixed=len(projects)>1
                for row in file_rows:row.update(session_mixed=mixed,review_required=row['review_required'] or mixed)
                if context.get('source_session'):session_index[context['source_session']]=projects
                pending.append((file_rows,context.get('parent')))
                rows.extend(file_rows)
            except OSError:issues+=1
    for file_rows,parent in pending:
        candidates=session_index.get(parent,set())
        if len(candidates)==1:
            for row in file_rows:
                if row['project']=='Unknown':row.update(project=next(iter(candidates)),project_evidence='parent session metadata; inferred',review_required=True)
    return {'schema':'local-token-usage/2','rows':rows,'issues':issues,'source':('Local usage counters and consented structural metadata.' if attribute else 'Local usage counters only; structural metadata excluded.')+' No prompt/reply text or full paths retained.','attribution_method':'Project identity and work category are independent heuristic suggestions. Mixed or uncertain sessions require review; counters are conserved, never prorated.'}


def demo():
    from .demo import sample_usage
    return sample_usage()


def local_transcript(session, roots, max_chars=2_000_000):
    """Read one already selected session, never an arbitrary browser-supplied path."""
    from .policy import redact_keys
    found = None
    for harness, raw_root in roots:
        root = Path(raw_root).expanduser().resolve()
        for path in root.rglob('*.jsonl'):
            actual = path.resolve()
            if not actual.is_relative_to(root) or not actual.is_file():
                continue
            identity = hashlib.sha256(str(actual).encode()).hexdigest()[:12]
            if identity == session:
                if found is not None and found != (harness, actual):
                    raise ValueError('Ambiguous session')
                found = (harness, actual)
    if found is None:
        raise ValueError('Session unavailable')
    harness, path = found
    lines, chars, skipped, truncated = [], 0, 0, False
    def content_text(content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return '\n'.join(str(block.get('text') or '') for block in content
                             if isinstance(block, dict) and block.get('type') in ('text','input_text','output_text'))
        return ''
    with path.open(errors='replace') as source:
        for raw in source:
            if len(raw) > 16_000_000:
                skipped += 1
                continue
            try:
                row = json.loads(raw)
                if harness == 'Claude Code':
                    message = row.get('message') or {}
                    role = message.get('role') or row.get('type')
                    if row.get('isMeta') or row.get('toolUseResult') is not None:
                        continue
                    text = content_text(message.get('content'))
                else:
                    message = row.get('payload') or {}
                    if row.get('type') != 'response_item' or message.get('type') != 'message':
                        continue
                    role, text = message.get('role'), content_text(message.get('content'))
                if role not in ('user','assistant') or not text.strip():
                    continue
                text = redact_keys(text)
                text = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[redacted email]', text)
                text = re.sub(r'/(?:Users|home|Volumes)/[^\s\"\'<>]+', '[redacted local path]', text)
                part = str(role).upper() + '\n' + text.strip() + '\n'
                if chars + len(part) > max_chars:
                    truncated = True
                    break
                lines.append(part)
                chars += len(part)
            except (ValueError, TypeError, AttributeError):
                skipped += 1
    return {'text': '\n'.join(lines), 'messages': len(lines), 'truncated': truncated,
            'skipped_records': skipped, 'redaction': 'Common API key shapes, email addresses and common absolute local paths masked. Other private text can remain. Inspect the preview before exporting.',
            'coverage': 'User and assistant text only. Tool output, images, audio and metadata omitted. Not an exact full raw archive.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--port', type=int, default=58631)
    parser.add_argument('--claude', default='~/.claude/projects')
    parser.add_argument('--codex', action='append', help='Repeat for additional Codex record roots')
    parser.add_argument('--prices', type=Path, help='Optional local JSON rates per million tokens; no rates are fetched')
    parser.add_argument('--show-skill', action='store_true', help='Print the installed setup skill path and exit')
    args = parser.parse_args(argv)
    if args.show_skill:
        print(Path(__file__).parent / 'skills' / 'local-token-inventory' / 'SKILL.md')
        return
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    from .pricing import load_rates, estimate_usage
    from .demo import SAMPLE_RATES
    try:
        rates = SAMPLE_RATES if args.demo else load_rates(args.prices) if args.prices else {}
    except (OSError, ValueError) as error:
        parser.error(str(error))
    payload = {'rows': [], 'issues': 0, 'source': 'Locked. No transcript files have been read.'}
    scan_token = secrets.token_urlsafe(32)
    selected_roots = []
    connected = set()
    agent_exchange = {'context': None, 'reply': None}
    roots = [('Claude Code', args.claude)] + [('Codex', p) for p in (args.codex or ['~/.codex/sessions', '~/.codex/archived_sessions'])]
    if args.demo:
        roots=[('Claude Code','/synthetic/claude'),('Codex','/synthetic/codex')]
    page = (Path(__file__).parent / 'web' / 'inventory.html').read_text().replace('__SCAN_TOKEN__', scan_token).replace('__STATIC_DEMO__','false').replace('__DEMO_PAYLOAD__','null').replace('__RUN_MODE__', 'DEMO · SYNTHETIC COUNTERS' if args.demo else 'LOCAL HOST · NO UPLOADS').replace('__CONNECT_LABEL__', 'Explore example' if args.demo else 'Connect local counters').replace('__CONNECT_EXPLAIN__', 'Explore the synthetic sample. No local records are read in demo mode.' if args.demo else 'Click Connect to read selected local Claude Code and Codex counter records. Project suggestions use local metadata; names stay on this machine. Transcript text is excluded. Adjust sources and privacy settings below.').replace('__CONNECT_STATUS__', 'Demo mode reads no local records.' if args.demo else 'No usage records have been read. Reading starts only when you click Connect.').encode()
    from .connections import discovery, configured_roots, summary
    class Handler(BaseHTTPRequestHandler):
        def parse_request(self):
            if not super().parse_request():
                return False
            if self.headers.get('Host') not in ('127.0.0.1:' + str(args.port), 'localhost:' + str(args.port)):
                self.send_error(403, 'Loopback host required')
                return False
            return True
        def do_POST(self):
            nonlocal payload, selected_roots, roots
            if self.path not in ('/api/scan','/api/transcript','/api/revoke','/api/agent-review','/api/agent-context','/api/agent-reply','/api/discover','/api/assign'):
                self.send_error(404)
                return
            # A fresh page capability and JSON header prevent cross-site forms from unlocking logs.
            if self.headers.get('X-Inventory-Token') != scan_token or self.headers.get('Content-Type') != 'application/json':
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                self.send_error(400)
                return
            if length < 1 or length > (65536 if self.path.startswith('/api/agent-') else 2048):
                self.send_error(400)
                return
            try:
                options = json.loads(self.rfile.read(length))
                if not isinstance(options, dict) or options.get('consent') is not True:
                    raise ValueError('Consent required')
                if self.path == '/api/discover':
                    updated = roots if args.demo else configured_roots(options, roots)
                    if updated != roots:
                        roots=updated;connected.clear();selected_roots=[]
                        payload={'rows':[],'issues':0,'source':'Locked. Connection folders changed; reconnect with consent.'}
                        agent_exchange.update(context=None,reply=None)
                    self.do_GET_response(json.dumps(discovery(roots,connected,payload['rows'],args.demo)).encode(),'application/json')
                    return
                if self.path == '/api/assign':
                    from .attribution import CATEGORIES
                    target=options.get('row_id');project=options.get('project');category=options.get('work_category')
                    if not isinstance(project,str) or not 1<=len(project.strip())<=80 or category not in CATEGORIES:raise ValueError('Project and work category required')
                    matches=[r for r in payload['rows'] if r.get('row_id')==target]
                    if len(matches)!=1 or options.get('scope')!='counter_interval':raise ValueError('Choose an existing counter interval')
                    if 'original_attribution' not in matches[0]:matches[0]['original_attribution']={k:matches[0].get(k) for k in ('project','work_category','project_evidence','category_evidence')}
                    matches[0].update(project=project.strip(),work_category=category,review_required=False,reviewed=True,project_evidence='explicit local interval review',category_evidence='explicit local interval review')
                    agent_exchange.update(context=None,reply=None)
                    self.do_GET_response(json.dumps(payload).encode(),'application/json');return
                if self.path == '/api/revoke':
                    payload = {'rows': [], 'issues': 0, 'source': 'Locked. Scan access revoked.'}
                    selected_roots = []
                    connected.clear()
                    agent_exchange.update(context=None, reply=None)
                    self.do_GET_response(json.dumps(payload).encode(), 'application/json')
                    return
                if self.path == '/api/agent-context':
                    context = summary(payload) if options.get('from_inventory') is True else options.get('handoff')
                    if not isinstance(context, dict) or context.get('format') not in ('local-token-handoff-v1','local-token-handoff-v2'):
                        raise ValueError('Reviewed handoff required')
                    agent_exchange.update(context=context, reply=None)
                    self.do_GET_response(json.dumps({'status':'Ready for a local agent; awaiting reply'}).encode(), 'application/json')
                    return
                if self.path == '/api/agent-reply':
                    reply = options.get('reply')
                    if not agent_exchange['context'] or not isinstance(reply, str) or len(reply) > 12000:
                        raise ValueError('Prepare a handoff first')
                    agent_exchange['reply'] = reply
                    self.do_GET_response(json.dumps({'status':'Reply available locally'}).encode(), 'application/json')
                    return
                if self.path == '/api/agent-review':
                    # Read-only local helper: no model, shell, writes or network calls.
                    sessions = len({r['session'] for r in payload['rows']})
                    reply = {'mode': 'Local rule-based review; no AI model connected',
                             'sessions': sessions,
                             'next_action': ('Review the largest mixed session before assigning it. Keep it uncategorised if it contains several projects. Then compare one repeated routine against a saved baseline with the same output quality.' if sessions else 'Allow a counter scan before requesting a review.'),
                             'limits': ['Token volume does not measure useful output.', 'Claude Code and Codex counters must be compared separately.', 'No changes made. No transcript read. No external message sent.']}
                    self.do_GET_response(json.dumps(reply).encode(), 'application/json')
                    return
                if self.path == '/api/transcript':
                    session = options.get('session')
                    if not isinstance(session, str) or session not in {r['session'] for r in payload['rows']}:
                        raise ValueError('Choose a session from your scanned overview')
                    if args.demo:
                        transcript = {'text':'USER\nShow my weekly work by project.\n\nASSISTANT\nThese are synthetic demo messages. No personal transcript was read.','messages':2,'truncated':False,'skipped_records':0,'redaction':'Synthetic demo. No personal text.','coverage':'Demo transcript only.'}
                    else:
                        transcript = local_transcript(session, selected_roots)
                    self.do_GET_response(json.dumps(transcript).encode(), 'application/json')
                    return
                agents = options.get('agents', [])
                if not isinstance(agents, list) or not all(a in ('Claude Code', 'Codex') for a in agents):
                    raise ValueError('Invalid agents')
                roots = roots if args.demo else configured_roots(options, roots)
                selected = [r for r in roots if r[0] in agents]
                if not selected:
                    raise ValueError('Choose an agent')
                agent_exchange.update(context=None, reply=None)
                selected_roots = selected
                payload = demo() if args.demo else read_usage(selected, attribute=options.get('auto_attribution') is True)
                connected.clear();connected.update(agents)
                for i,row in enumerate(payload['rows']):
                    if args.demo and options.get('auto_attribution') is not True:
                        row.update(project='Unknown',work_category='Unknown',project_evidence='metadata attribution not permitted',category_evidence='metadata attribution not permitted',review_required=True)
                    row['row_id']=hashlib.sha256('|'.join(str(row.get(k,'')) for k in ('session','day','model','interval_index','project','work_category','project_evidence','category_evidence')).encode()).hexdigest()[:16]
                payload = estimate_usage(payload, rates)
                payload['schema']='local-token-usage/2'
                payload['rows'] = [r for r in payload['rows'] if r['harness'] in agents]
                if not options.get('folder_hints', False):
                    payload = {**payload, 'rows': [{**r, 'folder': 'Hidden folder'} for r in payload['rows']]}
                payload['source'] = ('Synthetic demo counters. No personal logs read.' if args.demo else
                    'Local usage counters. Transcript text and full paths stay out of the response. Folder hints ' + ('on.' if options.get('folder_hints') else 'off.'))
            except (ValueError, TypeError, OSError):
                self.send_error(400)
                return
            self.do_GET_response(json.dumps(payload).encode(), 'application/json')

        def do_GET_response(self, body, content_type):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'none'; frame-ancestors 'none'; form-action 'none'")
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ('/api/discovery','/api/summary','/api/review'):
                if self.headers.get('X-Inventory-Token') != scan_token:
                    self.send_error(403);return
                data=discovery(roots,connected,payload['rows'],args.demo) if self.path=='/api/discovery' else summary(payload) if self.path=='/api/summary' else {'schema':'local-token-review/1','rows':[r for r in payload['rows'] if r.get('review_required')]}
                self.do_GET_response(json.dumps(data).encode(),'application/json');return
            if self.path in ('/api/agent-context','/api/agent-reply'):
                if self.headers.get('X-Inventory-Token') != scan_token:
                    self.send_error(403)
                    return
                key = 'context' if self.path.endswith('context') else 'reply'
                self.do_GET_response(json.dumps({key: agent_exchange[key]}).encode(), 'application/json')
                return
            if self.path not in ('/', '/api/usage'):
                self.send_error(404)
                return
            if self.path == '/api/usage' and self.headers.get('X-Inventory-Token') != scan_token:
                self.send_error(403);return
            body = json.dumps(payload).encode() if self.path == '/api/usage' else page
            self.do_GET_response(body, 'application/json' if self.path == '/api/usage' else 'text/html; charset=utf-8')
        def log_message(self, *args):
            pass
    # Print the URL only after the bind succeeds.
    url_message = ('Local inventory: http://127.0.0.1:%d | %s' % (args.port, payload['source']))
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as error:
        parser.exit(2, 'Cannot bind local port %d: %s. Try --port %d.\n' % (args.port, error.strerror, args.port + 1))
    print(url_message, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
