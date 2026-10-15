import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from backend.articles import extract_article, collect_articles, allowed_url, fetch_article
from backend.article_translation import translate_articles
from backend.storage import Store
from backend.ingestion import content_record


class ArticleTests(unittest.TestCase):
    def test_verified_public_api_requires_exact_link_published_unprotected_post(self):
        source = {'homepage_url': 'https://example.org', 'public_wordpress_rest': True}
        url = 'https://example.org/blog/exact/'
        def missing(*args): raise HTTPError(url, 404, 'not found', {}, None)
        wrong = {'id': 1, 'link': 'https://example.org/blog/other/', 'status': 'publish',
                 'content': {'protected': False, 'rendered': '<p>Wrong article</p>'}}
        correct = {**wrong, 'id': 2, 'link': url, 'content': {'protected': False, 'rendered': '<p>Public original</p>'}}
        html, resolved = fetch_article(url, source, missing, lambda *a: [wrong, correct])
        self.assertIn('Public original', html)
        self.assertNotIn('Wrong article', html)
        self.assertEqual(resolved, 'https://example.org/wp-json/wp/v2/posts/2')
        correct['content']['protected'] = True
        with self.assertRaisesRegex(ValueError, 'matching_public_unprotected'):
            fetch_article(url, source, missing, lambda *a: [correct])
        with self.assertRaises(HTTPError): fetch_article(url, {**source, 'public_wordpress_rest': False}, missing)

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'body.db')
        self.source = {'id': 'film-stage', 'name': 'Film Stage', 'homepage_url': 'https://thefilmstage.com',
                       'channels': ['film'], 'language': 'en', 'source_type': 'media', 'access_status': 'reviewed',
                       'access_method': 'rss', 'verified_at': '2026-10-13', 'enabled': True, 'adapter': 'rss'}
        self.store.register_sources([self.source])
        self.body = 'A director presents a new film at the international festival. ' * 30
        self.html = f'<title>Festival report</title><div class="entry-content"><h2>New films</h2><p>{self.body}</p><figure><img src="/scene.jpg"><figcaption>Courtesy of the director</figcaption></figure><p>See the <a href="/programme">festival programme</a>.</p><script>alert(1)</script><p hidden>Subscriber secret</p><div class="related-posts"><p>Unrelated stories</p></div></div>'

    def seed(self, suffix='story'):
        row = content_record(self.source, 'Film festival report', 'https://thefilmstage.com/' + suffix, excerpt='An introduction.')
        self.store.ingest_records([row], [], [])
        return row

    def test_public_body_is_saved_beyond_excerpt_with_images_and_without_executable_markup(self):
        row = self.seed()
        result = collect_articles(self.store, 10, getter=lambda url, source: (self.html, url))
        self.assertEqual(result['collected'], 1)
        saved = self.store.dataset('live')['content'][0]
        self.assertGreater(len(saved['article_text']), 1000)
        self.assertIn(self.body.strip(), saved['article_text'])
        self.assertNotIn('Subscriber secret', saved['article_text'])
        self.assertNotIn('Unrelated stories', saved['article_text'])
        self.assertNotIn('alert(1)', saved['article_text'])
        blocks = json.loads(saved['article_blocks_json'])
        image = next(b for b in blocks if b['type'] == 'image')
        self.assertEqual(image['url'], 'https://thefilmstage.com/scene.jpg')
        self.assertEqual(image['caption'], 'Courtesy of the director')
        self.assertEqual(saved['article_source_url'], row['canonical_url'])

    def test_http_failure_keeps_every_record_bookmark_and_cached_body(self):
        first = self.seed('first'); second = self.seed('second')
        self.store.save_bookmark('content', first['id'])
        collect_articles(self.store, 10, getter=lambda url, source: (self.html, url))
        before = {r['id']: r['article_text'] for r in self.store.dataset('live')['content']}
        def failed(url, source): raise HTTPError(url, 403, 'Forbidden', {}, None)
        collect_articles(self.store, 10, getter=failed, force=True)
        after = {r['id']: r['article_text'] for r in self.store.dataset('live')['content']}
        self.assertEqual(before, after)
        self.assertEqual(len(self.store.bookmarks()), 1)
        self.assertEqual(len(after), 2)
        new = self.seed('third')
        collect_articles(self.store, 10, getter=failed)
        self.assertEqual(next(r for r in self.store.dataset('live')['content'] if r['id'] == new['id'])['article_status'], 'restricted')

    def test_ingestion_preserves_body_and_translation_until_original_url_changes(self):
        row = self.seed()
        collect_articles(self.store, 1, getter=lambda url, source: (self.html, url))
        with self.store.connect() as db: db.execute("UPDATE content SET article_translation_json='[]',article_translation_hash='saved' WHERE id=?", (row['id'],))
        refreshed = content_record(self.source, 'Revised headline', row['canonical_url'], excerpt='Revised introduction')
        self.store.ingest_records([refreshed], [], [])
        saved = self.store.dataset('live')['content'][0]
        self.assertIn(self.body.strip(), saved['article_text'])
        self.assertEqual(saved['article_translation_hash'], 'saved')
        refreshed['original_page_url'] = 'https://thefilmstage.com/new-page'
        self.store.ingest_records([refreshed], [], [])
        saved = self.store.dataset('live')['content'][0]
        self.assertIsNone(saved['article_blocks_json']); self.assertIsNone(saved['article_translation_hash'])

    def test_paywall_only_collects_visible_body_and_challenge_is_not_an_article(self):
        payload = '<script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false,"articleBody":"SECRET SUBSCRIPTION BODY"}</script>' + self.html
        article = extract_article(payload, 'https://thefilmstage.com/a', self.source)
        self.assertEqual(article['article_status'], 'partial')
        self.assertNotIn('SECRET SUBSCRIPTION BODY', article['article_text'])
        challenge = extract_article('<title>Just a moment...</title>' + self.html, 'https://thefilmstage.com/a', self.source)
        self.assertEqual(challenge['article_status'], 'restricted')
        self.assertNotIn('article_text', challenge)
        self.assertIsNone(allowed_url('https://127.0.0.1/private', self.source))
        self.assertIsNone(allowed_url('https://other.example/a', self.source))

    def test_official_description_in_outer_form_and_plain_text_div_is_kept(self):
        source = {**self.source, 'source_type': 'official', 'article_selectors': ['#exhibit-description']}
        payload = '<form><main><div id="exhibit-description">' + self.body + '<br>Second description paragraph.</div></main></form>'
        article = extract_article(payload, 'https://thefilmstage.com/exhibition', source)
        self.assertEqual(article['article_status'], 'collected')
        self.assertIn(self.body.strip(), article['article_text'])
        self.assertIn('Second description paragraph.', article['article_text'])

    def test_body_translation_resumes_chunks_without_repeating_calls_or_losing_original(self):
        self.seed()
        collect_articles(self.store, 1, getter=lambda url, source: (self.html, url))
        class Translator:
            name = 'fixture'; calls = 0
            def translate(self, text, language):
                self.calls += 1
                return '译文：' + text
        provider = Translator()
        before = self.store.dataset('live')['content'][0]['article_text']
        partial = translate_articles(self.store, provider, call_limit=2, daily_limit=100)
        self.assertTrue(partial['budget_exhausted'])
        saved = self.store.dataset('live')['content'][0]
        self.assertIsNone(saved['article_translation_hash'])
        self.assertTrue(saved['article_translation_json'])
        complete = translate_articles(self.store, provider, call_limit=20, daily_limit=100)
        self.assertEqual(complete['translated'], 1)
        self.assertEqual(translate_articles(self.store, provider, call_limit=20, daily_limit=100)['calls'], 0)
        self.assertEqual(before, self.store.dataset('live')['content'][0]['article_text'])
        self.assertEqual(provider.calls, 5)
