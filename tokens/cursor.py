"""Cursor counters come from an opt-in local stop hook, not from transcripts.

Cursor's agent transcripts have no token fields, and its application databases
are not usage records. The hook appends one counters-only line per parent turn.
Subagent tokens are not in that payload. Nothing here contacts Cursor's API.
"""
import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = '~/.cursor/usage-ledger'
LEDGER_NAME = 'turns.jsonl'
MAX_TOKENS = 10 ** 15
STATUSES = {'completed', 'aborted', 'error'}


def hook_command():
    import sys
    from shlex import quote
    return quote(sys.executable) + ' -m tokens.cursor_hook'


def _bounded_text(value, limit):
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > limit or any(ord(ch) < 32 for ch in text):
        return None
    return text


def _count(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < 0 or value > MAX_TOKENS:
        return None
    return value


def counters_from_turn(event):
    """Split Cursor's inclusive input into the inventory's four buckets.

    Cursor's input_tokens includes cache_read_tokens and cache_write_tokens.
    Missing cache fields stay unknown: the raw input is kept and marked so it
    is not presented as uncached traffic.
    """
    incoming = _count(event.get('input_tokens'))
    outgoing = _count(event.get('output_tokens'))
    if incoming is None or outgoing is None:
        return None
    cache_read = _count(event.get('cache_read_tokens'))
    cache_write = _count(event.get('cache_write_tokens'))
    split = cache_read is not None and cache_write is not None and cache_read + cache_write <= incoming
    if split:
        uncached = incoming - cache_read - cache_write
        read, write = cache_read, cache_write
    else:
        uncached, read, write = incoming, 0, 0
    if not (uncached or outgoing or read or write):
        return None
    return uncached, outgoing, read, write, split


def normalize_stop(payload, now=None):
    """Keep counters, model, time and one workspace root. Drop everything else."""
    if not isinstance(payload, dict):
        return None
    if payload.get('hook_event_name') not in (None, 'stop'):
        return None
    generation = _bounded_text(payload.get('generation_id'), 80)
    if generation is None:
        return None
    if counters_from_turn(payload) is None:
        return None
    conversation = _bounded_text(payload.get('conversation_id'), 80) or generation
    model = _bounded_text(payload.get('model_id'), 120) or _bounded_text(payload.get('model'), 120) or 'Unknown model'
    roots = payload.get('workspace_roots')
    paths = [p for p in roots if _bounded_text(p, 1024)] if isinstance(roots, list) else []
    status = payload.get('status') if payload.get('status') in STATUSES else None
    stamp = now or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if not isinstance(stamp, str) or len(stamp) < 20:
        return None
    record = {
        'type': 'cursor_turn',
        'timestamp': stamp,
        'conversation_id': conversation,
        'generation_id': generation,
        'model': model,
        'input_tokens': payload['input_tokens'],
        'output_tokens': payload['output_tokens'],
    }
    if _count(payload.get('cache_read_tokens')) is not None and _count(payload.get('cache_write_tokens')) is not None:
        record['cache_read_tokens'] = payload['cache_read_tokens']
        record['cache_write_tokens'] = payload['cache_write_tokens']
    if paths:
        record['cwd'] = paths[0]
        if len(paths) > 1:
            record['multiple_workspaces'] = True
    if status:
        record['status'] = status
    return record


def append_turn(root, record):
    directory = Path(root).expanduser()
    if directory.is_symlink():
        raise OSError('Cursor ledger directory must not be a symlink')
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    target = directory / LEDGER_NAME
    if target.is_symlink():
        raise OSError('Cursor ledger must not be a symlink')
    line = json.dumps(record, separators=(',', ':')) + '\n'
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)


def install_user_hook(home, command=None):
    """Add the stop hook beside any hooks the user already configured."""
    command = command or hook_command()
    cursor = Path(home).expanduser() / '.cursor'
    if cursor.is_symlink():
        raise OSError('Refusing to edit a symlinked .cursor directory')
    cursor.mkdir(parents=True, exist_ok=True)
    path = cursor / 'hooks.json'
    if path.is_symlink():
        raise OSError('Refusing to edit a symlinked hooks.json')
    existing = {}
    if path.exists():
        existing = json.loads(path.read_text())
        if not isinstance(existing, dict):
            raise ValueError('hooks.json must be a JSON object')
    hooks = existing.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('hooks.json hooks must be an object')
    stop = hooks.get('stop', [])
    if not isinstance(stop, list):
        raise ValueError('hooks.json stop must be a list')
    if not any(isinstance(item, dict) and item.get('command') == command for item in stop):
        stop.append({'command': command})
    hooks['stop'] = stop
    existing['hooks'] = hooks
    existing.setdefault('version', 1)
    path.write_text(json.dumps(existing, indent=2) + '\n')
    ledger = cursor / 'usage-ledger'
    if not ledger.exists():
        ledger.mkdir()
    return path


def read_cursor_file(path, attribute=False):
    """One ledger file. Same generation_id is kept once; later lines replace earlier ones."""
    from .attribution import assignment, display_basename, structural_context
    issues = 0
    order, turns = [], {}
    with Path(path).open(errors='replace') as source:
        for line in source:
            try:
                event = json.loads(line)
                if not isinstance(event, dict) or event.get('type') != 'cursor_turn':
                    issues += 1
                    continue
                generation = event.get('generation_id')
                if not isinstance(generation, str) or not generation:
                    issues += 1
                    continue
                counted = counters_from_turn(event)
                stamp = str(event.get('timestamp', ''))
                if counted is None or len(stamp) < 10:
                    issues += 1
                    continue
                conversation = event.get('conversation_id') if isinstance(event.get('conversation_id'), str) else generation
                if generation not in turns:
                    order.append(generation)
                turns[generation] = (conversation[:80], stamp, str(event.get('model') or 'Unknown model')[:120], event.get('cwd') if isinstance(event.get('cwd'), str) else None, bool(event.get('multiple_workspaces')), counted)
            except (ValueError, TypeError, AttributeError):
                issues += 1
    grouped = {}
    for generation in order:
        conversation, stamp, model, cwd, multiple, counted = turns[generation]
        grouped.setdefault(conversation, []).append((stamp, model, cwd, multiple, counted))
    rows = []
    for conversation, events in grouped.items():
        session = hashlib.sha256(conversation.encode()).hexdigest()[:12]
        buckets, bounds = {}, {}
        last_signature, interval_index = None, 0
        for stamp, model, cwd, multiple, counted in events:
            context = {'project': 'Unknown', 'uncertain': True}
            folder = 'Unknown folder' if attribute else 'Hidden folder'
            if attribute and cwd:
                structural_context({'cwd': cwd}, context)
                if multiple:
                    context['uncertain'] = True
                    context['project_evidence'] = 'first of several workspace roots; others not allocated'
                folder = display_basename(cwd)[:80] or 'Root folder'
            label = assignment(context) if attribute else dict(project='Unknown', work_category='Unknown', project_evidence='metadata attribution not permitted', category_evidence='metadata attribution not permitted', review_required=True, attribution_scope='counter records only')
            uncached, outgoing, cache_read, cache_write, split = counted
            if not split:
                label['review_required'] = True
                label['category_evidence'] = label['category_evidence'] + '; cache fields absent, so input may include cached tokens'
            signature = (label['project'], label['work_category'], label['project_evidence'], label['category_evidence'], folder)
            if signature != last_signature:
                interval_index += 1
                last_signature = signature
            key = (stamp[:10], model, *signature[:4], label['review_required'], folder, interval_index)
            bounds.setdefault(key, [stamp, stamp])[1] = stamp
            old = buckets.setdefault(key, [0, 0, 0, 0])
            for index, value in enumerate((uncached, outgoing, cache_read, cache_write)):
                old[index] += value
        file_rows = []
        for key, values in buckets.items():
            day, model, project, category, project_evidence, category_evidence, review, row_folder, interval = key
            file_rows.append(dict(session=session, folder=row_folder, interval_index=interval, interval_start=bounds[key][0], interval_end=bounds[key][1], day=day, model=model, harness='Cursor', project=project, work_category=category, project_evidence=project_evidence, category_evidence=category_evidence, review_required=review, attribution_scope='Cursor stop-hook parent turn. Uncached input is the reported input minus cache read and cache write. Subagent tokens are absent. Not a provider bill.' if attribute else 'counter records only', input=values[0], output=values[1], cache_read=values[2], cache_write=values[3]))
        projects = {row['project'] for row in file_rows if row['project'] != 'Unknown'}
        mixed = len(projects) > 1
        for row in file_rows:
            row.update(session_mixed=mixed, review_required=row['review_required'] or mixed)
        rows.extend(file_rows)
    return rows, issues
