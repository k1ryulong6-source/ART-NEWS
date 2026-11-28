import json
import unittest
from datetime import date, datetime, timezone

from bs4 import BeautifulSoup

from backend.film_calendar import local_day, parse_screenings, record_id, refresh
from backend.japan_film_calendar import current_films, release_dates, screening_dates
from backend.streaming_premieres import apple_dates, press_dates, press_premiere


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
                         [('cinema_release','2026-12-01',None)])
        self.assertTrue(rows[0]['poster_url'].endswith('/320.jpg'))
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

    def test_disney_ignores_monthly_catalogue_and_accepts_dated_original_film_announcement(self):
        source = {'id':'disney-hulu','adapter':'disney','name':'Disney Press','url':'https://press.disneyplus.com/news','timezone':'America/New_York'}
        index = BeautifulSoup('''<a href="/news/next-on-disney-plus-december-2026">December films and premieres</a>
        <a href="/news/new">Disney+ Original Movie “New Film” premieres December 7</a>''','html.parser')
        page = '''<meta property="article:published_time" content="2026-11-25T00:00:00Z">
        <div class="rich-text-container"><p>The Disney+ Original movie New Film premieres December 7, only on Disney+.</p></div>'''
        coverage = {}
        rows = list(press_dates(index,source,{'https://press.disneyplus.com/news/new':page}.__getitem__,coverage))
        self.assertEqual([(r['platform'],r['start_date'],r['title_original']) for r in rows],
                         [('Disney+','2026-12-07','New Film')])

    def test_netflix_press_distinguishes_premiere_date_from_news_date(self):
        source = {'id':'netflix-newsroom','adapter':'netflix_news','name':'About Netflix',
                  'url':'https://about.netflix.com/en/newsroom','timezone':'UTC','platform':'Netflix'}
        index = BeautifulSoup("""<a href='/en/news/one'>Documentary 'Ocean' premieres December 3</a>
        <a href='/en/news/two'>Series 'Ocean II' premieres December 4</a>
        <a href='/en/news/three'>Film 'Ocean III' releases on Netflix December 5</a>""",'html.parser')
        article = '''<p class="ArticleDateWrapper">19 November 2026</p><div class="ArticleCopy">
        <p>Ocean, a new documentary about sea life, premieres at a theatre November 25, then debuts globally on Netflix on December 3.</p></div>'''
        series = article.replace('a new documentary about sea life','a documentary series').replace('Ocean','Ocean II')
        catalogue = article.replace('Ocean','Ocean III').replace('premieres at a theatre November 25, then debuts globally on Netflix on December 3',
                                                                  'will be available on Netflix starting December 5')
        pages = {'one':article, 'two':series, 'three':catalogue}
        rows = list(press_dates(index,source,lambda url: pages[url.rsplit('/',1)[-1]],{}))
        self.assertEqual([(r['start_date'],r['title_original']) for r in rows],[('2026-12-03','Ocean')])
        self.assertEqual(rows[0]['premiere_source_url'], 'https://about.netflix.com/en/news/one')

    def test_apple_premiere_must_match_original_film_and_latest_concrete_date(self):
        source = {'id':'apple-tv','name':'Apple TV Press','url':'https://www.apple.com/tv-pr/originals/',
                  'timezone':'America/Los_Angeles','platform':'Apple TV'}
        sample = {'showTypeKey':'films','title':'Movie','url':'/tv-pr/originals/movie/',
                  'releaseDateDisplayString':'November 25, 2026','releaseDateISOString':'2026-11-25T00:00:00Z'}
        payload = {'results':{'originals':[
            sample,
            {**sample,'title':'Monthly','releaseDateDisplayString':'December 2026','releaseDateISOString':'2026-12-01T00:00:00Z'},
            {**sample,'title':'Series','showTypeKey':'series'},
            {**sample,'title':'Only year','releaseDateDisplayString':'2027','releaseDateISOString':'2027-01-01T00:00:00Z'},
            {**sample,'title':'Mismatch','releaseDateISOString':'2026-01-01T00:00:00Z'},
            {**sample,'title':'Already Online'}
        ]}}
        feed = '<feed>' + ''.join(f'<entry><title>“{name}” premieres</title><id>https://www.apple.com/tv-pr/news/{slug}/</id></entry>'
                                  for name, slug in [('Movie','movie'),('Monthly','month'),('Already Online','earlier')]) + '</feed>'
        page = '<div class="body-copy"><p>“Movie” debuts in cinemas November 20 and globally on Apple TV November 25, 2026.</p></div>'
        earlier = page.replace('“Movie”','“Already Online”').replace('</p>', ' Already Online was previously released online.</p>')
        rows = list(apple_dates(json.dumps(payload),feed,source,lambda url: earlier if '/earlier/' in url else page,{}))
        self.assertEqual([(r['title_original'],r['start_date'],r['date_precision']) for r in rows],
                         [('Movie','2026-11-25','day')])
        self.assertTrue(rows[0]['evidence_url'].endswith('/originals/movie/'))

    def test_weekly_regional_arrivals_and_digital_rereleases_are_not_premieres(self):
        cases = (
            ['Ocean premieres on December 3, only on Netflix in Japan.'],
            ['Ocean debuts globally on Netflix on December 3.', 'Ocean was available to rent in August.'],
            ['Ocean will be available on Netflix on December 3.'],
        )
        for paragraphs in cases:
            with self.subTest(paragraphs=paragraphs):
                self.assertIsNone(press_premiere(paragraphs,'Ocean','Netflix',date(2026,11,25)))
        self.assertIsNone(press_premiere(['Ocean debuts globally on Netflix on December 3.'],
                                        'Ocean','Netflix',date(2026,11,25),require_first_online=True))

    def test_refresh_drops_unverified_saved_streams_even_if_press_sources_are_unavailable(self):
        source = {'id':'netflix','adapter':'netflix_news','name':'About Netflix',
                  'url':'https://about.netflix.com/en/newsroom','timezone':'UTC','platform':'Netflix'}
        unavailable = {'id':'previous-stream','source_id':'netflix','title_original':'Library movie',
                       'event_type':'streaming_release','platform':'Netflix','date_precision':'day',
                       'start_date':'2026-12-02','evidence_url':'https://about.netflix.com/en/news/film'}
        verified = {**unavailable,'id':'new-film','start_date':'2026-12-03',
                    'premiere_source_url':'https://about.netflix.com/en/news/premiere','premiere_basis':'official_announcement'}
        cinema = {**unavailable,'id':'cinema','event_type':'cinema_release'}
        previous = {'items':[cinema,verified,unavailable], 'sources':{}}
        def blocked(_):
            raise ValueError('source_crawl_disallowed')
        result = refresh(previous,[source],fetch_factory=lambda _: blocked)
        self.assertEqual([row['id'] for row in result['items']], ['cinema','new-film'])
        self.assertEqual(result['sources']['netflix']['status'],'failed')

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
