import json
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
import unittest
from backend.programmes import bfi_records,wpo_records,diaphana_records
from backend.storage import Store
from backend.timing import instant_passed
from backend.jobs import notify
from scripts.audit_data import audit_payload

class ProgrammeChecks(unittest.TestCase):
    def source(self,**extra):
        return {'id':'test-programme','name':'Test','homepage_url':'https://example.invalid','channels':['film'],'country':'GB','city':'伦敦','language':'en','source_type':'official','adapter':'bfi_programme','feed_url':'https://example.invalid/default.asp','access_status':'reviewed','access_method':'public_page','enabled':True,'verified_at':'2026-10-13',**extra}

    def bfi_page(self,when='Sunday 25 October 2026 11:45'):
        names=['id','object_type','data3','description','start_date','venue_description','additional_info','min_price','max_price','availability_status']
        rows=[['same-session','P','LFFGALA','Test film',when,'BFI Southbank, NFT1','default.asp?article_id=film&BOparam::WScontent::loadArticle::context_id=same-session','£10','£18','S'],['talk','P','LFFFREE','Podcast talk',when,'BFI','default.asp?article_id=talk','£0','£0','G']]
        return ('<title>BFI London Film Festival 2026</title><script>var ctx={searchNames:'+json.dumps(names)+',searchResults:'+json.dumps(rows)+'};</script>').encode()

    def test_festival_real_times_dst_and_identity_survive_schedule_change(self):
        src=self.source();content,events,links=bfi_records(src,self.bfi_page())
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['start_at'],'2026-10-25T11:45:00+00:00')
        self.assertEqual(events[0]['booking_status'],'sold_out')
        changed=bfi_records(src,self.bfi_page('Sunday 25 October 2026 12:45'))[1][0]
        self.assertEqual(changed['id'],events[0]['id'])
        with TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.db');store.register_sources([src]);store.ingest_records(content,events,links);bookmark=store.save_bookmark('event',events[0]['id']);store.ingest_records(content,[changed],links)
            self.assertEqual(store.bookmarks()[0]['id'],bookmark['id'])
            self.assertEqual(store.dataset('live')['events'][0]['start_at'],changed['start_at'])

    def test_photography_clock_conflict_is_not_replaced_with_a_guess(self):
        src=self.source(country='GLOBAL',city=None,timezone='UTC',channels=['photography'],adapter='wpo_calls',entry_label_zh='学生组',entry_host='example.invalid')
        body='<div id="block-wpo-content"><article><h1>Student competition</h1>Deadline for entries is 27 November 2026 at 16:00 (GMT). Entries must be submitted by 16.00 GMT on 27 November 2026. Entries to be uploaded by 13.00 GMT on 27 November 2026. Free to enter.<a href="https://example.invalid/competition/171/categories">Enter competition</a></article></div>'
        content,events,links=wpo_records(src,body)
        event=events[0]
        self.assertIn('/competition/171/',event['booking_url']);self.assertEqual(event['time_status'],'conflict');self.assertIsNone(event['deadline_at']);self.assertEqual(event['country'],'GLOBAL')
        report=audit_payload({'content':content,'events':events,'content_events':links},{'sources':[src]},'2026-10-13')
        self.assertFalse(report['errors']);self.assertEqual(report['warnings'][0]['code'],'conflicting_official_time')
        body=body.replace('13.00 GMT','16.00 GMT')
        exact=wpo_records(src,body)[1][0]
        self.assertEqual(exact['deadline_at'],'2026-11-27T16:00:00+00:00');self.assertEqual(exact['id'],event['id'])
        with TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'time-change.db');store.register_sources([src]);store.ingest_records(content,[exact],links);store.ingest_records(content,[event],links)
            self.assertIsNone(store.dataset('live')['events'][0]['deadline_at'])
        self.assertTrue(instant_passed(exact,datetime(2026,11,27,16,1,tzinfo=timezone.utc)))
        self.assertFalse(instant_passed(exact,datetime(2026,11,27,15,59,tzinfo=timezone.utc)))

    def test_release_requires_full_year_not_article_publication_or_film_year(self):
        src=self.source(country='FR',city=None,adapter='diaphana_releases')
        def card(title,dates):return f'<div class="slide-content"><div class="slide-title">{title}</div><div class="slide-date">{dates}</div><a href="/film/{title}">Film</a></div>'
        c,e,l=diaphana_records(src,card('one','21 octobre 2026')+card('no-year','18 novembre')+'<article>2026 film, published 2026-10-13</article>')
        self.assertEqual(len(e),1);self.assertEqual(e[0]['start_date'],'2026-10-21');self.assertEqual(e[0]['country'],'FR');self.assertIsNone(c[0]['published_at'])

    def test_deadline_reminder_title_refreshes_without_duplicate_or_clock_conflict(self):
        with TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'reminders.db');source=self.source(country='GLOBAL',city=None,adapter='wpo_calls');store.register_sources([source])
            from backend.ingestion import content_record,event_record
            content=content_record(source,'Call','https://example.invalid/call')
            event=event_record(source,content,'call_deadline','2027-01-05',country='GLOBAL',timezone='UTC');event['time_status']='conflict'
            store.ingest_records([content],[event],[{'content_id':content['id'],'event_id':event['id']}]);store.save_bookmark('event',event['id'])
            self.assertEqual(notify(store,'2027-01-01'),1);self.assertEqual(notify(store,'2027-01-02'),0)
            with store.connect() as db:
                title=db.execute('SELECT title FROM notifications').fetchone()[0]
            self.assertIn('3天后截止',title)
            self.assertEqual(notify(store,'2027-01-05'),0)
