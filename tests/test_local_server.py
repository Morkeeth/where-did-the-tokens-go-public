import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError,URLError
from tokens.inventory import read_usage
from tokens.attribution import project_identity

ROOT=Path(__file__).resolve().parents[1]

class LocalServer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.logs=self.home/'.claude/projects/sample';self.logs.mkdir(parents=True)
        self.secret='PRIVATE_TEST_PROMPT_CANARY';self.path=self.logs/'session.jsonl'
        events=[{'type':'user','timestamp':'2025-06-01T10:00:00Z','message':{'content':self.secret}},
            {'type':'assistant','timestamp':'2025-06-01T10:00:01Z','cwd':'/tmp/harbor-notes','message':{'id':'sample-message','model':'Synthetic model A','usage':{'input_tokens':40,'output_tokens':7},'content':[{'type':'tool_use','name':'SendMessage','input':{'command':'never execute recorded tool arguments'}},{'type':'text','text':'Synthetic reply'}]}}]
        self.path.write_text('\n'.join(map(json.dumps,events)));self.original=self.path.read_bytes()
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.url='http://127.0.0.1:'+str(self.port);self.opener=build_opener(ProxyHandler({}))
        # Audit hook makes accidental private reads before a consented API call,
        # provider connections and recorded-command execution fail in the server.
        code="""import sys,socket,subprocess
from pathlib import Path
from tokens import inventory
allowed={'read':False}
original=inventory.read_usage
transcript=inventory.local_transcript
def read(*a,**kw):
 allowed['read']=True
 try:return original(*a,**kw)
 finally:allowed['read']=False
def text(*a,**kw):
 allowed['read']=True
 try:return transcript(*a,**kw)
 finally:allowed['read']=False
def hook(event,args):
 if event=='open' and str(args[0]).endswith('session.jsonl') and not allowed['read']:raise RuntimeError('Record read before consent')
 if event=='socket.connect' and args[1][0] not in ('127.0.0.1','::1'):raise RuntimeError('Nonloopback egress')
 if event=='subprocess.Popen':raise RuntimeError('Unexpected subprocess')
sys.addaudithook(hook)
inventory.read_usage=read;inventory.local_transcript=text
inventory.main()
"""
        env=dict(os.environ,HOME=str(self.home),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
        self.process=subprocess.Popen([sys.executable,'-c',code,'--port',str(self.port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        for _ in range(100):
            if self.process.poll() is not None:raise AssertionError(self.process.communicate())
            try:self.page=self.opener.open(self.url,timeout=.3).read().decode();break
            except (OSError,URLError):time.sleep(.03)
        else:raise AssertionError('server did not start')
        self.token=re.search("const scanToken='([^']+)'",self.page)[1]

    def tearDown(self):
        if hasattr(self,'process'):
            self.process.terminate();self.process.communicate(timeout=5)
        self.tmp.cleanup()

    def request(self,path,body=None,token=True,host=None):
        headers={}
        if token:headers['X-Inventory-Token']=self.token
        if host:headers['Host']=host
        if body is not None:headers['Content-Type']='application/json'
        return json.load(self.opener.open(Request(self.url+path,json.dumps(body).encode() if body is not None else None,headers)))

    def test_empty_then_consented_private_capture_and_revoke(self):
        with self.assertRaises(HTTPError) as no_cap:self.request('/api/usage',token=False)
        self.assertEqual(no_cap.exception.code,403)
        self.assertEqual(self.request('/api/usage')['rows'],[])
        with self.assertRaises(HTTPError):self.request('/api/scan',{'consent':False,'agents':['Claude Code']})
        with self.assertRaises(HTTPError) as wrong_host:self.request('/api/discovery',host='outside.invalid')
        self.assertEqual(wrong_host.exception.code,403)
        usage=self.request('/api/scan',{'consent':True,'agents':['Claude Code'],'auto_attribution':True})
        self.assertEqual(sum(r['input']+r['output'] for r in usage['rows']),47)
        self.assertNotIn(self.secret,json.dumps(usage));self.assertNotIn(str(self.home),json.dumps(usage))
        row=usage['rows'][0];self.assertEqual(row['work_category'],'Agent-to-agent');self.assertEqual(row['project'],'harbor-notes')
        self.assertGreater(row['unpriced_tokens'],0)
        self.request('/api/assign',{'consent':True,'scope':'counter_interval','row_id':row['row_id'],'project':'Trail Planner','work_category':'Project work'})
        summary=self.request('/api/summary');self.assertIn('Trail Planner',json.dumps(summary));self.assertNotIn(self.secret,json.dumps(summary));self.assertNotIn(row['session'],json.dumps(summary))
        text=self.request('/api/transcript',{'consent':True,'session':row['session']});self.assertIn(self.secret,text['text'])
        self.request('/api/revoke',{'consent':True});self.assertEqual(self.request('/api/usage')['rows'],[])
        with self.assertRaises(HTTPError):self.request('/api/transcript',{'consent':True,'session':row['session']})
        self.assertEqual(self.path.read_bytes(),self.original)

    def test_agent_cli_requires_scope_before_reading_and_accepts_only_loopback(self):
        for args in [['summary','--url',self.url],['summary','--allow-summary','--url','https://outside.invalid']]:
            p=subprocess.run([sys.executable,'-m','tokens.agent',*args],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
        p=subprocess.run([sys.executable,'-m','tokens.agent','summary','--allow-summary','--url',self.url],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['window']['from'],None)

    def test_foreign_platform_paths_do_not_become_project_labels(self):
        project,_,_=project_identity(cwd='C:\\Users\\example\\work\\harbor-notes')
        self.assertEqual(project,'harbor-notes')
