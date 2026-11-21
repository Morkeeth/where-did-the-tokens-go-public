import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from tokens.cursor import append_turn, counters_from_turn, install_user_hook, normalize_stop
from tokens.inventory import read_usage


class CursorLedger(unittest.TestCase):
    def test_stop_payload_splits_inclusive_input_and_drops_private_fields(self):
        payload = {
            'hook_event_name': 'stop',
            'conversation_id': 'conversation-1',
            'generation_id': 'generation-1',
            'model': 'cursor-grok-4.6-high-fast',
            'model_id': 'grok-4.6',
            'status': 'completed',
            'input_tokens': 1180993,
            'output_tokens': 8146,
            'cache_read_tokens': 1007022,
            'cache_write_tokens': 173957,
            'user_email': 'person@example.com',
            'transcript_path': '/Users/person/private/agent-transcripts/conversation-1.jsonl',
            'workspace_roots': ['/work/harbor-notes', '/work/other'],
            'prompt': 'PRIVATE PROSE NEVER STORED',
        }
        record = normalize_stop(payload, now='2026-11-11T16:09:00Z')
        self.assertEqual(counters_from_turn(record)[:4], (14, 8146, 1007022, 173957))
        encoded = json.dumps(record)
        self.assertNotIn('person@example.com', encoded)
        self.assertNotIn('PRIVATE PROSE', encoded)
        self.assertNotIn('transcript', encoded)
        self.assertEqual(record['model'], 'grok-4.6')
        self.assertTrue(record['multiple_workspaces'])
        self.assertIsNone(normalize_stop({'hook_event_name': 'beforeSubmitPrompt', 'generation_id': 'g', 'input_tokens': 3, 'output_tokens': 1}))
        self.assertIsNone(normalize_stop({'hook_event_name': 'stop', 'generation_id': 'g', 'input_tokens': 0, 'output_tokens': 0}))

    def test_ledger_dedupes_a_generation_and_hides_paths_until_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / 'harbor-notes'
            (project / '.git').mkdir(parents=True)
            ledger = root / 'ledger'
            first = normalize_stop({'hook_event_name': 'stop', 'conversation_id': 'conversation-1', 'generation_id': 'generation-1', 'model': 'Example', 'input_tokens': 10, 'output_tokens': 1, 'workspace_roots': [str(project)], 'user_email': 'person@example.com'}, now='2026-11-11T16:09:00Z')
            second = normalize_stop({'hook_event_name': 'stop', 'conversation_id': 'conversation-1', 'generation_id': 'generation-1', 'model': 'Example', 'input_tokens': 30, 'output_tokens': 4, 'cache_read_tokens': 10, 'cache_write_tokens': 5, 'workspace_roots': [str(project)]}, now='2026-11-11T16:10:00Z')
            missing_cache = normalize_stop({'hook_event_name': 'stop', 'conversation_id': 'conversation-2', 'generation_id': 'generation-2', 'model': 'Example', 'input_tokens': 8, 'output_tokens': 2, 'workspace_roots': [str(project)]}, now='2026-11-11T16:11:00Z')
            for record in (first, second, missing_cache):
                append_turn(ledger, record)
            hidden = read_usage([('Cursor', str(ledger))])
            self.assertEqual(sum(row['input'] + row['output'] + row['cache_read'] + row['cache_write'] for row in hidden['rows']), 8 + 2 + (30 - 10 - 5) + 4 + 10 + 5)
            self.assertNotIn('person@example.com', json.dumps(hidden))
            self.assertNotIn(str(project), json.dumps(hidden))
            self.assertTrue(all(row['project'] == 'Unknown' and row['folder'] == 'Hidden folder' for row in hidden['rows']))
            shown = read_usage([('Cursor', str(ledger))], attribute=True)
            self.assertTrue(all(row['project'] == 'harbor-notes' for row in shown['rows']))
            uncertain = [row for row in shown['rows'] if row['session'] != shown['rows'][0]['session'] or 'cache fields absent' in row['category_evidence']]
            self.assertTrue(any('cache fields absent' in row['category_evidence'] and row['review_required'] for row in shown['rows']))
            self.assertNotIn(str(project), json.dumps(shown))
            self.assertTrue(uncertain)

    def test_install_keeps_existing_hooks_and_refuses_a_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            hooks = home / '.cursor' / 'hooks.json'
            hooks.parent.mkdir()
            hooks.write_text(json.dumps({'version': 1, 'hooks': {'afterFileEdit': [{'command': './hooks/format.sh'}]}}))
            install_user_hook(home, command='python3 -m tokens.cursor_hook')
            saved = json.loads(hooks.read_text())
            self.assertEqual(saved['hooks']['afterFileEdit'][0]['command'], './hooks/format.sh')
            self.assertEqual(saved['hooks']['stop'], [{'command': 'python3 -m tokens.cursor_hook'}])
            install_user_hook(home, command='python3 -m tokens.cursor_hook')
            self.assertEqual(json.loads(hooks.read_text())['hooks']['stop'], [{'command': 'python3 -m tokens.cursor_hook'}])
            self.assertTrue((home / '.cursor' / 'usage-ledger').is_dir())
            linked = home / 'linked-ledger' / 'turns.jsonl'
            linked.parent.mkdir()
            linked.write_text('')
            alias = home / 'alias-ledger'
            alias.mkdir()
            os.symlink(linked, alias / 'turns.jsonl')
            with self.assertRaises(OSError):
                append_turn(alias, {'type': 'cursor_turn'})

    def test_hook_process_writes_counters_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'usage-ledger'
            payload = json.dumps({'hook_event_name': 'stop', 'conversation_id': 'c', 'generation_id': 'g', 'model_id': 'Example', 'input_tokens': 12, 'output_tokens': 3, 'cache_read_tokens': 4, 'cache_write_tokens': 1, 'user_email': 'person@example.com', 'transcript_path': '/secret/transcript.jsonl'})
            completed = subprocess.run([sys.executable, '-m', 'tokens.cursor_hook', '--ledger', str(ledger)], input=payload, capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), '{}')
            text = (ledger / 'turns.jsonl').read_text()
            self.assertNotIn('person@example.com', text)
            self.assertNotIn('transcript', text)
            self.assertIn('"generation_id":"g"', text)
            printed = subprocess.run([sys.executable, '-m', 'tokens.cursor_hook', '--print'], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(printed.returncode, 0)
            self.assertIn('tokens.cursor_hook', printed.stdout)


if __name__ == '__main__':
    unittest.main()
