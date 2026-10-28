import importlib.util
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import unittest
import zipfile
from tokens.pricing import estimate_usage,load_rates
from tokens.demo import sample_usage,SAMPLE_RATES

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',ROOT/'tools/audit_release.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class TextOutsideScript(HTMLParser):
    def __init__(self):super().__init__();self.inside=None;self.text=[];self.scripts=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.inside=tag
        if tag=='script':self.scripts+=1
    def handle_endtag(self,tag):
        if tag==self.inside:self.inside=None
    def handle_data(self,data):
        if not self.inside:self.text.append(data)

class Release(unittest.TestCase):
    def test_javascript_cannot_accidentally_be_visible_as_page_text(self):
        page=(ROOT/'tokens/web/inventory.html').read_text();parser=TextOutsideScript();parser.feed(page);visible=''.join(parser.text)
        self.assertEqual(parser.scripts,1);self.assertNotIn('const scanToken',visible);self.assertNotIn('function render',visible);self.assertIn('Claude Code and Codex JSONL counters',visible)
        self.assertEqual(page.count('const scanToken'),1)

    def test_unknown_prices_are_not_zero_and_partial_prices_remain_partial(self):
        usage=sample_usage();unknown=estimate_usage(usage,{})
        self.assertGreater(sum(r['unpriced_tokens'] for r in unknown['rows']),0)
        self.assertTrue(all(r['estimated_usd']==0 for r in unknown['rows']))
        partial=estimate_usage(usage,{'Synthetic model A':{'input':1}})
        self.assertGreater(sum(r['estimated_usd'] for r in partial['rows']),0);self.assertGreater(sum(r['unpriced_tokens'] for r in partial['rows']),0)
        full=estimate_usage(usage,SAMPLE_RATES);self.assertEqual(sum(r['unpriced_tokens'] for r in full['rows']),0)

    def test_rates_reject_nonfinite_or_negative_numbers(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'rates.json'
            for value in [-1,float('inf'),True]:
                path.write_text(json.dumps({'model':{'input':value}}))
                with self.assertRaises(ValueError):load_rates(path)

    def test_archive_guard_exercises_a_nested_leak(self):
        canary='GUARD_CANARY_NOT_FOR_RELEASE';outer=io.BytesIO();inner=io.BytesIO()
        with zipfile.ZipFile(inner,'w') as z:z.writestr('data.txt',canary)
        with zipfile.ZipFile(outer,'w') as z:z.writestr('nested.zip',inner.getvalue())
        failures=[]
        for name,content in audit.entries('outer.zip',outer.getvalue()):failures+=audit.inspect(name,content,[canary])
        self.assertEqual(len(failures),1);self.assertIn('nested.zip!data.txt',failures[0][0])

    def test_audit_plain_source_and_source_zip_without_git(self):
        from tools.build_release import FILES
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);plain=base/'plain';plain.mkdir();archive_path=base/'source.zip'
            with zipfile.ZipFile(archive_path,'w') as archive:
                for filename in FILES:
                    target=plain/filename;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/filename,target)
                    archive.write(ROOT/filename,filename)
            extracted=base/'extracted'
            with zipfile.ZipFile(archive_path) as archive:archive.extractall(extracted)
            for source in (plain,extracted):
                output=source/'artifacts';output.mkdir();(output/'example.txt').write_text('Synthetic audit example')
                command=[sys.executable,str(source/'tools/audit_release.py'),str(output)]
                result=subprocess.run(command,cwd=source,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                report=json.loads(result.stdout);self.assertGreater(report['checked_entries'],len(FILES));self.assertEqual(report['failures'],[])
                history=subprocess.run(command+['--history'],cwd=source,capture_output=True,text=True)
                self.assertNotEqual(history.returncode,0);self.assertIn('--history requires',history.stderr);self.assertNotIn('Traceback',history.stderr)
