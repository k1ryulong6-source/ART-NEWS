import json
import unittest
from datetime import date, datetime, timezone

from bs4 import BeautifulSoup

from backend.film_calendar import apple_dates, disney_dates, local_day, netflix_news_dates, parse_screenings, record_id
from backend.japan_film_calendar import current_films, release_dates, screening_dates


class FilmCalendarTests(unittest.TestCase):
    def test_japan_release_classification_preserves_published_dates_and_omits_unverified_cards(self):
        source = {'id':'eiga-releases','name':'映画.com','url':'https://eiga.com/coming/',
                  'week_url':'https://eiga.com/upcoming/','country':'JP','timezone':'Asia/Tokyo'}
        cards = '''<h2 class="title-square">2026年 <span>12月1日</span> 公開・配信開始</h2>
        <div class="list-block" id="mv1"><h3 class="title"><a href="/movie/1/">Cinema</a></h3>
        <div class="img-box"><img src="https://media.eiga.com/images/movie/1/photo/poster/320.jpg"></div></div>
        <div class="list-block" id="mv2"><h3 class="title"><a href="/movie/2/">Streaming</a></h3>
        <div class="txt-box"><p class="txt">Netflixで2026年12月2日から配信。</p></div></div>
        <div class="list-block" id="mv3"><h3 class="title"><a href="/movie/3/">Undated</a></h3></div>'''
        pages = {source['week_url']:'', 'https://eiga.com/movie/1/':'<p class="data">劇場公開日：2026年12月1日</p>',
                 'https://eiga.com/movie/2/':'<p class="data">配信：Netflix 配信開始日：2026年12月3日</p>',
                 'https://eiga.com/movie/3/':'<p class="data">2026年製作</p>'}
        rows, coverage = release_dates(BeautifulSoup(cards,'html.parser'),source,pages.__getitem__,date(2026,11,28),[])
        self.assertEqual([(r['event_type'],r['start_date'],r['platform']) for r in rows],
                         [('cinema_release','2026-12-01',None),('streaming_release','2026-12-03','Netflix')])
        self.assertTrue(rows[0]['poster_url'].endswith('/320.jpg'))
        self.assertEqual(rows[1]['date_source_url'],'https://eiga.com/movie/2/')
        self.assertEqual(coverage['unclassified'], 1)

    def test_showing_index_paginates_without_creating_calendar_days(self):
        source = {'id':'eiga-showing','name':'映画.com','url':'https://eiga.com/now/'}
        card = '<div class="list-block" id="mv{n}"><h3 class="title"><a href="/movie/{n}/">Film {n}</a></h3></div>'
        first = '<p class="search-number">全2件</p>' + card.format(n=1) + '<ul class="pagination"><li><a href="/now/all/release/2/">次へ</a></li></ul>'
        rows = current_films(BeautifulSoup(first,'html.parser'),source,lambda _:card.format(n=2))
        self.assertEqual([r['id'] for r in rows], ['eiga-showing-1','eiga-showing-2'])
        self.assertTrue(all('start_date' not in r for r in rows))
        with self.assertRaisesRegex(ValueError,'catalogue_count_mismatch'):
            current_films(BeautifulSoup(first,'html.parser'),source,lambda _:card.format(n=1))

    def test_venue_cells_require_matching_japan_time_and_drop_mismatched_booking(self):
        start = datetime.fromisoformat('2026-11-30T16:30:00+09:00')
        source = {'id':'theatre','name':'Cinema','venue':'Cinema','url':'https://eiga.com/theater/13/1/1/',
                  'country':'JP','city':'东京','timezone':'Asia/Tokyo'}
        html = f'''<h1>Cinema</h1><section id="m1"><h2 class="title-xlarge">Film</h2>
        <div class="movie-image"><a href="/movie/1/">Poster</a><img src="/images/noimg.png"></div>
        <table class="weekly-schedule"><tr><td data-date="20261130">
        <a href="https://example.org/#20260707" data-time="{int(start.timestamp())}">16:30</a>
        <a href="https://example.org/#20261130" data-time="{int(start.timestamp())}">19:00</a>
        </td></tr></table></section>'''
        rows = list(screening_dates(BeautifulSoup(html,'html.parser'),source,datetime(2026,11,28,tzinfo=timezone.utc)))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['start_at'],start.isoformat())
        self.assertEqual(rows[0]['programme_url'],'https://eiga.com/movie/1/')
        self.assertIsNone(rows[0]['booking_url'])
        self.assertNotIn('poster_url',rows[0])

    def test_disney_monthly_evidence_preserves_each_platform_and_published_day(self):
        source = {'id':'disney-hulu','name':'Disney Press','url':'https://press.disneyplus.com/news','timezone':'America/New_York'}
        index = BeautifulSoup('<a href="/news/next-on-disney-plus-december-2026">Upcoming films</a>','html.parser')
        page = '''<div class="rich-text-container"><h1>Tuesday, December 1</h1>
        <p>Disney+ and Hulu: Movie A (2022)</p><p>Hulu: The Series (Season 3) – Premiere</p>
        <h1>Monday, December 7</h1><p>Hulu: Movie B (2000)</p></div>'''
        rows = list(disney_dates(index,source,lambda _: page))
        self.assertEqual([(r['platform'],r['start_date'],r['title_original']) for r in rows],
                         [('Disney+','2026-12-01','Movie A'),('Hulu','2026-12-01','Movie A'),('Hulu','2026-12-07','Movie B')])
        self.assertEqual([r['film_year'] for r in rows], [2022, 2022, 2000])

    def test_netflix_press_distinguishes_premiere_date_from_news_date(self):
        source = {'id':'netflix-newsroom','name':'About Netflix','url':'https://about.netflix.com/en/newsroom','timezone':'UTC','platform':'Netflix'}
        index = BeautifulSoup("<a href='/en/news/one'>Documentary 'Ocean' premieres December 3</a><a href='/en/news/two'>Series 'Ocean II' premieres December 4</a>",'html.parser')
        article = '''<p class="ArticleDateWrapper">19 November 2026</p><div class="ArticleCopy">
        <p>Ocean, a documentary about sea life, premieres on December 3, only on Netflix.</p></div>'''
        series = article.replace('a documentary about sea life','a documentary series').replace('Ocean','Ocean II')
        rows = list(netflix_news_dates(index,source,lambda url: article if url.endswith('one') else series))
        self.assertEqual([(r['start_date'],r['title_original']) for r in rows],[('2026-12-03','Ocean')])

    def test_published_apple_labels_control_date_precision(self):
        source = {'id':'apple-tv','name':'Apple TV Press','url':'https://www.apple.com/tv-pr/originals/',
                  'timezone':'America/Los_Angeles','platform':'Apple TV'}
        sample = {'showTypeKey':'films','title':'Movie','url':'/tv-pr/originals/movie/',
                  'releaseDateDisplayString':'November 25, 2026','releaseDateISOString':'2026-11-25T00:00:00Z'}
        payload = {'results':{'originals':[
            sample,
            {**sample,'title':'Monthly','releaseDateDisplayString':'December 2026','releaseDateISOString':'2026-12-01T00:00:00Z'},
            {**sample,'title':'Series','showTypeKey':'series'},
            {**sample,'title':'Only year','releaseDateDisplayString':'2027','releaseDateISOString':'2027-01-01T00:00:00Z'},
            {**sample,'title':'Mismatch','releaseDateISOString':'2026-01-01T00:00:00Z'}
        ]}}
        rows = list(apple_dates(json.dumps(payload),source))
        self.assertEqual([(r['title_original'],r['start_date'],r['date_precision']) for r in rows],
                         [('Movie','2026-11-25','day'),('Monthly','2026-12','month')])
        self.assertTrue(rows[0]['evidence_url'].endswith('/originals/movie/'))

    def test_late_show_and_new_year_follow_explicit_venue_timetable(self):
        source = {'id':'eurospace','name':'Eurospace','adapter':'eurospace','url':'https://www.eurospace.co.jp/schedule/',
                  'venue':'ユーロスペース','country':'JP','city':'东京','timezone':'Asia/Tokyo'}
        sample = '''<article><h3>2026年12月31日（木）</h3>
        スクリーン1
        <div class="scrolltable"><table><tr class="time"><td>24:30</td><td>14:00</td></tr>
        <tr><td><a href="/works/1">Night Film</a></td><td><a href="/works/1">Night Film</a></td></tr></table></div></article>'''
        late, afternoon = parse_screenings(BeautifulSoup(sample,'html.parser'),source,date(2026,12,26))
        self.assertEqual(late['start_at'],'2027-01-01T00:30:00+09:00')
        self.assertEqual(late['evidence_url'],source['url'])
        self.assertTrue(late['programme_url'].endswith('/works/1'))
        self.assertNotEqual(record_id(late),record_id(afternoon))
        self.assertEqual(local_day('1/3',date(2026,12,31)),date(2027,1,3))

    def test_bungeiza_reads_the_matching_schedule_sibling_and_month_rollover(self):
        source = {'id':'shin-bungeiza','name':'新文芸坐','adapter':'bungeiza','url':'https://www.shin-bungeiza.com/schedule',
                  'venue':'新文芸坐','country':'JP','city':'东京','timezone':'Asia/Tokyo'}
        sample = '''<div class="schedule-box" id="d2026-12-30-1"><h1>企画</h1></div><div class="schedule-content">
        <div class="schedule-content-txt"><h2><em>12/30</em></h2><div class="schedule-program"><p>Film A</p><ul><li>11:05</li></ul></div>
        <h2><em>1/2</em></h2><div class="schedule-program"><p>Film B</p><ul><li>17:30</li></ul></div></div></div>'''
        slots = list(parse_screenings(BeautifulSoup(sample,'html.parser'),source,date(2026,12,25)))
        self.assertEqual([r['start_at'] for r in slots],['2026-12-30T11:05:00+09:00','2027-01-02T17:30:00+09:00'])
