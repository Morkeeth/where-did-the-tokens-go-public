import json
from pathlib import Path
import tempfile
import unittest
from tokens.inventory import read_usage
from tokens.connections import discovery

class ProductTest(unittest.TestCase):
    def test_metadata_axes_streaming_and_counter_conservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);logs=root/'logs';logs.mkdir();alpha=root/'alpha';beta=root/'beta'
            for p in (alpha,beta):(p/'.git').mkdir(parents=True)
            stamp='2026-10-26T08:00:00Z'
            def a(identity,cwd=None,inp=0,out=0,tool=None):
                e={'type':'assistant','timestamp':stamp,'sessionId':'mixed','message':{'id':identity,'model':'Example','usage':{'input_tokens':inp,'output_tokens':out},'content':[{'type':'text','text':'PRIVATE PROSE NEVER USED'}]}}
                if cwd:e['cwd']=str(cwd)
                if tool:e['message']['content'].append({'type':'tool_use','name':tool,'input':{'secret':'NEVER RETAIN'}})
                return e
            events=[a('m1',alpha,10,2),a('m1',alpha,10,5),a('m2',None,3,1,'SendMessage'),a('m3',beta,7,2),a('m4','/tmp',4,1)]
            path=logs/'mixed.jsonl';path.write_text('\n'.join(map(json.dumps,events)));original=path.read_bytes()
            result=read_usage([('Claude Code',str(logs))], attribute=True);rs=result['rows']
            self.assertEqual(sum(r['input'] for r in rs),24);self.assertEqual(sum(r['output'] for r in rs),9)
            self.assertTrue(any(r['project']=='alpha' and r['work_category']=='Agent-to-agent' for r in rs))
            self.assertTrue(any(r['project']=='beta' and r['work_category']=='Project work' for r in rs))
            self.assertTrue(any(r['project']=='Unknown' and r['review_required'] for r in rs))
            self.assertTrue(all(r['session_mixed'] for r in rs));self.assertTrue(all('interval_start' in r for r in rs))
            self.assertNotIn('PRIVATE PROSE',json.dumps(result));self.assertNotIn('NEVER RETAIN',json.dumps(result))
            without=read_usage([('Claude Code',str(logs))],attribute=False)
            self.assertEqual(sum(r['input']+r['output'] for r in without['rows']),33)
            self.assertTrue(all(r['project']=='Unknown' and r['work_category']=='Unknown' for r in without['rows']))
            default=read_usage([('Claude Code',str(logs))])
            self.assertEqual(default,without)
            self.assertTrue(all(r['folder']=='Hidden folder' and r['attribution_scope']=='counter records only' for r in default['rows']))
            for private in (str(root),'alpha','beta','SendMessage'):
                self.assertNotIn(private,json.dumps(default))
            self.assertEqual(path.read_bytes(),original)

    def test_codex_interval_metadata_and_parent_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);alpha=root/'alpha';beta=root/'beta'
            for p in (alpha,beta):(p/'.git').mkdir(parents=True)
            claude=root/'claude';codex=root/'codex';claude.mkdir();codex.mkdir();t='2026-10-26T08:00:00Z'
            parent={'type':'assistant','timestamp':t,'sessionId':'parent-one','cwd':str(alpha),'message':{'id':'a','usage':{'input_tokens':1}}}
            child={'type':'assistant','timestamp':t,'sessionId':'child','parentSessionId':'parent-one','message':{'id':'b','usage':{'input_tokens':2}}}
            (claude/'parent.jsonl').write_text(json.dumps(parent));(claude/'child.jsonl').write_text(json.dumps(child))
            es=[{'type':'session_meta','timestamp':t,'payload':{'id':'c','cwd':str(alpha)}},{'type':'response_item','timestamp':t,'payload':{'type':'function_call','name':'SendMessage'}},{'type':'event_msg','timestamp':t,'payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':100,'cached_input_tokens':40,'output_tokens':5}}}},{'type':'turn_context','timestamp':t,'payload':{'cwd':str(beta)}},{'type':'event_msg','timestamp':t,'payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':150,'cached_input_tokens':60,'output_tokens':10}}}}]
            (codex/'c.jsonl').write_text('\n'.join(map(json.dumps,es)))
            rs=read_usage([('Claude Code',str(claude)),('Codex',str(codex))], attribute=True)['rows'];c=[r for r in rs if r['harness']=='Codex']
            self.assertEqual(sum(r['input']+r['output']+r['cache_read'] for r in c),160)
            self.assertEqual({r['project'] for r in c},{'alpha','beta'});self.assertEqual(c[0]['work_category'],'Agent-to-agent')
            inherited=[r for r in rs if 'parent session' in r['project_evidence']];self.assertEqual(len(inherited),1);self.assertEqual(inherited[0]['project'],'alpha');self.assertTrue(inherited[0]['review_required']);self.assertEqual(inherited[0]['work_category'],'Unknown')
            d=discovery([('Claude Code',str(root/'missing')),('Codex',str(codex))]);self.assertEqual(d['harnesses'][0]['status'],'not_found');self.assertEqual(d['harnesses'][1]['status'],'discovered');self.assertEqual(d['harnesses'][2]['status'],'unsupported');self.assertFalse(d['content_read'])

if __name__=='__main__':unittest.main()
