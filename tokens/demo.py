"""Entirely invented usage, dates, projects and rates for the public demo."""
from datetime import date, timedelta
import hashlib

SAMPLE_RATES = {
    'Synthetic model A': {'input': 1.2, 'output': 4.8, 'cache_read': .2, 'cache_write': 1.5},
    'Synthetic model B': {'input': 2.0, 'output': 6.0, 'cache_read': .3, 'cache_write': 0},
}


def sample_usage():
    rows=[]
    for day_index in range(30):
        for session_index in range(6):
            harness='Claude Code' if session_index<3 else 'Codex'
            project=['Harbor Notes','Trail Planner','Tiny Shop','Harbor Notes','Unknown','No product'][session_index]
            category='Agent-to-agent' if session_index==3 else 'Unknown' if session_index==4 else 'Admin' if session_index==5 else 'Project work'
            day=(date(2025,6,30)-timedelta(days=day_index)).isoformat()
            sid='synthetic-session-'+str(session_index)
            row_id=hashlib.sha256((sid+day).encode()).hexdigest()[:16]
            rows.append(dict(row_id=row_id,session=sid,folder='Synthetic workspace',day=day,
                model='Synthetic model A' if harness=='Claude Code' else 'Synthetic model B',harness=harness,
                project=project,work_category=category,project_evidence='Invented demo metadata',category_evidence='Invented demo activity',
                review_required=project=='Unknown',session_mixed=False,attribution_scope='Wholly synthetic demo',
                input=(session_index+2)*(day_index%7+2)*3100,output=(session_index+1)*1700,
                cache_read=(day_index%5+1)*14000,cache_write=9000 if harness=='Claude Code' else 0))
    return {'schema':'local-token-usage/2','rows':rows,'issues':0,'source':'Synthetic demo counters and illustrative fictional rates. No personal records.','synthetic':True}
