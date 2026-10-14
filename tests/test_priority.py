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
