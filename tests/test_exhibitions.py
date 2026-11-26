import json
import unittest
from datetime import datetime, timezone

from backend.exhibition_assets import compact_list, detail_view, public_items, venue_reference
from backend.exhibition_priority import add_recommendations
from backend.exhibition_details import parse_detail, pick_intro
from backend.exhibition_sources import date_range, museum_scan, observation, parse_official, tab_scan
from backend.exhibitions import config, merge_observations


class ExhibitionSourcesTests(unittest.TestCase):
    def test_art_navi_reader_retains_nested_and_line_break_prose_without_share_text(self):
        url = 'https://artexhibition.jp/exhibitions/20261125-AEJ1/'
        entry = {'source': 'artexhibition', 'url': url, 'title': '今日の展覧会'}
        html = '''<meta property="og:image" content="/share-logo.jpg"><main><article class="main-content">
        <header class="main-content-header"><h1 class="main-content-title">今日の展覧会</h1></header>
        <figure class="eyecatch"><img src="/exhibition.jpg"></figure>
        <p>展覧会の最初の段落です。<p>この段落が入れ子になっています。<br>最後の展示の説明です。</p></p>
        <div class="share"><p>Facebook に共有</p></div>
        <div class="official"><a href="https://venue.example.jp/exhibitions/1/">公式サイト</a></div></article></main>'''
        value = parse_detail(html, entry)
        self.assertEqual(value['status'], 'introduction')
        self.assertEqual(value['paragraphs'], ['展覧会の最初の段落です。', 'この段落が入れ子になっています。', '最後の展示の説明です。'])
        self.assertEqual(value['image'], 'https://artexhibition.jp/exhibition.jpg')
        self.assertEqual(value['official_url'], 'https://venue.example.jp/exhibitions/1/')
        with self.assertRaisesRegex(ValueError, 'detail_identity_changed'):
            parse_detail(html, {**entry, 'title': '別の展覧会'})
        with self.assertRaisesRegex(ValueError, 'exhibition_detail_not_public'):
            parse_detail('<script type="application/ld+json">{"isAccessibleForFree": false}</script>' + html, entry)

    def test_dates_keep_unpublished_year_and_ambiguous_rollover_unknown(self):
        self.assertEqual(date_range('2026年11月25日（水）〜12月13日（日）'), ('2026-11-25', '2026-12-13'))
        self.assertEqual(date_range('2026年12月12日[土]–27日[日]'), ('2026-12-12', '2026-12-27'))
        self.assertEqual(date_range('2026.12.12 – 2027.01.13'), ('2026-12-12', '2027-01-13'))
        self.assertEqual(date_range('2026年12月12日〜1月13日'), ('2026-12-12', None))
        self.assertEqual(date_range('2026年12月12日〜翌年1月13日'), ('2026-12-12', '2027-01-13'))
        self.assertEqual(date_range('2027年1月 詳細未発表'), (None, None))
        self.assertEqual(date_range('12月12日〜12月27日'), (None, None))

    def test_national_directory_recognizes_empty_count_but_rejects_repeated_page(self):
        settings = {**config(), 'prefectures': [['13', '東京都', '东京', '关东'], ['36', '徳島県', '德岛', '四国']]}
        source = settings['directories']['internet-museum']
        card = '<div class="c-eventItem"><div class="c-eventItem_museum"><a href="/event/123">水彩コレクション展</a></div><p class="c-eventItem_event">会場 | 東京都</p><p class="c-eventItem_duration">2026年11月25日〜12月13日</p></div>'

        def get(url):
            if 'pref-36' in url:
                return '<title>徳島県の展覧会</title><div class="c-listHeader_col_contentSearch">全 0件</div>'
            return '<title>東京都の展覧会</title><div class="c-listHeader_col_contentSearch">全 21件</div>' + card

        items, report = museum_scan(source, settings, get)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['types'], ['painting'])
        self.assertTrue(report['prefectures']['36']['complete'])
        self.assertFalse(report['prefectures']['13']['complete'])
        self.assertIn('duplicate_pagination', report['prefectures']['13']['errors'])

    def test_capped_tab_catalogue_is_partitioned_by_verified_public_area_routes(self):
        settings = {**config(), 'tab_area_index': {'h1': '北海道', 't1': '東京都'}}
        source = settings['directories']['tokyo-art-beat']

        def item(slug, name, area):
            return {'slug': slug, 'eventName': '装置展示 ' + slug, 'scheduleStartsOn': '2026-11-01',
                    'scheduleEndsOn': '2026-12-07', 'categories': [{'fields': {'name': 'インスタレーション'}}],
                    'venue': {'fields': {'fullName': name + '画廊', 'localArea': {'fields': {'name': name}, 'sys': {'id': area}}}}}

        north = item('north/a', '北海道', 'h1')
        tokyo = item('tokyo/b', '東京都', 't1')
        supplement = item('north/local', '北海道', 'h1')

        def get(url):
            area = url.split('/')[-1] if 'localAreaId/' in url else None
            props = {'excludeClosed': True}
            if area:
                props['localAreaId'] = area
            data, total = ([north, tokyo], 3) if not area else ([north, supplement], 2) if area == 'h1' else ([tokyo], 1)
            payload = {'props': {'pageProps': {'fallback': {json.dumps({'name': 'EventSearch', 'props': props}):
                       {'data': data, 'paginator': {'total': total}}}}}}
            return '<script id="__NEXT_DATA__">' + json.dumps(payload) + '</script>'

        items, report = tab_scan(source, settings, get, {})
        self.assertEqual(len(items), 3)
        self.assertTrue(report['complete'])
        self.assertEqual(report['pages'], 3)
        self.assertEqual(sum(row['prefecture'] == '01' for row in items), 2)
        self.assertTrue(all(row['types'] == ['installation'] for row in items))

    def test_venue_markup_uses_explicit_date_attributes_and_no_movie_links(self):
        calendar = next(c for c in config()['official_calendars'] if c['id'] == 'tokyo-photo-museum')
        html = """<table class="scheduleTable"><tr><td class="ex"><a class="detail_ref" href="/exhibition/5/">本展</a>
        <p class="date"><span data-date="2026-12-01"></span>～<span data-date="2027-01-17"></span></p></td>
        <td class="ex"><a class="detail_ref" href="/movie/7/">映画</a></td></tr></table>"""
        items, unread, excluded = parse_official(html, calendar)
        self.assertEqual((len(items), unread, excluded), (1, 0, 0))
        self.assertEqual((items[0]['start'], items[0]['end'], items[0]['prefecture']), ('2026-12-01', '2027-01-17', '13'))


class ExhibitionInventoryTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 11, 25, 3, tzinfo=timezone.utc)
        self.settings = config()

    def example(self, source='internet-museum', ending='2026-12-12', *, url=None, start='2026-11-01', venue='国立新美術館', official=False, prefecture='13'):
        return observation(source, url=url or f'https://www.example.org/{source}', title='特別展「植物と記憶」',
                           venue=venue, prefecture=prefecture, dates=(start, ending), official=official)

    def test_venue_follow_uses_canonical_alias_and_confirmed_location(self):
        aliases = self.settings['venue_aliases']
        venue = {'venue': '国立新美術館', 'country': 'JP', 'prefecture': '13'}
        ref = venue_reference(venue, aliases)
        romanized = {**venue, 'venue': 'The National Art Center, Tokyo'}
        self.assertEqual(venue_reference(romanized, aliases), ref)
        self.assertNotEqual(venue_reference({**venue, 'prefecture': '26'}, aliases)['venue_id'], ref['venue_id'])
        self.assertEqual(venue_reference({**venue, 'venue': '会場未定'}, aliases), {})

    def test_official_dates_win_without_erasing_conflict_or_changing_id(self):
        prior = merge_observations([], [self.example()], self.settings, self.instant)
        authoritative = self.example('national-art-center', '2026-12-10', official=True)
        result = merge_observations(prior, [authoritative], self.settings, self.instant)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], prior[0]['id'])
        self.assertEqual(result[0]['end_date'], '2026-12-10')
        self.assertTrue(result[0]['official'])
        self.assertTrue(result[0]['date_conflict'])
        self.assertEqual(len(result[0]['evidence']), 2)

    def test_same_title_other_venue_or_year_is_not_merged(self):
        records = [self.example(), self.example('artexhibition', start='2027-11-01', ending='2027-12-12'),
                   self.example('tokyo-art-beat', venue='大阪の画廊', prefecture='27')]
        self.assertEqual(len(merge_observations([], records, self.settings, self.instant)), 3)

    def test_seasonal_title_variants_share_a_recommendation_without_replacing_reading_ids(self):
        source = self.example()
        title = '青年武良茂（水木しげる）と戦争'
        rows = [
            {**source, 'id': 'variant', 'title_original': f'秋の企画展「{title}」', 'start_date': source['start'],
             'end_date': source['end'], 'country': 'JP', 'flags': ['special'], 'evidence': [{**source, 'title': f'秋の企画展「{title}」'}]},
            {**source, 'id': 'original', 'title_original': f'「{title}」', 'start_date': source['start'],
             'end_date': source['end'], 'country': 'JP', 'evidence': [{**source, 'title': title, 'url': 'https://other.example/show'}]},
        ]
        items = public_items({'items': rows})
        self.assertEqual(set(items), {'variant', 'original'})
        self.assertEqual(items['variant']['duplicate_group'], items['original']['duplicate_group'])
        self.assertEqual(items['variant']['recommendation'], items['original']['recommendation'])
        self.assertEqual(items['variant']['recommendation']['tier'], 1)
        self.assertEqual([source['url'] for source in items['variant']['related_sources']], ['https://other.example/show'])

    def test_programme_evidence_requires_a_matching_claim_from_independent_sources_for_the_top_tier(self):
        title = '北湾国際芸術祭 2027'
        source = {'title': title, 'url': 'https://www.directory.example/1', 'official': False}
        row = {'id': 'festival', 'title_original': title, 'evidence': [source]}
        add_recommendations({'festival': row})
        self.assertEqual(row['recommendation']['tier'], 2)
        row['evidence'] += [{**source, 'url': 'https://directory.example/2'},
                            {**source, 'title': '芸術祭', 'url': 'https://other.example/1'}]
        add_recommendations({'festival': row})
        self.assertEqual(row['recommendation']['tier'], 2)
        row['evidence'].append({**source, 'url': 'https://another.example/1'})
        add_recommendations({'festival': row})
        self.assertEqual(row['recommendation']['tier'], 3)

    def test_verified_programme_applies_to_its_reviewed_dates(self):
        row = {'id': 'survey', 'title_original': '展覧会', 'start_date': '2026-11-01', 'end_date': '2026-11-30'}
        policy = {'verified_programmes': [{'ids': ['survey'], 'url': 'https://museum.example/programme',
                  'start_date': row['start_date'], 'end_date': row['end_date'], 'reason': '主办方确认馆藏联展。'}], 'related_events': []}
        add_recommendations({'survey': row}, policy)
        self.assertEqual(row['recommendation']['tier'], 3)
        row['end_date'] = '2027-01-20'
        add_recommendations({'survey': row}, policy)
        self.assertEqual(row['recommendation']['tier'], 1)

    def test_standalone_one_day_talk_and_a_one_day_exhibition_are_distinct(self):
        dates = {'start_date': '2026-11-27', 'end_date': '2026-11-27'}
        items = {'lecture': {'id': 'lecture', 'title_original': '連続講座「収集史」', **dates},
                 'show': {'id': 'show', 'title_original': '作品展「一日の絵」', **dates}}
        add_recommendations(items)
        self.assertEqual(items['lecture']['related_event'], '讲座')
        self.assertNotIn('related_event', items['show'])

    def test_missing_source_on_next_run_preserves_the_archived_exhibition(self):
        prior = merge_observations([], [self.example()], self.settings, self.instant)
        result = merge_observations(prior, [], self.settings, self.instant)
        self.assertEqual(result, prior)

    def test_compact_catalogue_keeps_details_on_their_own_page_with_matching_provenance(self):
        source = {**self.example(), 'intro_excerpt': '公開の短い紹介'}
        row, = merge_observations([], [source], self.settings, self.instant)
        catalogue = {'generated_at': None, 'items': [row], 'coverage': {'sources': {'internet-museum': {'name': 'Internet Museum'}}}}
        items = public_items(catalogue)
        detail = {row['id']: {'status': 'introduction', 'url': source['url'], 'source': source['source'], 'paragraphs': ['説明です。']}}
        index, = compact_list(catalogue, items)['items']
        self.assertEqual(index['id'], row['id'])
        self.assertEqual(index['venue_id'], items[row['id']]['venue_id'])
        self.assertNotIn('evidence', index)
        payload = detail_view(row, {'entries': detail}, catalogue['coverage'])
        self.assertEqual(payload['description']['paragraphs'], ['説明です。'])
        self.assertEqual(payload['sources'], {'internet-museum': 'Internet Museum'})
        detail[row['id']]['url'] = 'https://example.org/stale'
        self.assertEqual(pick_intro(row, detail)['status'], 'excerpt')

    def test_an_official_collection_hub_can_reuse_its_url_without_reassigning_notes(self):
        page = 'https://www.example.org/collection/?type=now'
        earlier = {**self.example(url=page), 'shared_index_url': True}
        later = {**self.example(url=page, start='2027-11-01', ending='2027-12-12'), 'shared_index_url': True}
        old = merge_observations([], [earlier], self.settings, self.instant)
        result = merge_observations(old, [later], self.settings, self.instant)
        self.assertEqual(len(result), 2)
        self.assertEqual(next(r for r in result if r['start_date'] == '2026-11-01')['id'], old[0]['id'])
