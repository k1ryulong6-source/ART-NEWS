import unittest
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from backend.originals import embedding_rule,check_originals,SITE_ORIGIN
from backend.storage import Store
from backend.ingestion import content_record

class OriginalChecks(unittest.TestCase):
 def headers(self,**values):
  m=Message()
  for key,value in values.items():m[key.replace('_','-')]=value
  return m
 def test_publisher_frame_rules_are_respected_and_csp_overrides_xfo(self):
  url='https://publisher.example/article'
  self.assertEqual(embedding_rule(self.headers(X_Frame_Options='SAMEORIGIN'),url)[0],'blocked')
  self.assertEqual(embedding_rule(self.headers(X_Frame_Options='deny'),url)[0],'blocked')
  self.assertEqual(embedding_rule(self.headers(Content_Security_Policy="frame-ancestors 'self'"),url)[0],'blocked')
  self.assertEqual(embedding_rule(self.headers(Content_Security_Policy="frame-ancestors https://*.github.io",X_Frame_Options='DENY'),url)[0],'available')
  self.assertEqual(embedding_rule(self.headers(Content_Security_Policy_Report_Only="frame-ancestors 'none'"),url)[0],'available')
  self.assertEqual(embedding_rule(self.headers(Content_Security_Policy='frame-ancestors '+SITE_ORIGIN+':443'),url)[0],'available')
  combined=self.headers(Content_Security_Policy='frame-ancestors '+SITE_ORIGIN);combined['Content-Security-Policy']="frame-ancestors 'none'"
  self.assertEqual(embedding_rule(combined,url)[0],'blocked')
 def test_all_records_remain_even_if_every_publisher_blocks_or_fails(self):
  with TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'reader.db')
   source={'id':'film-stage','name':'Reader fixture','channels':['film'],'language':'en','source_type':'media','homepage_url':'https://thefilmstage.com/','access_status':'reviewed','access_method':'rss','verified_at':'2026-10-13','enabled':True,'adapter':'rss'}
   store.register_sources([source]);rows=[content_record(source,'Story '+str(i),'https://thefilmstage.com/story-'+str(i),excerpt='Short original excerpt.') for i in range(3)]
   store.ingest_records(rows,[],[]);store.save_bookmark('content',rows[0]['id']);ids={r['id'] for r in store.dataset('live')['content']}
   def checker(url):
    if url.endswith('0'):raise HTTPError(url,403,'Forbidden',{},None)
    return {'original_embed_status':'blocked','original_embed_reason':'publisher_x_frame_options'}
   result=check_originals(store,20,checker);self.assertEqual(result['blocked'],2);self.assertEqual(result['unavailable'],1)
   after=store.dataset('live')['content'];self.assertEqual({r['id'] for r in after},ids);self.assertEqual(len(store.bookmarks()),1)
   self.assertTrue(all(r['original_page_url'] for r in after));self.assertEqual(check_originals(store,20,checker)['blocked'],0)
   new=content_record(source,rows[1]['title_original'],rows[1]['canonical_url'],excerpt='Short original excerpt.');new['original_page_url']='https://thefilmstage.com/revised-page'
   store.ingest_records([new],[],[]);changed=next(r for r in store.dataset('live')['content'] if r['id']==new['id']);self.assertIsNone(changed['original_embed_checked_at']);self.assertIsNone(changed['original_embed_status'])
