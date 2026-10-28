"""Local structural evidence only. Suggestions are not exact project billing."""
from pathlib import Path
from urllib.parse import urlsplit
import re

GENERIC = {'home','users','code','projects','src','tests','tmp','desktop','downloads','.claude','.codex','root'}
CATEGORIES = {'Project work','Admin','Agent-to-agent','Unknown','Mixed'}


def display_basename(value):
    # Imported records can originate on another operating system.
    return Path(str(value).replace('\\','/').rstrip('/')).name


def project_identity(cwd=None, repo=None):
    if isinstance(repo, dict):
        repo = repo.get('root') or repo.get('path') or repo.get('name')
    if isinstance(repo, str) and repo.strip():
        name = display_basename(urlsplit(repo).path).removesuffix('.git')
        if name and name.lower() not in GENERIC:
            return name[:80], 'repository metadata', False
    if isinstance(cwd, str) and cwd.strip():
        path = Path(cwd).expanduser()
        for parent in ([path, *list(path.parents)[:8]] if path.is_absolute() else []):
            try:
                if (parent / '.git').exists():
                    return parent.name[:80], 'local repository marker from cwd', False
            except OSError:
                pass
        name = display_basename(cwd)
        if name and name.lower() not in GENERIC:
            return name[:80], 'cwd basename; repository unverified', True
    return 'Unknown', 'no usable project metadata', True


def structural_context(event, current):
    """Inspect metadata/tool names, never prompt/reply prose or command arguments."""
    payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
    git = event.get('git') if isinstance(event.get('git'), dict) else {}
    cwd = event.get('cwd') or payload.get('cwd')
    repo = event.get('repo_root') or event.get('repository') or git.get('repo_root') or payload.get('repo_root') or payload.get('repository')
    if cwd or repo:
        project, evidence, uncertain = project_identity(cwd, repo)
        current.update(project=project, project_evidence=evidence, uncertain=uncertain)
    current['source_session'] = event.get('sessionId') or (payload.get('id') if event.get('type') == 'session_meta' else None) or current.get('source_session')
    parent = event.get('parentSessionId') or event.get('parent_session_id') or payload.get('parent_session_id') or payload.get('forked_from_id')
    if isinstance(parent, str):
        current['parent'] = parent
    names = []
    message = event.get('message') if isinstance(event.get('message'), dict) else {}
    content = message.get('content')
    if isinstance(content, list):
        names += [str(b.get('name','')) for b in content if isinstance(b,dict) and b.get('type') == 'tool_use']
    if payload.get('type') in ('function_call','tool_use'):
        names.append(str(payload.get('name','')))
    categories = set()
    for name in names:
        if re.search(r'send.?message|spawn.?agent|agent.?message|cmux.*(?:send|message)', name, re.I):
            categories.add('Agent-to-agent')
        elif re.search(r'todowrite|update_plan|taskcreate|taskupdate', name, re.I):
            categories.add('Admin')
        else:
            categories.add('Project work' if current.get('project') != 'Unknown' else 'Unknown')
    if categories:
        current['pending_category'] = next(iter(categories)) if len(categories)==1 else 'Mixed'
        current['category_evidence'] = 'structural tool names: '+', '.join(names)[:120]+'; heuristic'
    return current


def assignment(current):
    project = current.get('project','Unknown')
    category = current.pop('pending_category', None) or ('Project work' if project != 'Unknown' else 'Unknown')
    category_evidence = current.pop('category_evidence', None) or ('project-context default; task type unverified' if project != 'Unknown' else 'no work-category evidence')
    return dict(project=project, work_category=category,
                project_evidence=current.get('project_evidence','no usable project metadata'),
                category_evidence=category_evidence,
                review_required=current.get('uncertain',True) or category in ('Unknown','Mixed'),
                attribution_scope='recorded counter interval metadata; heuristic, not exact billing')
