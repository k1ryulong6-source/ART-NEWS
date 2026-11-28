import unittest
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from backend.film_metadata import MovieLookup, calendar_with_films, film_key, page_movie, refresh_metadata, wikidata_matches


def event(identifier, **fields):
    return {'id': identifier, 'title_original': '天国の日々 4K', 'event_type': 'cinema_screening',
            'evidence_url': 'https://www.shin-bungeiza.com/schedule#d2026-11-25-1', 'start_date': '2026-11-29',
            'country': 'JP', **fields}


def entity(label, year, subject, movie):
    def claim(value):
        return {'mainsnak': {'datavalue': {'value': value}}}
    return {'labels': {'en': {'value': label}}, 'claims': {
        'P577': [claim({'time': f'+{year}-01-01T00:00:00Z'})], 'P4529': [claim(subject)], 'P4947': [claim(movie)]
    }}


class FilmMetadataTests(unittest.TestCase):
    def test_eiga_stream_credits_exclude_platform_text_and_default_poster(self):
        row = {'title_original':'同じ映画'}
        page = 'https://eiga.com/movie/123/'
        html = '''<div class="poster-img"><img src="https://media.eiga.com/images/assets/no_poster_image.png"></div>
        <div class="hero-img"><img src="https://media.eiga.com/images/movie/123/still.jpg" alt="同じ映画"></div>
        <p class="data">2026年製作／日本 原題：Film Name 配信：Netflix 配信開始日：2026年12月1日</p>'''
        result = page_movie(row,BeautifulSoup(html,'html.parser'),page)
        self.assertFalse(result.get('poster_url'))
        self.assertEqual(result['original_title'],'Film Name')
        self.assertEqual(result['artwork_kind'],'still')

    def test_venue_credits_distinguish_production_year_from_the_restoration_schedule(self):
        soup = BeautifulSoup('''<div id="d2026-11-25-1"><img src="/photo/one-p.jpg"></div>
        <div class="schedule-content"><div class="schedule-content-txt"><p class="nihon-date">
        <a href="/film">天国の日々 4K</a> <small>（1978・米/94分）監督：テレンス・マリック</small>
        </p></div></div>''', 'html.parser')
        row = event('screening')
        result = page_movie(row, soup, row['evidence_url'])
        self.assertEqual(result['year'], 1978)
        self.assertEqual(result['poster_url'], 'https://www.shin-bungeiza.com/photo/one-p.jpg')
        self.assertEqual(result['poster_source_url'], row['evidence_url'])

    def test_douban_identifier_disambiguates_homonyms_before_attaching_posters(self):
        candidates = {'Q1': entity('Warm Current', 1939, '3052709', '1'),
                      'Q2': entity('Warm Current', 1957, '4127259', '2')}
        self.assertEqual(wikidata_matches(candidates, 'Warm Current'), {})
        cross_reference = wikidata_matches(candidates, 'Warm Current', 1939)
        self.assertEqual(cross_reference['id'], '3052709')

        class Lookup(MovieLookup):
            def source_facts(self, row):
                return {'year': 1939, 'poster_url': 'https://example.org/poster.jpg'}
            def wikidata(self, title, year):
                return cross_reference
            def douban(self, title):
                return {'4127259': '同名片', '3052709': '暖流'}, 'https://m.douban.com/search?query=Warm+Current'

        row = event('classic', title_original='Warm Current')
        result = Lookup().resolve(row)
        self.assertEqual(result['title_zh'], '暖流')
        self.assertTrue(result['douban_url'].endswith('/3052709/'))

    def test_shared_venue_paragraph_matches_the_second_film_and_programme_art_carries_no_title(self):
        page = 'https://www.shin-bungeiza.com/schedule#d2026-11-16-1'
        soup = BeautifulSoup('''<div id="d2026-11-16-1"><div class="schedule-box-img">
          <img src="/photo/2026-11-16-1-01-p.jpg"><img src="/photo/2026-11-16-1-02-p.jpg">
          </div></div><div class="schedule-content">
          <div class="schedule-content-img"><img src="/photo/2026-11-16-1-02-s1.jpg"></div>
          <p class="nihon-date"><a href="/film1">あるじ</a><small>（1925・デンマーク/107分）</small><br/>
          <a href="/film2">吸血鬼</a><small>（1931・仏=独/74分）</small></p>
          <div class="schedule-program"><p>2本セット ドライヤー</p></div></div>''', 'html.parser')
        second = page_movie(event('second', title_original='吸血鬼'), soup, page)
        self.assertEqual(second['year'], 1931)
        self.assertTrue(second['poster_url'].endswith('02-p.jpg'))
        self.assertTrue(second['artwork_url'].endswith('02-s1.jpg'))
        self.assertEqual(second['artwork_kind'], 'still')
        programme = event('programme', title_original='2本セット ドライヤー')
        facts = page_movie(programme, soup, page)
        self.assertEqual(facts['artwork_kind'], 'programme')
        self.assertNotIn('poster_url', facts)
        metadata = {'records': {film_key(programme, include_programmes=True): facts}}
        published = calendar_with_films(calendar={'items': [programme]}, metadata=metadata)
        self.assertEqual(published['films']['programme'], facts)
        self.assertIsNone(film_key(programme))

    def test_theatre_programme_date_binds_two_remakes_to_distinct_showtimes(self):
        suffix = ('<ul class="films" id="id1"><li><h3>『暖流（94分／35mm）』</h3></li>'
                  '<li class="img"><img src="http://www.cinemavera.com/files/warm.jpg"></li>'
                  '<li class="txt">公開：1957年</li></ul>')
        current = BeautifulSoup('<ul class="subject"><li class="schedule">2026/11/21 ～ 2026/12/18</li></ul>' + suffix, 'html.parser')
        url = 'https://www.cinemavera.com/programs.html'
        same = event('early', title_original='暖流', source_id='cinema-vera', start_date='2026-12-10')
        later = {**same, 'id': 'late', 'start_date': '2026-12-20'}
        movie = page_movie(same, current, url)
        self.assertEqual(movie['year'], 1957)
        self.assertEqual(movie['artwork_url'], 'https://www.cinemavera.com/files/warm.jpg')
        self.assertEqual(movie['artwork_source_url'], url+'#id1')
        self.assertEqual(page_movie(later, current, url), {})
        self.assertNotEqual(film_key(same), film_key(later))

    def test_unsure_results_never_replace_original_and_retry_preserves_verified_records(self):
        class Lookup(MovieLookup):
            def source_facts(self, row): return {}
            def wikidata(self, title, year): return {}
            def douban(self, title): return {'1': '同名甲', '2': '同名乙'}, 'https://m.douban.com/search'

        row = event('first')
        second = event('second', start_date='2026-11-30')
        bundle = event('double', title_original='2本セット ガイバー+ガイバー')
        saved = {film_key(row): {'title_zh': '天堂之日', 'douban_id': '1293232', 'checked_at': '2026-11-15T00:00:00+00:00'}}
        self.assertNotIn('title_zh', Lookup().resolve(row))
        initial = {'items': [row, second, bundle]}
        result = refresh_metadata(initial, [], {'records': saved}, instant=datetime(2026, 11, 28, tzinfo=timezone.utc), lookup=Lookup())
        public = calendar_with_films(calendar=initial, metadata=result)
        self.assertEqual(public['films']['first']['title_zh'], '天堂之日')
        self.assertEqual(public['films']['first'], public['films']['second'])
        self.assertNotIn('double', public['films'])
        self.assertEqual(result['report']['works'], 1)
