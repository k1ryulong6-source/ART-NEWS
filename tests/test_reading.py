import json
import unittest
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.storage import Store
from backend.ingestion import content_record,rss_records
from backend.reading import public_url,short_excerpt,page_fields
from backend.translation import run_translation

class ReadingChecks(unittest.TestCase):
 def setUp(self):
  self.temp=TemporaryDirectory();self.store=Store(Path(self.temp.name)/'reader.db')
  self.source={'id':'reading-fixture','name':'Public reader fixture','homepage_url':'https://example.org/','feed_url':'https://example.org/feed','source_type':'media','channels':['photography'],'language':'en','adapter':'rss','enabled':True,'access_status':'reviewed','access_method':'rss','verified_at':'2026-10-13'}
  self.store.register_sources([self.source])
 def tearDown(self):self.temp.cleanup()
 def seed(self,excerpt='A photographer explores the changing city.'):
  row=content_record(self.source,'A new photo exhibition','https://example.org/story',excerpt=excerpt)
  self.store.ingest_records([row],[],[]);return row
 def test_feed_image_excerpt_and_page_metadata_are_safe_short_and_attributed(self):
  rss=b'<rss xmlns:media="http://search.yahoo.com/mrss/"><channel><item><title>Photo project</title><link>https://example.org/story</link><description><![CDATA[<p>A public introduction.</p><script>bad()</script>]]></description><media:thumbnail url="https://images.example.org/photo.jpg"/><media:credit>Photographer</media:credit></item></channel></rss>'
  rows,_,_=rss_records(self.source,rss);self.assertEqual(rows[0]['image_credit'],'Photographer');self.assertEqual(rows[0]['excerpt_original'],'A public introduction.')
  for url in ('javascript:alert(1)','http://example.org/a.jpg','https://127.0.0.1/a.jpg','https://user:password@example.org/a.jpg','https://['):self.assertIsNone(public_url(url))
  self.assertLessEqual(len(short_excerpt('word '*1000)),281)
  fields=page_fields(self.source,'https://example.org/story',b'<meta property="og:image" content="/photo.jpg"><meta property="og:description" content="Short original introduction.">')
  self.assertEqual(fields['image_url'],'https://example.org/photo.jpg');self.assertEqual(fields['excerpt_original'],'Short original introduction.')
 def test_translation_caches_requests_keeps_original_and_invalidates_when_excerpt_changes(self):
  row=self.seed();self.store.save_bookmark('content',row['id'])
  class Translator:
   name='fixture-translation';calls=0
   def translate(self,text,language):self.calls+=1;return '中文：'+text
  provider=Translator();self.assertEqual(run_translation(self.store,provider,daily_limit=10)['translated'],1)
  self.assertEqual(provider.calls,2);self.assertEqual(run_translation(self.store,provider,daily_limit=10)['translated'],0)
  cached=self.store.dataset('live')['content'][0];self.assertEqual(cached['title_original'],row['title_original']);self.assertTrue(cached['translated_excerpt_zh'])
  image_only=content_record(self.source,row['title_original'],row['canonical_url'],excerpt=row['raw_excerpt']);image_only['image_url']='https://images.example.org/new.jpg'
  self.store.ingest_records([image_only],[],[]);self.assertEqual(run_translation(self.store,provider,daily_limit=10)['translated'],0)
  self.assertEqual(self.store.dataset('live')['content'][0]['image_url'],image_only['image_url'])
  changed=content_record(self.source,row['title_original'],row['canonical_url'],excerpt='Changed verified introduction.')
  self.store.ingest_records([changed],[],[]);self.assertIsNone(self.store.dataset('live')['content'][0]['translated_excerpt_zh'])
  self.assertEqual(run_translation(self.store,provider,daily_limit=10)['translated'],1);self.assertEqual(len(self.store.bookmarks()),1)
 def test_failed_service_keeps_sources_and_exact_budget_is_restored_across_snapshots(self):
  row=self.seed()
  class Broken:
   name='broken-fixture'
   def translate(self,text,language):raise TimeoutError()
  self.assertEqual(run_translation(self.store,Broken(),daily_limit=1)['failed'],1)
  self.assertEqual(run_translation(self.store,Broken(),daily_limit=1)['budget_exhausted'],1)
  unchanged=self.store.dataset('live')['content'][0];self.assertEqual(unchanged['excerpt_original'],row['excerpt_original']);self.assertIsNone(unchanged['translated_title_zh'])
  snapshot=self.store.dataset('live');snapshot['translation_usage']=[{'day':datetime.now(timezone.utc).date().isoformat(),'calls':3}]
  file=Path(self.temp.name)/'snapshot.json';file.write_text(json.dumps(snapshot))
  for _ in range(2):self.store.restore_public_snapshot(file)
  with self.store.connect() as db:self.assertEqual(db.execute('SELECT calls FROM translation_usage').fetchone()[0],3)
 def test_changed_source_while_request_runs_does_not_receive_stale_translation(self):
  row=self.seed();store=self.store;source=self.source
  class Changed:
   name='changed-fixture';calls=0
   def translate(self,text,language):
    self.calls+=1
    if self.calls==1:store.ingest_records([content_record(source,'Revised title',row['canonical_url'],excerpt='Revised text.')],[],[])
    return '中文：'+text
  result=run_translation(store,Changed(),daily_limit=4);self.assertEqual(result['changed_during_request'],1);self.assertIsNone(store.dataset('live')['content'][0]['translated_title_zh'])
