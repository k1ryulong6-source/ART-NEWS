import unittest
from backend.priority import classify, rank_snapshot, priority_key


class PriorityTests(unittest.TestCase):
    def test_major_fresh_news_precedes_archive_without_invented_dates(self):
        now='2026-10-14T12:00:00+00:00'
        story={'id':'award','title_original':'Vancouver Film Festival Award Winners','published_at':'2026-10-14T10:00:00+00:00'}
        self.assertEqual(classify(story,reference=now)['priority'],'P0')
        self.assertEqual(classify({**story,'published_at':'2023-01-01'},reference=now)['priority'],'P3')
        unknown=classify({'id':'unknown','title_original':'Exhibition opens October 15'},reference=now)
        self.assertFalse(unknown['time_sensitive']);self.assertIsNone(unknown['due'])
        future=classify({**story,'published_at':'2027-01-01'},reference=now)
        self.assertFalse(future['fresh']);self.assertNotEqual(future['priority'],'P0')

    def test_local_day_and_passed_exact_deadline_control_time_sensitivity(self):
        row={'id':'call','title_original':'Student competition'}
        event={'id':'deadline','event_type':'call_deadline','date_precision':'day','start_date':'2026-10-14',
               'timezone':'Asia/Tokyo','deadline_at':'2026-10-14T02:00:00+09:00'}
        result=classify(row,[event],'2026-10-13T16:00:00+00:00')
        self.assertEqual(result['priority'],'P0');self.assertEqual(result['due']['days'],0)
        expired=classify(row,[event],'2026-10-13T17:01:00+00:00')
        self.assertFalse(expired['time_sensitive'])
        approximate=classify(row,[{**event,'date_precision':'month'}],'2026-10-13T16:00:00+00:00')
        self.assertFalse(approximate['time_sensitive'])

    def test_snapshot_only_uses_explicitly_linked_dates_and_high_importance_wins_ties(self):
        rows=[{'id':'important','title_original':'Museum merger announced','published_at':'2026-10-14T10:00:00Z'},
              {'id':'film','title_original':'A film'}]
        snapshot={'content':rows,'events':[{'id':'screen','event_type':'festival_screening','date_precision':'day',
                                           'start_date':'2026-10-14','timezone':'Europe/London'}],
                  'content_events':[{'content_id':'film','event_id':'screen'}]}
        ranks=rank_snapshot(snapshot,'2026-10-14T12:00:00Z')
        self.assertFalse(ranks['important']['time_sensitive']);self.assertTrue(ranks['film']['time_sensitive'])
        ordered=sorted([{**r,'translation_priority':ranks[r['id']]}for r in rows],key=priority_key)
        self.assertEqual(ordered[0]['id'],'important')

    def test_foreign_ordinary_exhibit_is_lower_even_on_closing_day_but_dates_are_kept(self):
        row={'id':'outside','channel':'art','title_original':'A painting exhibition','country':'GB','language':'ja','published_at':'2026-10-14T09:00:00Z'}
        event={'id':'exhibit','event_type':'exhibition','country':'GB','date_precision':'day','start_date':'2026-09-01','end_date':'2026-10-14','timezone':'Europe/London'}
        result=classify(row,[event],'2026-10-14T12:00:00Z')
        self.assertEqual(result['priority'],'P3');self.assertTrue(result['time_sensitive'])
        self.assertEqual(result['due']['label'],'闭展');self.assertTrue(result['exhibition_deprioritized'])
        self.assertGreater(result['recommendation_penalty'],0)
        japanese=classify({**row,'country':'US'},[{**event,'country':'JP','timezone':'Asia/Tokyo'}],'2026-10-14T12:00:00Z')
        self.assertEqual(japanese['priority'],'P0');self.assertFalse(japanese['exhibition_deprioritized'])
        mixed=classify(row,[event,{**event,'id':'japan','country':'JP','timezone':'Asia/Tokyo'}],'2026-10-14T12:00:00Z')
        self.assertFalse(mixed['exhibition_deprioritized'])

    def test_major_foreign_exhibitions_and_editor_overrides_keep_priority(self):
        from backend.priority import policy
        row={'id':'major','channel':'art','title_original':'Venice Biennale exhibition opens','country':'IT','published_at':'2026-10-14T09:00:00Z'}
        result=classify(row,reference='2026-10-14T12:00:00Z')
        self.assertEqual(result['priority'],'P0');self.assertFalse(result['exhibition_deprioritized'])
        retrospective=classify({**row,'title_original':'A career-spanning retrospective opens'},reference='2026-10-14T12:00:00Z')
        self.assertEqual(retrospective['importance'],'high');self.assertFalse(retrospective['exhibition_deprioritized'])
        ordinary={**row,'title_original':'A painting exhibition'};rules=policy();rules['manual_overrides']={'major':{'importance':'high','reason':'重大展览，编辑指定'}}
        marked=classify(ordinary,reference='2026-10-14T12:00:00Z',rules=rules)
        self.assertEqual(marked['priority'],'P0');self.assertFalse(marked['exhibition_deprioritized'])
        rules['manual_overrides']['major']={'priority':'P1','reason':'手动优先'}
        self.assertEqual(classify(ordinary,reference='2026-10-14T12:00:00Z',rules=rules)['priority'],'P1')

    def test_unknown_exhibition_venue_is_not_guessed_from_language_and_films_are_unaffected(self):
        row={'id':'unknown','channel':'photography','title_original':'A new exhibition','language':'ja','source_id':'ima'}
        result=classify(row,reference='2026-10-14T12:00:00Z')
        self.assertEqual(result['exhibition_region'],'unknown');self.assertFalse(result['exhibition_deprioritized'])
        self.assertEqual(result['priority'],'P2')
        film=classify({**row,'channel':'film','title_original':'Film retrospective screening','country':'US'},reference='2026-10-14T12:00:00Z')
        self.assertFalse(film['exhibition_deprioritized']);self.assertEqual(film['priority'],'P2')
