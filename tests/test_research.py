import unittest
import json
from tempfile import TemporaryDirectory
from pathlib import Path
from backend.storage import Store
from backend.ingestion import map_records,zeitz_records,rss_records
from scripts.audit_data import audit_payload

class ResearchChecks(unittest.TestCase):
    def source(self, id, **extra):
        return {'id':id,'channels':['art'],'country':'IN','city':'班加罗尔','language':'en','source_type':'official','venue':'MAP','timezone':'Asia/Kolkata','feed_url':'https://example.invalid/exhibitions','adapter':'map_exhibitions',**extra}

    def test_map_rejects_online_installation_and_incomplete_dates(self):
        def card(name,category,dates):
            return f'<article class="rds-card"><a href="/exhibition/{name}"></a><h5 class="rds-card__category-location">{category}</h5><h3 class="rds-card__title">{name}</h3><p class="rds-card__date">{dates}</p></article>'
        html=card('physical','Exhibitions | MAP Bengaluru','Aug 15, 2026 - Nov 1, 2026')+card('virtual','Online Exhibitions','Aug 15, 2026 - Nov 1, 2026')+card('until','Installations | MAP Bengaluru','Ongoing until November 22, 2026')+card('no-year','Exhibitions | MAP Bengaluru','Aug 15 - Nov 1')+'<footer>Jan 1, 2020 - Dec 31, 2028</footer>'
        records,events,links=map_records(self.source('map'),html)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['timezone'],'Asia/Kolkata')
        self.assertEqual(events[0]['start_date'],'2026-08-15')
        self.assertIsNone(events[0]['price_text'])
        self.assertEqual(records[0]['geography_status'],'confirmed')
        self.assertEqual(len(links),1)
        _, with_policy, _ = map_records(self.source('map'), html + '<div class="footer__top__info">Monday · Closed Free entry to all exhibitions on Tuesdays</div>')
        self.assertIn('周二', with_policy[0]['price_text'])
        self.assertIn('周一闭馆', with_policy[0]['closure_note'])

    def test_zeitz_season_workshop_and_current_badge_are_not_exhibition_evidence(self):
        def card(name,kind):
            return f'<article class="zeitz-card"><a href="/exhibition/{name}"></a><p class="zeitz-card__subtitle">{kind}</p><h3 class="zeitz-card__title">{name}</h3><span>Current</span><div class="zeitz-card__date">20 Nov 2025 – 11 Oct 2026</div></article>'
        src=self.source('zeitz',country='ZA',city='开普敦',timezone='Africa/Johannesburg',venue='Zeitz MOCAA',adapter='zeitz_exhibitions')
        records,events,_=zeitz_records(src,card('Solo Exhibition','EXHIBITIONS')+card('Announces Exhibition Season','EXHIBITIONS')+card('Workshop','WORKSHOPS')+card('Film','FILM'))
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['end_date'],'2026-10-11')
        self.assertEqual(events[0]['country'],'ZA')

    def test_multilingual_gear_and_television_filters_preserve_photobooks_and_films(self):
        src=self.source('media',source_type='media',adapter='rss',exclude_title_regex=r'\bsérie\b|\btemporada\b')
        titles=[('Test appareil photo: nouvel objectif',''),('Teste de câmera',''),('Prueba de cámara',''),('Uma série em nova temporada',''),('Blindfolded','Livre photo'),('Entretien avec un artiste','Interviews'),('Crítica de filme','')]
        xml='<rss><channel>'+''.join(f'<item><title>{title}</title><category>{category}</category><link>https://example.invalid/{index}</link></item>' for index,(title,category) in enumerate(titles))+'</channel></rss>'
        records,_,_=rss_records(src,xml.encode())
        self.assertEqual([r['kind'] for r in records],['photobook','interview','news'])

    def test_audit_distinguishes_archival_metadata_from_integrity_errors(self):
        row={'id':'a','source_id':'source','canonical_url':'https://example.invalid/a','title_original':'Archival art','published_at':'2021-01-01T00:00:00+00:00','language':'fr','channel':'art','geography_status':'unknown','locations_json':'[]','is_demo':0}
        data={'content':[row],'events':[],'content_events':[]};catalog={'sources':[{'id':'source','enabled':True}]}
        report=audit_payload(data,catalog,'2026-10-13')
        self.assertFalse(report['errors']);self.assertEqual(report['counts']['old_publications_over_30_days'],1)
        data['content'].append(dict(row,id='b'))
        data['content_events'].append({'content_id':'a','event_id':'missing'})
        codes=[e['code'] for e in audit_payload(data,catalog,'2026-10-13')['errors']]
        self.assertIn('duplicate_url',codes);self.assertIn('broken_content_event_link',codes)

    def test_snapshot_restores_source_history_without_inventing_a_new_fetch(self):
        with TemporaryDirectory() as temp:
            path=Path(temp)/'snapshot.json'
            success='2026-10-13T09:00:00+00:00'
            failed={'started_at':'2026-10-13T10:00:00+00:00','finished_at':'2026-10-13T10:01:00+00:00','status':'failed','fetched_count':0,'inserted_count':0,'error':'HTTPError HTTP 403'}
            path.write_text(json.dumps({'content':[],'events':[],'content_events':[],'source_status':[{'id':'asianmoviepulse','last_success_at':success,'last_run':failed}]}))
            store=Store(Path(temp)/'history.db')
            store.restore_public_snapshot(path);store.restore_public_snapshot(path)
            status=next(x for x in store.source_status() if x['id']=='asianmoviepulse')
            self.assertEqual(status['last_success_at'],success)
            self.assertEqual(status['last_run']['status'],'failed')
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM ingest_runs').fetchone()[0],0)
            # Loading an older snapshot must not erase the newer failure.
            path.write_text(json.dumps({'content':[],'events':[],'content_events':[],'source_status':[{'id':'asianmoviepulse','last_success_at':success,'last_run':{**failed,'started_at':success,'status':'success'}}]}))
            store.restore_public_snapshot(path)
            status=next(x for x in store.source_status() if x['id']=='asianmoviepulse')
            self.assertEqual(status['last_run']['status'],'failed')
