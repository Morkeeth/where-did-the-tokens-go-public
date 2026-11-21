"""Browser consent regression. CI requires Playwright and Google Chrome; local runs use Chrome."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    if os.environ.get('INVENTORY_REQUIRE_BROWSER') == '1':
        raise
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(sync_playwright, 'Optional Playwright browser test')
class BrowserConsent(unittest.TestCase):
    def test_recheck_preserves_disabled_source_and_counter_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            for source in ('.claude/projects', '.codex/sessions'):
                logs = home / source
                logs.mkdir(parents=True)
                # Invented records make the discovery-only scenario independent of personal logs.
                (logs / 'not-yet-permitted.jsonl').write_text('invented invalid record')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            url = f'http://127.0.0.1:{port}'
            process = subprocess.Popen([sys.executable, '-m', 'tokens.inventory', '--port', str(port)],
                cwd=ROOT, env=dict(os.environ, HOME=str(home)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        urlopen(url, timeout=.2).close()
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail('Inventory exited before becoming ready')
                        time.sleep(.03)
                else:
                    self.fail('Inventory did not start within the readiness window')
                with sync_playwright() as pw:
                    channel = os.environ.get('INVENTORY_BROWSER_CHANNEL', 'chrome')
                    try:
                        browser = pw.chromium.launch(channel=channel or None, headless=True, chromium_sandbox=True)
                    except Exception as error:
                        if os.environ.get('INVENTORY_REQUIRE_BROWSER') == '1':
                            raise
                        self.skipTest('Browser unavailable: ' + str(error).splitlines()[0])
                    try:
                        page = browser.new_page(viewport={'width':390, 'height':844})
                        scans = []
                        page.on('request', lambda r: scans.append(r.url) if r.url.endswith('/api/scan') else None)
                        page.goto(url)
                        page.locator('#connectSettings').evaluate('(e) => e.open = true')
                        page.locator('#allowCodex').uncheck()
                        page.locator('#allowCursor').uncheck()
                        page.locator('#autoAttribution').uncheck()
                        page.locator('#allowCodex').evaluate("e => e.dataset.beforeRecheck = 'true'")
                        with page.expect_response('**/api/discover'):
                            page.locator('#discover').click()
                        page.locator('#allowCodex:not([data-before-recheck])').wait_for(state='attached')
                        self.assertFalse(page.locator('#allowCodex').is_checked(), 'Recheck silently re-enabled Codex')
                        self.assertFalse(page.locator('#allowCursor').is_checked(), 'Recheck silently re-enabled Cursor')
                        self.assertFalse(page.locator('#autoAttribution').is_checked())
                        self.assertEqual(scans, [], 'Recheck must not scan counters')
                        page.locator('#allowClaude').uncheck()
                        page.locator('#allowClaude').evaluate("e => e.dataset.beforeRecheck = 'true'")
                        with page.expect_response('**/api/discover'):
                            page.locator('#discover').click()
                        page.locator('#allowClaude:not([data-before-recheck])').wait_for(state='attached')
                        self.assertFalse(page.locator('#allowClaude').is_checked())
                        page.locator('#connect').click()
                        self.assertIn('Choose', page.locator('#connectStatus').inner_text())
                        self.assertEqual(scans, [])
                    finally:
                        browser.close()
            finally:
                process.terminate()
                process.wait(timeout=5)

    def test_cursor_ledger_connects_without_reading_a_transcript(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            project = home / 'harbor-notes'
            (project / '.git').mkdir(parents=True)
            ledger = home / '.cursor' / 'usage-ledger'
            ledger.mkdir(parents=True)
            (ledger / 'turns.jsonl').write_text(
                '{"type":"cursor_turn","timestamp":"2026-11-11T16:09:00Z","conversation_id":"c","generation_id":"g","model":"Example","input_tokens":30,"output_tokens":4,"cache_read_tokens":10,"cache_write_tokens":5,"cwd":"%s"}\n' % project
                + '{"type":"cursor_turn","timestamp":"2026-11-11T16:09:01Z","conversation_id":"c","generation_id":"g","model":"Example","input_tokens":30,"output_tokens":4,"cache_read_tokens":10,"cache_write_tokens":5,"cwd":"%s","prompt":"PRIVATE PROSE"}\n' % project
            )
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            url = f'http://127.0.0.1:{port}'
            process = subprocess.Popen([sys.executable, '-m', 'tokens.inventory', '--port', str(port), '--cursor', str(ledger)],
                cwd=ROOT, env=dict(os.environ, HOME=str(home)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        urlopen(url, timeout=.2).close()
                        break
                    except OSError:
                        if process.poll() is not None:
                            self.fail('Inventory exited before becoming ready')
                        time.sleep(.03)
                else:
                    self.fail('Inventory did not start within the readiness window')
                with sync_playwright() as pw:
                    channel = os.environ.get('INVENTORY_BROWSER_CHANNEL', 'chrome')
                    try:
                        browser = pw.chromium.launch(channel=channel or None, headless=True, chromium_sandbox=True)
                    except Exception as error:
                        if os.environ.get('INVENTORY_REQUIRE_BROWSER') == '1':
                            raise
                        self.skipTest('Browser unavailable: ' + str(error).splitlines()[0])
                    try:
                        page = browser.new_page(viewport={'width': 1280, 'height': 900})
                        page.goto(url)
                        page.locator('#connectSettings').evaluate('(e) => e.open = true')
                        page.locator('#allowClaude').uncheck()
                        page.locator('#allowCodex').uncheck()
                        page.locator('#allowCursor').check()
                        page.locator('#autoAttribution').check()
                        self.assertIn('cursor_hook', page.locator('#harnessCards').inner_text())
                        with page.expect_response('**/api/scan'):
                            page.locator('#connect').click()
                        page.locator('#workspace').wait_for(state='visible')
                        body = page.locator('body').inner_text()
                        self.assertIn('harbor-notes', body)
                        self.assertNotIn('PRIVATE PROSE', body)
                        self.assertNotIn(str(project), body)
                        page.locator('#chartHarness').select_option('Cursor')
                        self.assertGreater(page.locator('#chart .bar').count(), 0)
                    finally:
                        browser.close()
            finally:
                process.terminate()
                process.wait(timeout=5)
