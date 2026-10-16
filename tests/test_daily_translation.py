import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.daily_translation import import_packs, prepare_queue
from backend.articles import collect_articles
from backend.ingestion import content_record
from backend.storage import Store
from backend.editorial import publish_translation


class DailyTranslationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.store=Store(self.root/'daily.db')
        source={'id':'film-stage','name':'Film Stage','homepage_url':'https://thefilmstage.com',
                'channels':['film'],'language':'en','source_type':'media','access_status':'reviewed',
                'access_method':'rss','verified_at':'2026-10-13','enabled':True,'adapter':'rss'}
        self.store.register_sources([source]);row=content_record(source,'Festival 2026','https://thefilmstage.com/daily',excerpt='Festival introduction.')
        self.store.ingest_records([row],[],[]);collect_articles(self.store,1,getter=lambda url,source:('<div class="entry-content"><p>The festival starts in 2026 and tickets cost 600 yen. '+('Many directors will discuss their new work. '*5)+'</p></div>',url))
        self.row=self.store.dataset('live')['content'][0];self.store.save_bookmark('content',self.row['id'])
        self.directory=self.root/'packs';self.directory.mkdir()
        self.pack={'schema_version':1,'id':self.row['id'],'source_hash':self.row['article_hash'],
                   'source_title':self.row['title_original'],'execution':'scheduled',
                   'translation':{'title_zh':'2026年电影节','excerpt_zh':'电影节介绍。',
                                  'blocks':[{'index':0,'text':'电影节于2026年开始，门票600日元。多位导演将谈论各自的新作。'}],'notes':[]},
                   'review':{'approved':True,'issues':[],'method':'AI逐段对照原文校对'}}

    def write(self):
        (self.directory/(self.row['id']+'.json')).write_text(json.dumps(self.pack))

    def test_reviewed_task_pack_publishes_once_and_keeps_originals_and_bookmarks(self):
        self.write();self.assertEqual(import_packs(self.store,self.directory)['imported'],[self.row['id']])
        saved=self.store.dataset('live')['content'][0]
        self.assertEqual(saved['article_text'],self.row['article_text']);self.assertEqual(len(self.store.bookmarks()),1)
        self.assertEqual(saved['editorial_status'],'reviewed')
        self.assertEqual(import_packs(self.store,self.directory)['unchanged'],[self.row['id']])

    def test_stale_or_unreviewed_or_missing_paragraph_pack_cannot_publish(self):
        self.pack['source_hash']='stale';self.write();self.assertEqual(import_packs(self.store,self.directory)['stale'],[self.row['id']])
        self.pack['source_hash']=self.row['article_hash'];self.pack['review']['approved']=False;self.write();self.assertTrue(import_packs(self.store,self.directory)['invalid'])
        self.pack['review']['approved']=True;self.pack['translation']['blocks']=[];self.write();self.assertTrue(import_packs(self.store,self.directory)['invalid'])
        self.assertIsNone(self.store.dataset('live')['content'][0]['editorial_blocks_json'])

    def test_queue_retains_all_source_inputs_but_removes_published_from_pending(self):
        snapshot=self.store.dataset('live');result=prepare_queue(snapshot,self.root/'public');self.assertEqual(result['pending'],1)
        input_file=self.root/'public/translation-input'/(self.row['id']+'.json')
        original=json.loads(input_file.read_text());self.assertEqual(original['article_hash'],self.row['article_hash'])
        self.assertEqual(original['blocks'],json.loads(self.row['article_blocks_json']))
        self.write();import_packs(self.store,self.directory);result=prepare_queue(self.store.dataset('live'),self.root/'public');self.assertEqual(result['pending'],0);self.assertTrue(input_file.exists())

    def test_direct_fast_model_pack_publishes_without_false_review_approval(self):
        self.pack.update(quality_mode='direct-ai',draft_model='gpt-6-luna (session worker)')
        self.pack['review']={'approved':False,'status':'not_requested','issues':[],'method':'AI直接翻译'}
        self.write();self.assertEqual(import_packs(self.store,self.directory)['imported'],[self.row['id']])
        row=self.store.dataset('live')['content'][0]
        self.assertEqual(row['editorial_status'],'translated');self.assertIsNone(row['editorial_review_model'])
        self.assertEqual(row['editorial_model'],'gpt-6-luna (session worker)')
        self.assertEqual(import_packs(self.store,self.directory)['unchanged'],[self.row['id']])
        self.assertEqual(prepare_queue(self.store.dataset('live'),self.root/'public')['pending'],0)

    def test_api_completion_after_pack_creation_is_preserved(self):
        self.pack.update(quality_mode='direct-ai', draft_model='current conversation')
        self.pack['review']={'approved':False,'status':'not_requested','issues':[],'method':'Direct translation'}
        self.write()
        publish_translation(self.store, self.row, self.pack['translation'],
                            'contextual-api:gemini:test', 'gemini-test', None, self.pack['review'])
        before=self.store.dataset('live')['content'][0]
        report=import_packs(self.store,self.directory)
        self.assertEqual(report['imported'],[])
        self.assertEqual(report['unchanged'],[self.row['id']])
        self.assertEqual(self.store.dataset('live')['content'][0],before)

    def test_invalid_existing_copy_does_not_block_valid_pack(self):
        with self.store.connect() as db:
            db.execute("UPDATE content SET editorial_status='translated',editorial_title_zh='不完整译文',editorial_blocks_json='[]' WHERE id=?", (self.row['id'],))
        self.write()
        self.assertEqual(import_packs(self.store,self.directory)['imported'],[self.row['id']])
        self.assertEqual(self.store.dataset('live')['content'][0]['editorial_status'],'reviewed')
