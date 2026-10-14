import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from backend.coverage import translation_progress, reconcile_rss, audit_sources
from backend.daily_translation import prepare_queue
from backend.ingestion import stable_id
from backend.editorial import numbers


class CoverageTests(unittest.TestCase):
    def test_title_only_and_partial_copy_do_not_inflate_full_translation_progress(self):
        rows=[{'id':'title','language':'en','article_blocks_json':'[]','editorial_title_zh':'中文标题'},
              {'id':'partial','language':'en','article_status':'partial','article_blocks_json':'[]',
               'editorial_status':'reviewed','editorial_blocks_json':'[]','editorial_title_zh':'校译标题'},
              {'id':'native','language':'zh','article_blocks_json':'[]'},
              {'id':'blocked','language':'en'}, {'id':'demo','is_demo':1}]
        p=translation_progress({'content':rows})
        self.assertEqual((p['total'],p['reviewed'],p['reviewed_partial'],p['native_chinese'],p['pending'],p['without_body']),(4,1,1,1,1,1))

    def test_observed_feed_reconciliation_tracks_missing_and_user_requested_exclusions(self):
        source={'id':'source','language':'en','channels':['photography'],'source_type':'media'}
        feed=b'<rss><channel><item><title>Art news</title><link>https://example.org/art</link></item><item><title>New exhibition</title><link>https://example.org/show</link></item><item><title>Camera review</title><link>https://example.org/camera</link></item></channel></rss>'
        snapshot={'content':[{'id':stable_id('https://example.org/art'),'source_id':'source'}]}
        r=reconcile_rss(snapshot,source,feed)
        self.assertEqual((r['observed'],r['eligible'],r['in_inventory']),(3,2,1))
        self.assertEqual(r['missing'][0]['title_original'],'New exhibition')
        self.assertEqual(r['excluded'][0]['reason'],'equipment_review')
        source.update(enabled=True,adapter='rss',feed_url='https://example.org/rss',name='Source',homepage_url='https://example.org')
        def failed(url): raise HTTPError(url,403,'Forbidden',None,None)
        check=audit_sources(snapshot,{'sources':[source]},failed)['sources'][0]
        self.assertEqual(check['status'],'failed');self.assertIsNone(check['missing'])

    def test_full_queue_pages_include_every_pending_article_not_just_shortlist(self):
        with TemporaryDirectory() as tmp:
            rows=[]
            for index in range(75):
                rows.append({'id':'live-'+f'{index:024x}','source_id':'one','language':'en','title_original':'A story',
                             'channel':'art','article_blocks_json':'[{"type":"paragraph","text":"Original"}]',
                             'article_hash':'hash','canonical_url':'https://example.org/'+str(index),'article_status':'collected'})
            snapshot={'content':rows}
            prepare_queue(snapshot,Path(tmp))
            q=json.loads((Path(tmp)/'translation-queue.json').read_text());ids=[]
            for page in q['pending_pages']:
                data=json.loads((Path(tmp)/page['path'].removeprefix('data/')).read_text())
                ids += [r['id'] for r in data['items']]
            self.assertEqual(len(ids),75);self.assertEqual(len(set(ids)),75)
            self.assertLess(len(q['next']),75)
            snapshot['content']=[rows[0]];prepare_queue(snapshot,Path(tmp))
            self.assertEqual(len(list((Path(tmp)/'translation-queue').glob('*.json'))),1)

    def test_natural_chinese_currency_conversion_keeps_numeric_value(self):
        self.assertEqual(numbers('$4.6 million'),numbers('460万美元'))
        self.assertEqual(numbers('$100 million'),numbers('1亿美元'))
        self.assertEqual(numbers('$35 M.'),numbers('3500万美元'))
        self.assertNotEqual(numbers('$4.6 million'),numbers('460美元'))
        self.assertEqual(numbers('2026, 9:30 and 600 yen'),numbers('2026年9:30，600日元'))
