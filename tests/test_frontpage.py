import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from backend.frontpage import frontpage_rows, headline_slots
from backend.priority import classify, rank_snapshot, reference_time, translation_batch
from backend.ai_translation import selected_rows
from backend.presentation import browser_snapshot
from backend.headlines import load_headlines

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = '2026-10-15T12:00:00+00:00'


class FrontpagePriorityTests(unittest.TestCase):
    def fixture(self):
        rows = []
        for i in range(24):
            rows.append({'id': 'story-' + str(i), 'source_id': 'publisher-' + str(i % 5),
                         'channel': ['film', 'art', 'photography'][i % 3], 'language': 'en',
                         'kind': 'news', 'title_original': ('Cannes Film Festival Award Winners' if i == 4 else 'A cultural story ' + str(i)),
                         'evidence_status': 'media_reported', 'published_at': '2026-10-15T' + f'{i % 12:02}:00:00Z'})
        rows[0].update(kind='industry_buzz')
        rows[1].update(evidence_status='unverified', title_original='Unverified Cannes awards')
        rows[2].update(editorial_status='translated', editorial_title_zh='当代艺术与摄影集', editorial_blocks_json='[{"type":"paragraph","text":"已译"}]')
        rows[3].update(published_at=None)
        rows[6].update(published_at='2020-01-01')
        rows[7].update(title_original='A painting exhibition', country='GB')
        rows[8].update(title_original='摄影集', language='zh')
        return {'content': rows, 'events': [], 'content_events': []}

    @unittest.skipUnless(shutil.which('node'), 'Node is only needed for browser/backend parity testing')
    def test_public_frontpage_matches_browser_for_fixture_and_current_archive(self):
        preferences = json.loads((ROOT / 'config/preferences.json').read_text())
        snapshots = [self.fixture(), json.loads((ROOT / 'data/live.json').read_text())]
        node = r"""
const fs=require('node:fs'), input=JSON.parse(fs.readFileSync(0,'utf8'));
const RealDate=Date;
global.Date=class extends RealDate {constructor(...args){super(...(args.length?args:[input.reference]));}static now(){return new RealDate(input.reference).getTime();}};
global.CULTURE_BOOTSTRAP={priorities:input.priorities,headlines:input.headlines};
const C=require('./frontend/core.js');
const context={...input.snapshot,reference_date:C.localDate(input.preferences.reading_timezone)};
console.log(JSON.stringify(C.frontpageRows(input.snapshot.content,input.preferences,context).map(r=>r.id)));
"""
        for snapshot in snapshots:
            priorities = rank_snapshot(snapshot, REFERENCE)
            headlines = load_headlines(snapshot)
            for prefs in [preferences, {**preferences, 'interests': ['摄影'], 'industry_buzz': {'enabled': False, 'max_share': 0.1}}]:
                expected = [r['id'] for r in frontpage_rows(snapshot, priorities, reference_time(REFERENCE), prefs, headlines)]
                output = subprocess.check_output(['node', '-e', node], input=json.dumps({'snapshot': browser_snapshot(snapshot), 'priorities': priorities, 'headlines': headlines, 'preferences': prefs, 'reference': REFERENCE}).encode(), cwd=ROOT)
                self.assertEqual(json.loads(output), expected)

    def test_headlines_stay_before_old_share_and_preserve_all_unique_slots(self):
        rows = [{'id': 'head-' + str(i), 'translation_priority': {'priority': 'P2', 'headline_order': i}, 'published_at': '2026-10-15'} for i in range(4)]
        rows += [{'id': 'urgent-' + str(i), 'translation_priority': {'priority': 'P0'}, 'published_at': '2026-10-15'} for i in range(20)]
        rows += [{'id': 'old-' + str(i), 'translation_priority': {'priority': 'P3'}, 'published_at': '2020-01-01'} for i in range(12)]
        for limit in (2, 4, 8, 20):
            selected, backlog = translation_batch(rows, limit)
            self.assertEqual([r['id'] for r in selected[:min(4, limit)]], ['head-' + str(i) for i in range(min(4, limit))])
            self.assertEqual(len(selected), limit)
            self.assertEqual(len({r['id'] for r in selected}), limit)
            if limit >= 8:
                self.assertTrue(backlog)
                self.assertTrue(all(next(i for i, r in enumerate(selected) if r['id'] == old) >= 4 for old in backlog))
        self.assertEqual(translation_batch([], 0), ([], []))

    def test_all_frontpage_headlines_receive_metadata_and_ai_uses_it(self):
        snapshot = self.fixture()
        ranks = rank_snapshot(snapshot, REFERENCE)
        slots = headline_slots(snapshot, ranks, reference_time(REFERENCE))
        for index, (identifier, slot) in enumerate(slots):
            self.assertEqual(ranks[identifier]['headline_order'], index)
            self.assertEqual(ranks[identifier]['headline_slot'], slot)
        # AI operates on foreign pending originals, leaving completed/native Chinese out.
        rows = [copy.deepcopy(r) for r in snapshot['content'] if r['language'] != 'zh' and r.get('editorial_status') != 'translated']
        for row in rows:
            row['translation_priority'] = ranks[row['id']]
        expected = [r['id'] for r in translation_batch(rows, 12)[0]]
        # Freeze rank_snapshot's reference for this worker-only check.
        from unittest.mock import patch
        with patch('backend.ai_translation.rank_snapshot', return_value=ranks):
            actual = selected_rows(rows, snapshot, 12)
        self.assertEqual([r['id'] for r in actual], expected)
        self.assertNotIn('story-1', [identifier for identifier, _ in slots])
