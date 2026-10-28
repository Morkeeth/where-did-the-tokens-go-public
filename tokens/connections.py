"""Directory discovery only: never reads usage or transcript contents."""
from pathlib import Path


def discovery(roots, connected=(), rows=(), demo=False):
    cards=[]
    for name in ('Claude Code','Codex'):
        paths=[str(Path(p).expanduser()) for h,p in roots if h==name]
        found=False if demo else any(Path(p).is_dir() for p in paths)
        records=sum(r['harness']==name for r in rows)
        state=('connected' if records else 'connected_no_counters') if name in connected else ('discovered' if found else 'not_found')
        if demo:state='demo_connected' if name in connected else 'demo_ready'
        cards.append(dict(harness=name,status=state,configured_roots=paths,directory_found=found,counter_rows=records,
                          command='claude' if name=='Claude Code' else 'codex',
                          recovery='Synthetic demo ready; no local record content or harness installation is needed.' if demo else 'Run the installed harness normally from a project folder. Select its local JSONL record directory here, then explicitly connect. A missing directory or empty scan is not proof of no usage.'))
    cursor_paths=[Path('~/Library/Application Support/Cursor').expanduser(),Path('~/.config/Cursor').expanduser()]
    cards.append(dict(harness='Cursor',status='unsupported',directory_found=False if demo else any(p.is_dir() for p in cursor_paths),configured_roots=[],counter_rows=None,command=None,
                      recovery='This package has no Cursor counter adapter. Detected application data is not imported usage. Keep Cursor billing and transcripts separate; no account or export is accessed.'))
    return {'schema':'local-harness-discovery/1','content_read':False,'harnesses':cards}


def configured_roots(options, existing):
    supplied=options.get('roots')
    if supplied is None:return existing
    if not isinstance(supplied,dict) or any(k not in ('Claude Code','Codex') for k in supplied):raise ValueError('Invalid harness roots')
    result=[]
    for harness in ('Claude Code','Codex'):
        paths=supplied.get(harness,[p for h,p in existing if h==harness])
        if not isinstance(paths,list) or not 1<=len(paths)<=8:raise ValueError('Choose one to eight record folders per harness')
        for raw in paths:
            if not isinstance(raw,str) or not 1<=len(raw)<=1024:raise ValueError('Invalid folder')
            path=Path(raw).expanduser()
            if not path.is_absolute():raise ValueError('Use an absolute path or a path beginning with ~')
            if path.exists() and not path.is_dir():raise ValueError('Record root must be a directory')
            result.append((harness,str(path)))
    return result


def summary(payload):
    rows=payload['rows'];agents={}
    for agent in ('Claude Code','Codex'):
        selected=[r for r in rows if r['harness']==agent]
        totals={key:sum(r[key] for r in selected) for key in ('input','output','cache_read','cache_write')}
        axes={}
        for axis in ('project','work_category'):
            values={}
            for row in selected:
                label=row.get(axis,'Unknown');values[label]=values.get(label,0)+sum(row[k] for k in totals)
            axes[axis]=values
        agents[agent]={'counters':totals,'recorded_sessions':len({r['session'] for r in selected}),**axes}
    days=sorted(r['day'] for r in rows)
    return {'format':'local-token-handoff-v2','scope':'all connected counter records','window':{'from':days[0] if days else None,'to':days[-1] if days else None},'source':payload['source'],'data_kind':'synthetic demo' if payload['source'].startswith('Synthetic') else 'local counter records','agents':agents,
            'uncertain_intervals':sum(bool(r.get('review_required')) for r in rows),
            'limitations':['Project identity and work category are independent heuristic suggestions, not exact billing.','Mixed/unknown work remains uncertain; interval boundaries follow recorded metadata, not token-level causality.','Counters are recorded traffic, not output quality or money paid.','No session IDs, folder paths or transcript text in this summary.']}
