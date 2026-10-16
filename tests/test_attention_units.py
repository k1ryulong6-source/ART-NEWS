import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import httpx
from backend.app import create_app
from backend.attention_units import attention_report, reserved_units, configuration
from backend.editorial_regions import body_batch


class AttentionUnitTests(unittest.TestCase):
    def source(self, identifier, role='discovery', enabled=True):
        return {'id': identifier, 'name': identifier, 'enabled': enabled, 'adapter': 'rss',
                'language': 'en', 'channels': ['art'], 'publisher_country': 'XX',
                'editorial_focus': {'role': role, 'countries': ['CL'], 'regions': ['latin_america_caribbean'],
                                    'media_weight': {'international': 99 if role == 'global_core' else 40,
                                                     'local_specialist': 90, 'discovery': 95}}}

    def rows(self, source, n=60, **rank):
        return [{'id': source['id'] + '-' + str(i), 'source_id': source['id'], 'channel': 'art',
                 'translation_priority': {'priority': 'P2', **rank}, 'published_at': '2026-10-15'} for i in range(n)]

    def test_unit_has_protected_slots_without_growing_discovery_or_total_budget(self):
        unit = self.source('artishock')
        other = self.source('other-discovery')
        world = self.source('world', 'global_core')
        sources = [unit, other, world]
        fresh = sum((self.rows(s) for s in sources), [])
        old = [{'id': 'old-' + str(i), 'source_id': 'world'} for i in range(10)]
        selected = body_batch(fresh, old, {s['id']: s for s in sources}, 50)
        self.assertEqual(len(selected), 50)
        self.assertEqual(len({r['id'] for r in selected}), 50)
        self.assertGreaterEqual(sum(r['source_id'] == 'artishock' for r in selected), 4)
        self.assertTrue(any(r['source_id'] == 'other-discovery' for r in selected))
        self.assertGreaterEqual(sum(r['source_id'] == 'world' for r in selected), 12)
        self.assertEqual(sum(r['id'].startswith('old-') for r in selected), 10)
        # The reserved unit contributes to the shared discovery budget, not an added quota.
        first = selected[:8]
        self.assertEqual(sum(r['source_id'] == 'artishock' for r in first[:4]), 4)
        self.assertEqual(sum(r['source_id'] == 'other-discovery' for r in first[4:]), 4)

    def test_headlines_and_major_news_are_never_displaced_by_unit(self):
        unit, world = self.source('artishock'), self.source('world', 'global_core')
        catalog = {s['id']: s for s in (unit, world)}
        heads = self.rows(world, 4)
        for i, row in enumerate(heads):
            row['translation_priority']['headline_order'] = i
        self.assertEqual(body_batch(self.rows(unit) + heads, [], catalog, 4), heads)
        important = self.rows(world, 20, priority='P0', importance='high')
        selected = body_batch(self.rows(unit) + important, [], catalog, 20)
        self.assertEqual([r['source_id'] for r in selected[:15]], ['world'] * 15)

    def test_empty_unit_slots_return_to_other_sources_and_disabled_members_are_ineligible(self):
        world = self.source('world', 'global_core')
        unit = self.source('artishock', enabled=False)
        catalog = {s['id']: s for s in (world, unit)}
        self.assertEqual(reserved_units(catalog), [])
        selected = body_batch(self.rows(world), [], catalog, 20)
        self.assertEqual(len(selected), 20)
        self.assertTrue(all(r['source_id'] == 'world' for r in selected))

    def test_report_retains_failed_source_cached_articles_and_distinguishes_publication_from_fetch(self):
        unit = {'id': 'a-kind-of-attention', 'name': '一种关注', 'enabled': True,
                'body_share_of_new_slots': .1, 'members': [{'source_id': 'artishock', 'why': '地区报道', 'focus_label': '智利与拉美'}]}
        source = self.source('artishock')
        source.update(homepage_url='https://example.org', feed_url='https://example.org/feed')
        row = {'id': 'article', 'source_id': 'artishock', 'title_original': 'Artist project', 'language': 'en',
               'published_at': '2026-08-01T00:00:00Z', 'article_blocks_json': '[{"type":"paragraph","text":"Original"}]',
               'editorial_status': 'translated', 'editorial_blocks_json': None, 'editorial_title_zh': None}
        snapshot = {'content': [row], 'source_status': [{'id': 'artishock', 'last_run': {'status': 'failed'},
                                                       'last_success_at': '2026-10-15T00:00:00Z'}]}
        report = attention_report(snapshot, {'sources': [source]}, units={'units': [unit]})['units'][0]
        member = report['members'][0]
        self.assertEqual(member['collection_status'], 'failed')
        self.assertEqual(member['article_count'], 1)
        self.assertEqual(member['with_body_count'], 1)
        self.assertEqual(member['ai_translated_count'], 0)
        self.assertEqual(member['latest_publication_at'], row['published_at'])
        self.assertEqual(member['last_successful_fetch_at'], '2026-10-15T00:00:00Z')
        self.assertIsNone(member['recent_items'][0]['reported_country'])
        self.assertEqual(member['recent_items'][0]['reader_path'], '#reader/article')

    def test_invalid_unit_export_path_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'config').mkdir()
            (root / 'config/attention-units.json').write_text(json.dumps({'units': [{'id': '../outside'}]}))
            with patch('backend.attention_units.ROOT', root), self.assertRaisesRegex(ValueError, 'invalid_attention_unit_id'):
                configuration()

    def test_public_json_and_api_expose_exact_name_and_unknown_unit_is_404(self):
        with TemporaryDirectory() as tmp:
            app = create_app(Path(tmp) / 'news.db')
            async def check():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    response = await client.get('/api/attention-units')
                    public = await client.get('/reports/attention-units.json')
                    self.assertEqual(response.json(), public.json())
                    direct = await client.get('/reports/attention-units/a-kind-of-attention.json')
                    self.assertEqual(direct.json(), response.json()['units'][0])
                    self.assertEqual(direct.json()['name'], '一种关注')
                    self.assertEqual(direct.json()['source_count'], 6)
                    self.assertEqual(direct.json()['article_count'], 0)
                    self.assertEqual((await client.get('/api/attention-units/missing')).status_code, 404)
            asyncio.run(check())
