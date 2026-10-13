import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.app import create_app, Preferences
from backend.ingestion import content_record, event_record, tate_records
from backend.geography import matches_region
from backend.storage import Store

SOURCE = dict(id='world-test', name='World', homepage_url='https://example.invalid', channels=['art'], country=None, publisher_country='US', language='en', source_type='media', adapter='rss', access_status='reviewed', access_method='rss', enabled=True, verified_at='2026-10-13')

class GlobalChecks(unittest.TestCase):
    def test_publisher_origin_does_not_locate_story(self):
        unknown = content_record(SOURCE, 'An artist interview', 'https://example.invalid/unknown')
        self.assertIsNone(unknown['country'])
        self.assertEqual(unknown['geography_status'], 'unknown')
        self.assertTrue(matches_region(unknown, 'unknown'))
        mentioned = content_record(SOURCE, 'Exhibition in Paris and Tokyo', 'https://example.invalid/mentions')
        self.assertIsNone(mentioned['country'])
        self.assertTrue(matches_region(mentioned, 'FR', '巴黎'))
        self.assertTrue(matches_region(mentioned, 'JP', '东京'))
        self.assertFalse(matches_region(mentioned, 'US'))
        self.assertEqual(mentioned['geography_status'], 'mentioned')
        self.assertFalse(matches_region(content_record(SOURCE, 'Comparison of artworks', 'https://example.invalid/word'), 'FR'))

    def test_tate_dates_are_scoped_to_card_and_member_price_not_assumed(self):
        source = {**SOURCE, 'source_type':'official', 'country':'GB', 'city':'伦敦', 'adapter':'tate_exhibitions', 'feed_url':'https://example.invalid/whats-on/tate-modern'}
        def card(slug, dates):
            return f'<a href="/whats-on/tate-modern/{slug}"><div class="card-tags">Exhibition</div><div class="event-info__venue">Tate Modern</div><h2 class="card__title">Art photography</h2><div class="event-info__date">{dates}</div><div class="event-info__price">FREE FOR MEMBERS</div></a>'
        payload = card('full', '14 Oct 2026 – 21 Feb 2027') + card('same-year', '25 Feb – 27 Jun 2027') + card('end-only', 'Until 3 Jan 2027') + card('ambiguous', '25 Dec – 27 Jan 2027') + '<a href="/magazine/articles/1">2 Oct 2026</a>'
        records, events, links = tate_records(source, payload)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]['start_date'], '2026-10-14')
        self.assertEqual(events[1]['start_date'], '2027-02-25')
        self.assertTrue(all(e['timezone']=='Europe/London' and e['country']=='GB' and e['price_text'] is None for e in events))
        self.assertEqual(records[0]['geography_status'],'confirmed')
        self.assertEqual(len(links),2)
        with self.assertRaises(ValueError): event_record(SOURCE, records[0], 'exhibition', '2026-10-14')

    def test_migration_preserves_preferences_bookmarks_and_summary(self):
        with TemporaryDirectory() as temp:
            store=Store(Path(temp)/'world.db')
            store.register_sources([SOURCE])
            article=content_record(SOURCE,'Paris show','https://example.invalid/a',summary='Cached Chinese summary')
            article.update(country='US', city=None, geography_status='unknown', locations_json='[]')
            store.ingest_records([article],[],[])
            bookmark=store.save_bookmark('content',article['id'])
            store.save_preferences({'default_city':'东京','reading_timezone':'Asia/Tokyo'})
            store.register_sources([SOURCE])
            reopened=Store(store.path)
            self.assertEqual(reopened.preferences()['news_scope'],'global')
            self.assertEqual(reopened.preferences()['default_city'],'东京')
            self.assertEqual(reopened.bookmarks()[0]['id'],bookmark['id'])
            corrected=reopened.dataset('live')['content'][0]
            self.assertEqual(corrected['country'],'FR')
            self.assertEqual(corrected['summary_zh'],'Cached Chinese summary')

    def test_api_region_and_language_and_world_timezone(self):
        with TemporaryDirectory() as temp:
            app=create_app(Path(temp)/'api.db'); store=app.state.store
            store.register_sources([SOURCE])
            story=content_record(SOURCE,'Paris and Tokyo galleries','https://example.invalid/world')
            store.ingest_records([story],[],[])
            route=next(r.endpoint for r in app.routes if r.path=='/api/content')
            self.assertEqual(len(asyncio.run(route(mode='live',country='FR',language='en'))),1)
            self.assertEqual(len(asyncio.run(route(mode='live',country='JP',language='es'))),0)
            self.assertEqual(Preferences(reading_timezone='America/New_York').safe_dict()['news_scope'],'global')
            with self.assertRaises(ValueError): Preferences(reading_timezone='invalid/timezone').safe_dict()
