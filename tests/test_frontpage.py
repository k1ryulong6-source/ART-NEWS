import copy
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from backend.frontpage import frontpage_rows, headline_slots, headline_ready
from backend.priority import classify, rank_snapshot, reference_time, translation_batch
from backend.ai_translation import selected_rows
from backend.presentation import browser_snapshot
from backend.headlines import load_headlines

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = '2026-10-15T12:00:00+00:00'


class FrontpagePriorityTests(unittest.TestCase):
    def story(self, id, published, title='A cultural report', channel='film', **extra):
        original = json.dumps([{'type': 'paragraph', 'text': 'Public article 2026.'}])
        return {'id': id, 'source_id': id, 'channel': channel, 'language': 'en',
                'kind': 'news', 'title_original': title, 'published_at': published,
                'evidence_status': 'media_reported', 'article_blocks_json': original,
                'article_hash': hashlib.sha256(original.encode()).hexdigest(),
                'editorial_status': 'translated', 'editorial_title_zh': '译文：' + title,
                'editorial_blocks_json': json.dumps([{'type': 'paragraph', 'text': '公开正文2026。'}]), **extra}

    def pick(self, rows):
        snapshot = {'content': rows, 'events': [], 'content_events': []}
        ranks = rank_snapshot(snapshot, REFERENCE)
        return frontpage_rows(snapshot, ranks, reference_time(REFERENCE))

    def test_new_major_story_is_not_excluded_by_interest_candidate_limit(self):
        interests = [self.story('photo-' + str(i), '2026-10-15T11:00:00Z', 'A new photobook ' + str(i), 'photography') for i in range(20)]
        major = self.story('major', '2026-10-15T10:00:00Z', 'A major museum declares bankruptcy', 'art')
        self.assertEqual(self.pick(interests + [major])[0]['id'], 'major')

    def test_week_old_award_and_old_column_fallback_cannot_displace_new_reports(self):
        old = self.story('old-award', '2026-10-08T11:00:00Z', 'PhotoBook Awards shortlist', 'photography')
        archive = self.story('archive', '2026-09-24T00:00:00Z', 'A photobook exhibition', 'photography')
        recent = self.story('recent', '2026-10-15T09:00:00Z', channel='photography')
        rows = self.pick([old, archive, recent])
        self.assertEqual([r['id'] for r in rows], ['recent'])

    def test_importance_decays_and_age_expiry_is_deterministic_without_random_rotation(self):
        aged = self.story('aged-major', '2026-10-12T13:00:00Z', 'PhotoBook Awards shortlist')
        fresh = self.story('fresh', '2026-10-15T11:00:00Z')
        self.assertEqual(self.pick([aged, fresh])[0]['id'], 'fresh')
        self.assertEqual(self.pick([fresh, aged])[0]['id'], 'fresh')
        fallback = self.story('fallback', '2026-10-11T12:00:00Z')
        self.assertEqual(self.pick([fallback])[0]['id'], 'fallback')
        self.assertEqual(self.pick([self.story('expired', '2026-10-08T11:59:59Z')]), [])

    def test_fetch_date_unknown_publication_and_far_future_do_not_count_as_fresh_news(self):
        unknown = self.story('unknown', None, fetched_at=REFERENCE, updated_at=REFERENCE)
        invalid = self.story('invalid', 'unknown', fetched_at=REFERENCE)
        future = self.story('future', '2026-10-16T12:00:00Z')
        self.assertEqual(self.pick([unknown, invalid, future]), [])

    def test_undated_event_is_only_fallback_and_never_uses_fetch_age(self):
        unknown = self.story('unknown', None, fetched_at=REFERENCE)
        dated = self.story('dated', '2026-10-15T10:00:00Z')
        ranks = {'unknown': {'source_title': unknown['title_original'], 'priority': 'P0', 'importance': 'high', 'due': {'days': 1}},
                 'dated': {'source_title': dated['title_original'], 'priority': 'P2', 'importance': 'normal'}}
        snapshot = {'content': [unknown, dated], 'events': [], 'content_events': []}
        rows = frontpage_rows(snapshot, ranks, reference_time(REFERENCE), headlines={})
        self.assertEqual([r['id'] for r in rows], ['dated'])
        snapshot['content'] = [unknown]
        fallback = frontpage_rows(snapshot, ranks, reference_time(REFERENCE), headlines={})[0]
        self.assertIsNone(fallback['frontpage_age_hours'])
        self.assertEqual(fallback['frontpage_basis'], 'confirmed_upcoming_event')

    def fixture(self):
        rows = []
        for i in range(24):
            rows.append(self.story('story-' + str(i), '2026-10-15T' + f'{i % 12:02}:00:00Z',
                         'Cannes Film Festival Award Winners' if i == 4 else 'A cultural story ' + str(i),
                         ['film', 'art', 'photography'][i % 3], source_id='publisher-' + str(i % 5)))
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
        edge = {'content': [self.story('offset', '2026-10-15T03:00:00-09:00'),
                            self.story('same-time', '2026-10-15T12:00:00Z'),
                            self.story('future', '2026-10-16T12:00:00Z'),
                            self.story('old', '2026-10-08T11:59:59Z'),
                            self.story('unknown', None), self.story('invalid', 'unknown')],
                'events': [], 'content_events': []}
        snapshots = [self.fixture(), edge, json.loads((ROOT / 'data/live.json').read_text())]
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
        slots = headline_slots(snapshot, ranks, reference_time(REFERENCE), candidates=True)
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

    def test_pending_headline_candidate_is_first_to_translate_but_cannot_display_until_AI_ready(self):
        pending = self.story('pending', '2026-10-15T11:00:00Z', 'Cannes Film Festival Award Winners',
                             editorial_status=None, editorial_blocks_json=None, editorial_title_zh=None)
        ready = self.story('ready', '2026-10-15T10:00:00Z', 'A current cultural report')
        snapshot = {'content': [pending, ready], 'events': [], 'content_events': []}
        ranks = rank_snapshot(snapshot, REFERENCE)
        self.assertEqual(self.pick(snapshot['content'])[0]['id'], 'ready')
        self.assertEqual(ranks['pending']['headline_order'], 0)
        self.assertEqual(ranks['ready']['frontpage_headline_order'], 0)
        picked = selected_rows([pending], snapshot, 10)
        self.assertEqual(picked[0]['id'], 'pending')
        pending.update(editorial_status='translated', editorial_title_zh='戛纳电影节获奖名单',
                       editorial_blocks_json=json.dumps([{'type': 'paragraph', 'text': '公开正文2026。'}]))
        self.assertEqual(self.pick(snapshot['content'])[0]['id'], 'pending')

    def test_each_desk_starts_with_AI_body_and_keeps_untranslated_briefs_below(self):
        lead = self.story('lead', '2026-10-15T11:00:00Z', 'A museum declares bankruptcy', 'art')
        translated = self.story('film-ready', '2026-10-15T10:00:00Z', 'A film interview')
        pending = self.story('film-pending', '2026-10-15T11:00:00Z', 'A new film opening',
                             editorial_status=None, editorial_blocks_json=None)
        photo = self.story('photo-pending', '2026-10-15T11:00:00Z', 'A new photobook', 'photography',
                           editorial_status=None, editorial_blocks_json=None)
        picked = self.pick([lead, pending, translated, photo])
        self.assertEqual(picked[0]['id'], 'lead')
        self.assertEqual([r['id'] for r in picked if r['channel'] == 'film'], ['film-ready', 'film-pending'])
        self.assertNotIn('photo-pending', [r['id'] for r in picked])
        self.assertEqual(len([lead, pending, translated, photo]), 4)

    def test_title_only_machine_incomplete_or_numeric_failure_is_not_AI_headline(self):
        valid = self.story('story', '2026-10-15T11:00:00Z')
        self.assertTrue(headline_ready(valid))
        variants = [
            {**valid, 'editorial_status': None, 'translated_title_zh': '只有标题'},
            {**valid, 'editorial_status': None, 'article_translation_provider': 'offline-m2m100:test',
             'article_translation_json': valid['editorial_blocks_json'], 'translation_status': 'machine'},
            {**valid, 'editorial_blocks_json': '[]'},
            {**valid, 'editorial_blocks_json': '[{"type":"paragraph","text":"丢失原文年份"}]'},
            {**valid, 'article_hash': 'stale-source-version'},
            {**valid, 'article_blocks_json': None},
        ]
        for row in variants:
            self.assertFalse(headline_ready(row))
            self.assertEqual(self.pick([row]), [])
        self.assertTrue(headline_ready({**valid, 'editorial_status': 'reviewed'}))

    def test_native_chinese_requires_body_but_does_not_need_retranslation(self):
        row = self.story('chinese', '2026-10-15T11:00:00Z', '艺术报道', language='zh',
                         editorial_status=None, editorial_blocks_json=None)
        self.assertTrue(headline_ready(row))
        self.assertEqual(self.pick([row])[0]['id'], 'chinese')
        self.assertFalse(headline_ready({**row, 'article_blocks_json': None}))
