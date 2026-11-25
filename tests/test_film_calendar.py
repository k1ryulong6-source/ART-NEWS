import json
import unittest
from datetime import date

from bs4 import BeautifulSoup

from backend.film_calendar import apple_dates, disney_dates, local_day, netflix_news_dates, parse_screenings, record_id


class FilmCalendarTests(unittest.TestCase):
    def test_disney_monthly_evidence_preserves_each_platform_and_published_day(self):
        source = {'id':'disney-hulu','name':'Disney Press','url':'https://press.disneyplus.com/news','timezone':'America/New_York'}
        index = BeautifulSoup('<a href="/news/next-on-disney-plus-december-2026">Upcoming films</a>','html.parser')
        page = '''<div class="rich-text-container"><h1>Tuesday, December 1</h1>
        <p>Disney+ and Hulu: Movie A (2022)</p><p>Hulu: The Series (Season 3) – Premiere</p>
        <h1>Monday, December 7</h1><p>Hulu: Movie B (2000)</p></div>'''
        rows = list(disney_dates(index,source,lambda _: page))
        self.assertEqual([(r['platform'],r['start_date'],r['title_original']) for r in rows],
                         [('Disney+','2026-12-01','Movie A'),('Hulu','2026-12-01','Movie A'),('Hulu','2026-12-07','Movie B')])

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
