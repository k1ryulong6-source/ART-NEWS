import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.japanese_art import artexhibition_records, tokyo_art_beat_records, tab_article_pages
from backend.articles import extract_article
from backend.ingestion import content_record
from backend.storage import Store


class JapaneseArtTests(unittest.TestCase):
    def source(self, sid='tokyo-art-beat'):
        return next(s for s in json.loads(Path('config/sources.json').read_text())['sources'] if s['id'] == sid)

    def hydration(self, name, props, data):
        value = {'props': {'pageProps': {'fallback': {json.dumps({'name': name, 'props': props}): {'data': data}}}}}
        return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(value) + '</script>'

    def page(self, current=0, total=3, **extra):
        row = {'slug': 'report', 'articleType': 'Page nation', 'paginated_content_total': total,
               'paginated_content_current': current,
               'paginated_content': {'page': current, 'content': [{'nodeType': 'paragraph', 'content': [{'nodeType': 'text', 'value': f'Public page {current + 1}. ' * 20}]}]},
               'paginated_contents': [{'content': 'HIDDEN ALL PAGE SUBSCRIPTION TEXT'}], **extra}
        props = {'slug': 'report', **({'q': ['page' + str(current + 1)]} if current else {})}
        return self.hydration('ArticleDetail', props, [row])

    def first(self):
        return ('<html><head><script type="application/ld+json">{"@type":"NewsArticle","author":{"name":"Author"}}</script></head><body>'
                '<div class="articleDetail"><div class="articleMainImage-wrap"><img src="/main.jpg"><p class="articleFigcaption">Credit: artist</p></div>'
                '<div class="articleDetailTitleBottoms"><p>SHARE PROFILE NOISE</p></div>'
                '<div class="detailContent"><p>' + 'Introduction. ' * 20 + '</p></div>'
                '<div class="detailContent"><p>' + 'Public page one. ' * 20 + '</p></div>'
                '<div class="pagenation"><button>1</button><button>2</button><button>3</button></div>'
                '<div class="relatedConent"><div class="detailContent"><p>UNRELATED NEWS</p></div></div>'
                '<div class="detailContent marginContent"><p>TAG NOISE</p></div></div>' + self.page() + '</body></html>')

    def test_tab_list_preserves_time_image_and_interview_without_guessing_location(self):
        row = {'slug': 'artist-profile', 'title': '写真家インタビュー', 'publishedAt': '2026-10-15T09:00:00Z',
               'categories': [{'fields': {'name': 'インタビュー'}}],
               'mainImage': {'fields': {'file': {'url': '//images.example.org/photo.jpg'}, 'description': 'Artist'}}}
        xml = self.hydration('ArticleSearch', {'condId': 'latest'}, [row, row, {**row, 'slug': '//evil.example'}, {**row, 'slug': 'gear', 'title': 'カメラレビュー'}])
        rows, events, links = tokyo_art_beat_records(self.source(), xml)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['published_at'], '2026-10-15T09:00:00+00:00')
        self.assertEqual(rows[0]['image_url'], 'https://images.example.org/photo.jpg')
        self.assertEqual(rows[0]['kind'], 'interview')
        self.assertEqual(rows[0]['channel'], 'photography')
        self.assertIsNone(rows[0]['country'])
        self.assertEqual((events, links), ([], []))

    def test_photo_report_is_not_automatically_photography(self):
        xml = self.hydration('ArticleSearch', {'condId': 'latest'}, [{'slug': 'painting', 'title': 'New painting exhibition', 'publishedAt': 'bad', 'categories': [{'fields': {'name': 'フォトレポート'}}]}])
        row = tokyo_art_beat_records(self.source(), xml)[0][0]
        self.assertEqual(row['channel'], 'art')
        self.assertIsNone(row['published_at'])

    def test_changed_list_does_not_silently_report_zero_success(self):
        for method, sid in [(artexhibition_records, 'artexhibition'), (tokyo_art_beat_records, 'tokyo-art-beat')]:
            with self.assertRaises(ValueError): method(self.source(sid), '<html>Structure changed</html>')

    def test_art_list_deduplicates_members_metadata_without_inventing_clock(self):
        card = '<article><h3 class="article-title"><a href="/topics/events/members/20261015-AEJ123/">展覧会情報</a></h3><div class="body-txt">Introduction</div><time datetime="2026-10-15">2026.10.15</time><figure><img src="/art.jpg"></figure></article>'
        rows, events, _ = artexhibition_records(self.source('artexhibition'), '<main><div class="grid-tile">' + card * 2 + '</div></main>')
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]['published_at'])
        self.assertIsNone(rows[0]['country'])
        self.assertEqual(rows[0]['excerpt_origin'], 'public_page')
        self.assertEqual(events, [])

    def test_public_pagination_keeps_every_page_intro_image_caption_and_author(self):
        calls = []
        def getter(url, source):
            calls.append(url)
            return self.page(int(url[-1]) - 1), url
        payload = tab_article_pages(self.first(), 'https://www.tokyoartbeat.com/articles/-/report', self.source(), getter)
        fields = extract_article(payload, 'https://www.tokyoartbeat.com/articles/-/report', self.source())
        self.assertEqual(fields['article_status'], 'collected')
        for text in ['Introduction.', 'Public page one.', 'Public page 2.', 'Public page 3.']:
            self.assertIn(text, fields['article_text'])
        for text in ['HIDDEN ALL PAGE', 'UNRELATED NEWS', 'TAG NOISE', 'SHARE PROFILE NOISE']:
            self.assertNotIn(text, payload)
        self.assertEqual(fields['article_author'], 'Author')
        image = json.loads(fields['article_blocks_json'])[0]
        self.assertEqual(image['caption'], 'Credit: artist')
        self.assertEqual(len(calls), 2)

    def test_index_sections_are_not_mistaken_for_separate_pages(self):
        first = self.first().replace('<div class="pagenation"><button>1</button><button>2</button><button>3</button></div>', '').replace('Page nation', 'Index')
        def getter(*args): self.fail('Index is a full single public page')
        payload = tab_article_pages(first, 'https://www.tokyoartbeat.com/articles/-/report', self.source(), getter)
        self.assertEqual(extract_article(payload, 'https://www.tokyoartbeat.com/articles/-/report', self.source())['article_status'], 'collected')

    def test_selected_page_event_reference_keeps_dates_but_article_card_is_removed(self):
        from backend.japanese_art import render_public_nodes
        def entry(kind, fields):
            return {'nodeType': 'embedded-entry-block', 'data': {'target': {'sys': {'contentType': {'sys': {'id': kind}}}, 'fields': fields}}}
        nodes = [entry('article', {'title': {'en-US': 'UNRELATED'}}), entry('event', {'eventName': {'en-US': 'English', 'ja-JP': '日本展'}, 'slug': {'en-US': 'exhibition/venue/date'}, 'scheduleStartsOn': {'en-US': '2026-10-20'}, 'scheduleEndsOn': {'en-US': '2026-11-20'}, 'description': {'en-US': 'UNRENDERED'}})]
        result = render_public_nodes(nodes, 'https://www.tokyoartbeat.com/articles/-/report/page2')
        self.assertIn('日本展', result)
        self.assertIn('2026-10-20', result)
        self.assertIn('/events/-/exhibition/venue/date', result)
        self.assertNotIn('UNRELATED', result)
        self.assertNotIn('UNRENDERED', result)

    def test_failed_or_wrong_page_is_partial_without_silent_truncation(self):
        for wrong in [self.page(0), self.page(1, slug='other'), self.page(1, total=4), self.page(1, articleType='Members only')]:
            payload = tab_article_pages(self.first(), 'https://www.tokyoartbeat.com/articles/-/report', self.source(), lambda url, source: (wrong, url))
            fields = extract_article(payload, 'https://www.tokyoartbeat.com/articles/-/report', self.source())
            self.assertEqual(fields['article_status'], 'partial')
            self.assertEqual(fields['article_reason'], 'public_pagination_incomplete')
            self.assertIn('Public page one.', fields['article_text'])

    def test_publisher_restriction_prevents_page_data_recovery(self):
        first = self.first().replace('<head>', '<head><script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false}</script>')
        def getter(*args): self.fail('Restricted article must not request more pages')
        payload = tab_article_pages(first, 'https://www.tokyoartbeat.com/articles/-/report', self.source(), getter)
        fields = extract_article(payload, 'https://www.tokyoartbeat.com/articles/-/report', self.source())
        self.assertEqual(fields['article_status'], 'partial')
        self.assertEqual(fields['article_reason'], 'public_visible_body')

    def test_art_body_keeps_table_dates_caption_quotes_and_only_trims_proven_recommendation(self):
        source = self.source('artexhibition')
        paragraph = 'The artist discusses newsletters and related articles in her practice. ' * 5
        payload = ('<meta property="article:published_time" content="2026-10-15T14:00:04+09:00">'
                   '<article class="main-content"><div class="main-content-header"><p>SHARE</p></div><div class="news-detail"><p>' + paragraph + '</p>'
                   '<figure><img src="/art.jpg"><figcaption>Artist credit</figcaption></figure><table><tr><th>Opening</th><td>2026年10月20日<p>Tickets: 1500円</p></td></tr></table>'
                   '<p>Venue and event details<br>＜あわせて読みたい＞<br>UNRELATED RECOMMENDATION</p><div class="iframely-embed"><a data-iframely-url="https://iframely.net/example" href="https://artexhibition.jp/topics/news/20261015-AEJ999/"></a></div></div>'
                   '<div class="main-content-footer"><p>FOOTER</p></div></article>')
        fields = extract_article(payload, 'https://artexhibition.jp/topics/news/20261015-AEJ123/', source)
        self.assertEqual(fields['published_at'], '2026-10-15T05:00:04+00:00')
        for text in ['Opening', '2026年10月20日', 'Tickets: 1500円', paragraph.strip(), 'Venue and event details']:
            self.assertIn(text, fields['article_text'])
        self.assertEqual(fields['article_text'].count('Tickets: 1500円'), 1)
        for text in ['UNRELATED RECOMMENDATION', 'SHARE', 'FOOTER']:
            self.assertNotIn(text, fields['article_text'])
        self.assertEqual(next(b for b in json.loads(fields['article_blocks_json']) if b['type'] == 'image')['caption'], 'Artist credit')

    def test_metadata_refresh_does_not_erase_article_publication_timestamp(self):
        source = self.source('artexhibition')
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'test.db'); store.register_sources([source])
            url = 'https://artexhibition.jp/topics/news/20261015-AEJ123/'
            store.ingest_records([content_record(source, 'Report', url, published='2026-10-15T05:00:04+00:00')], [], [])
            store.ingest_records([content_record(source, 'Updated report', url)], [], [])
            self.assertEqual(store.dataset('live')['content'][0]['published_at'], '2026-10-15T05:00:04+00:00')
