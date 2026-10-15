import json
import unittest
import asyncio
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import httpx
from backend.app import create_app
from backend.editorial_regions import (policy, country_tier, source_tier, media_weight,
                                      international_gateway, ordered_sources,
                                      body_batch, regional_coverage, _regional_pick)
from backend.ingestion import content_record


class EditorialRegionTests(unittest.TestCase):
    def source(self, identifier, country, area, role='discovery', international=40, local=80, discovery=80):
        return {'id': identifier, 'name': identifier, 'channels': ['art'], 'adapter': 'rss',
                'enabled': True, 'publisher_country': 'XX', 'country': None,
                'editorial_focus': {'countries': [country], 'regions': [area], 'role': role,
                                    'media_weight': {'international': international, 'local_specialist': local, 'discovery': discovery}}}

    def rows(self, source, count=30, **rank):
        return [{'id': source['id'] + '-' + str(i), 'source_id': source['id'], 'channel': 'art',
                 'published_at': '2026-10-15', 'translation_priority': {'priority': 'P2', **rank}}
                for i in range(count)]

    def test_field_specific_tiers_and_every_unlisted_country_remain_eligible(self):
        self.assertEqual(country_tier('JP', 'art'), 1)
        self.assertEqual(country_tier('IR', 'film'), 1)
        self.assertEqual(country_tier('IR', 'art'), 2)
        self.assertEqual(country_tier('not-listed', 'photography'), 3)
        rules = policy()
        codes = [code for area in rules['world_regions'] for code in area['countries']]
        self.assertEqual(len(codes), len(set(codes)))
        for field in rules['channels'].values():
            self.assertFalse(set(field['tier_1']) & set(field['tier_2']))

    def test_media_strength_and_artist_region_attention_are_independent(self):
        local = self.source('small-japanese', 'JP', 'east_asia', international=10, local=95)
        world = self.source('worldwide-editor', 'not-listed', 'global', international=99, local=30)
        self.assertEqual(source_tier(local), 1)
        self.assertEqual(source_tier(world), 3)
        self.assertTrue(international_gateway(world, policy()))
        self.assertGreater(media_weight(world, 'global'), media_weight(local, 'global'))
        self.assertGreater(media_weight(local), media_weight(world))
        self.assertEqual([s['id'] for s in ordered_sources([world, local])], ['small-japanese', 'worldwide-editor'])
        selected = body_batch(self.rows(local) + self.rows(world), [], {s['id']: s for s in (local, world)}, 20)
        self.assertTrue(any(r['source_id'] == 'worldwide-editor' for r in selected))
        self.assertTrue(any(r['source_id'] == 'small-japanese' for r in selected))

    def test_headlines_and_major_news_precede_geography_and_preserve_rechecks(self):
        core = self.source('core', 'JP', 'east_asia', 'core')
        remote = self.source('remote', 'not-listed', 'sub_saharan_africa')
        rows = self.rows(core)
        heads = self.rows(remote, 4)
        for i, row in enumerate(heads):
            row['translation_priority']['headline_order'] = i
        major = {**self.rows(remote, 1, priority='P0', importance='high')[0], 'id': 'important-remote'}
        old = [{'id': 'cached-' + str(i), 'source_id': 'core'} for i in range(10)]
        catalog = {s['id']: s for s in (core, remote)}
        self.assertEqual([r['id'] for r in body_batch(rows + heads, old, catalog, 4)], [r['id'] for r in heads])
        selected = body_batch(rows + heads + [major], old, catalog, 20)
        self.assertEqual([r['id'] for r in selected[:5]], [r['id'] for r in heads] + ['important-remote'])
        self.assertEqual(len(selected), 20)
        self.assertEqual(len({r['id'] for r in selected}), 20)
        self.assertEqual(sum(r['id'].startswith('cached-') for r in selected), 5)

    def test_discovery_floor_global_gateway_and_local_source_rotation(self):
        core = self.source('global-core', 'US', 'north_america', 'global_core', 99)
        africa = self.source('africa', 'ZA', 'sub_saharan_africa', discovery=95)
        latin = self.source('latin', 'CL', 'latin_america_caribbean', discovery=94)
        japan = self.source('japan', 'JP', 'east_asia', 'core', local=95)
        sources = [core, africa, latin, japan]
        selected = body_batch(sum((self.rows(s, 50) for s in sources), []), [], {s['id']: s for s in sources}, 40)
        counts = Counter(r['source_id'] for r in selected)
        self.assertGreaterEqual(counts['africa'] + counts['latin'], 6)
        self.assertGreaterEqual(counts['global-core'], 9)
        self.assertTrue(all(counts[s['id']] for s in sources))
        self.assertEqual(len(selected), 40)

    def test_media_weight_changes_share_inside_same_region_without_excluding_small_source(self):
        strong = self.source('strong', 'JP', 'east_asia', local=95)
        small = self.source('small', 'JP', 'east_asia', local=20)
        sources = {s['id']: s for s in (strong, small)}
        selected = _regional_pick(self.rows(small, 100) + self.rows(strong, 100), 100, sources, policy())
        counts = Counter(r['source_id'] for r in selected)
        self.assertGreater(counts['strong'], counts['small'] * 3)
        self.assertGreater(counts['small'], 0)

    def test_report_separates_source_focus_from_actual_geography_and_exposes_missing_desks(self):
        source = self.source('south-africa', 'ZA', 'sub_saharan_africa')
        source.update(language='en', source_type='media', homepage_url='https://example.org')
        row = content_record(source, 'New artist project', 'https://example.org/project')
        self.assertIsNone(row['country'])
        report = regional_coverage({'content': [row]}, {'sources': [source]})
        self.assertEqual(report['unlocated_content'], 1)
        self.assertEqual(report['global_completeness'], 'unknown')
        self.assertTrue(report['source_focus_is_editorial_assignment_not_reported_geography'])
        self.assertIn({'country': 'JP', 'channel': 'art', 'reason': 'no_country_specific_source_assignment'}, report['priority_country_gaps'])
        east = next(r for r in report['matrix'] if r['id'] == 'east_asia')
        self.assertEqual(east['channels']['art']['coverage_status'], 'no_dedicated_source')

    def test_every_enabled_source_has_valid_independent_weights_and_region_assignment(self):
        root = Path(__file__).resolve().parents[1]
        sources = json.loads((root / 'config/sources.json').read_text())['sources']
        rules = policy()
        regions = {r['id'] for r in rules['world_regions']}
        for source in sources:
            if not source['enabled']:
                continue
            focus = source['editorial_focus']
            self.assertTrue(focus['regions'])
            self.assertTrue(set(focus['regions']) <= regions)
            for field in ('international', 'local_specialist', 'discovery'):
                self.assertTrue(0 <= focus['media_weight'][field] <= 100)
        self.assertEqual(body_batch([], [], {}, 0), [])

    def test_regional_report_api_matches_public_json_contract(self):
        with TemporaryDirectory() as tmp:
            app = create_app(Path(tmp) / 'test.db')
            async def check():
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
                    first = await client.get('/api/editorial-regions')
                    second = await client.get('/reports/regional-coverage.json')
                    self.assertEqual(first.status_code, 200)
                    self.assertEqual(first.json(), second.json())
                    self.assertEqual(first.json()['global_completeness'], 'unknown')
                    self.assertTrue(first.json()['international_gateway_source_ids'])
            asyncio.run(check())
