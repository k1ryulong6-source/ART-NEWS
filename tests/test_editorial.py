import copy
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from backend.editorial import ContextTranslator, checked_result, run_editorial, rules
from backend.storage import Store
from backend.ingestion import content_record
from backend.articles import collect_articles


class EditorialTests(unittest.TestCase):
    def setUp(self):
        current_rules=rules(); legacy=patch("backend.editorial.rules",return_value={**current_rules,"quality_mode":"reviewed"});legacy.start();self.addCleanup(legacy.stop)
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name)/'quality.db')
        self.source = {'id':'film-stage','name':'Film Stage','homepage_url':'https://thefilmstage.com',
                       'channels':['film'],'language':'en','source_type':'media','access_status':'reviewed',
                       'access_method':'rss','verified_at':'2026-10-13','enabled':True,'adapter':'rss'}
        self.store.register_sources([self.source])
        row = content_record(self.source,'Festival 2026','https://thefilmstage.com/festival',excerpt='Films and filmmakers.')
        self.store.ingest_records([row],[],[])
        body = 'The exhibition opens in 2026 and admission costs 600 yen. ' + 'A director discusses the relationship between images and memory. '*5
        collect_articles(self.store,1,getter=lambda url,source:('<div class="entry-content"><h2>A conversation</h2><p>'+body+'</p></div>',url))
        self.row=self.store.dataset('live')['content'][0]
        self.result={'title_zh':'2026年电影节','excerpt_zh':'电影与创作者。','blocks':[{'index':0,'text':'一场对话'},{'index':1,'text':'展览于2026年开幕，门票600日元。导演谈论影像与记忆之间的关系。'}],'notes':[]}

    def provider(self,rejected=False):
        expected=self.result
        def transport(payload):
            document=json.loads(payload['messages'][1]['content'])
            if 'original' in document:
                self.assertEqual(len(document['original']['blocks']),2)
                output={'approved':not rejected,'issues':['译名有待确认'] if rejected else [],'translation':expected}
            else:
                self.assertEqual(document['title_original'],'Festival 2026')
                self.assertIn('600',document['blocks'][1]['text'])
                self.assertIn('glossary',document['rules'])
                output=expected
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(output)}}]}
        return ContextTranslator(model='draft-model',review_model='review-model',transport=transport)

    def test_draft_is_not_published_until_separate_review_passes_and_retry_resumes_it(self):
        p=self.provider();first=run_editorial(self.store,p,daily_limit=1)
        self.assertEqual(first['status'],'budget_exhausted')
        row=self.store.dataset('live')['content'][0];self.assertEqual(row['editorial_status'],'draft');self.assertIsNone(row['editorial_blocks_json'])
        second=run_editorial(self.store,p,daily_limit=3)
        self.assertEqual(second['reviewed'],1);self.assertEqual(second['calls'],1)
        row=self.store.dataset('live')['content'][0];self.assertEqual(row['article_text'],self.row['article_text'])
        self.assertEqual(row['editorial_model'],'draft-model');self.assertEqual(row['editorial_review_model'],'review-model')
        self.assertEqual(run_editorial(self.store,p,daily_limit=3)['calls'],0)
        snapshot=self.store.dataset('live');snapshot['editorial_usage']=[{'day':'2026-10-13','calls':9}]
        file=Path(self.tmp.name)/'saved.json';file.write_text(json.dumps(snapshot));self.store.restore_public_snapshot(file)
        with self.store.connect() as db:self.assertEqual(db.execute("SELECT calls FROM editorial_usage WHERE day='2026-10-13'").fetchone()[0],9)

    def test_rejected_review_never_exposes_a_ready_translation(self):
        result=run_editorial(self.store,self.provider(rejected=True),daily_limit=3)
        self.assertEqual(result['rejected'],1)
        row=self.store.dataset('live')['content'][0];self.assertEqual(row['editorial_status'],'rejected');self.assertIsNone(row['editorial_blocks_json'])

    def test_missing_paragraph_changed_number_or_untranslated_body_is_rejected(self):
        short=copy.deepcopy(self.result);short['blocks'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'):checked_result(self.row,short)
        bad=copy.deepcopy(self.result);bad['blocks'][1]['text']='展览于2026年开幕，门票60日元。'
        with self.assertRaisesRegex(ValueError,'numbers'):checked_result(self.row,bad)
        bad=copy.deepcopy(self.result);bad['blocks'][1]['text']=json.loads(self.row['article_blocks_json'])[1]['text']
        with self.assertRaisesRegex(ValueError,'not_translated'):checked_result(self.row,bad)

    def test_source_change_during_review_cannot_publish_stale_translation(self):
        provider=self.provider();review=provider.review
        def changed(row,draft):
            with self.store.connect() as db:db.execute("UPDATE content SET article_hash='changed' WHERE id=?",(row['id'],))
            return review(row,draft)
        provider.review=changed
        self.assertEqual(run_editorial(self.store,provider,daily_limit=3)['changed_during_request'],1)
        self.assertIsNone(self.store.dataset('live')['content'][0]['editorial_blocks_json'])

    def test_missing_credentials_does_not_fall_back_to_google_or_disable_sources(self):
        with patch.dict('os.environ',{'EDITORIAL_PROVIDER':'openai-compatible','EDITORIAL_API_KEY':''}):result=run_editorial(self.store)
        self.assertEqual(result['status'],'not_configured')
        self.assertEqual(self.store.dataset('live')['content'][0]['article_text'],self.row['article_text'])
        self.assertEqual(len(self.store.dataset('live')['content']),1)

    def test_chatgpt_task_mode_needs_no_external_api_and_records_its_actual_mode(self):
        with patch.dict('os.environ',{'EDITORIAL_PROVIDER':'chatgpt-task','EDITORIAL_API_KEY':''}), patch('backend.editorial.ContextTranslator',side_effect=AssertionError('API must not be called')):
            result=run_editorial(self.store)
        self.assertEqual(result['status'],'chatgpt_task')
        with self.store.connect() as db:
            status=json.loads(db.execute("SELECT value FROM job_state WHERE id='last-editorial'").fetchone()[0])
        self.assertEqual(status['status'],'chatgpt_task')

    def test_direct_mode_spends_one_call_and_does_not_invoke_review(self):
        provider=self.provider()
        provider.review=lambda *args: (_ for _ in ()).throw(AssertionError('User opted out of review'))
        with patch('backend.editorial.rules',return_value={**rules(),'quality_mode':'direct-ai'}):
            result=run_editorial(self.store,provider,daily_limit=1)
        self.assertEqual(result['calls'],1);self.assertEqual(result['direct_translated'],1)
        row=self.store.dataset('live')['content'][0]
        self.assertEqual(row['editorial_status'],'translated');self.assertIsNone(row['editorial_review_model'])
        self.assertFalse(json.loads(row['editorial_review_json'])['approved'])
