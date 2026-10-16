import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.articles import extract_article
from backend.article_cleanup import subset_indexes, cached_widget_indexes, widget_deletions_only
from backend.autonomous_translation import digest, machine_ready
from backend.ingestion import content_record
from backend.storage import Store
from scripts.clean_article_bodies import clean_saved_bodies


class CleanupTests(unittest.TestCase):
    def test_a_shorter_publisher_page_is_not_permission_to_delete_real_paragraphs(self):
        prose = {'type': 'paragraph', 'text': self.prose}
        heading = {'type': 'heading', 'text': 'Related Articles'}
        ending = {'type': 'paragraph', 'text': 'A real paragraph that disappeared behind a new subscription curtain.'}
        original = [prose, heading, ending]
        self.assertTrue(widget_deletions_only(self.html, self.source['homepage_url'], self.source, original, [0, 2]))
        self.assertFalse(widget_deletions_only(self.html, self.source['homepage_url'], self.source, original, [0]))

    def test_new_publishers_remove_promotions_but_preserve_prose_and_author(self):
        body = 'The artist discusses subscriptions as a cultural subject. ' * 4
        html = '<div class="article__content"><p>' + body + '</p><div id="block-monopol-plus-paywall-curtain"><p>Subscription sales offer</p></div></div>'
        result = extract_article(html, 'https://example.org/story', {'id': 'monopol', 'name': 'Monopol', 'source_type': 'media', 'article_selectors': ['.article__content']})
        self.assertIn(body.strip(), result['article_text'])
        self.assertNotIn('Subscription sales offer', result['article_text'])
        html = '<article class="single-article--active"><p>' + body + '</p><section class="article-footer"><p>Donation and newsletter</p><a href="/authors/person/">Public Author</a></section></article>'
        result = extract_article(html, 'https://example.org/story', {'id': 'mistermotley', 'name': 'Mister Motley', 'source_type': 'media', 'article_selectors': ['article.single-article--active']})
        self.assertNotIn('Donation and newsletter', result['article_text'])
        self.assertEqual(result['article_author'], 'Public Author')

    def sharing_widget(self):
        return ('<div data-component="social-media"><ul data-alias="social-media__list">'
                '<li><a href="https://www.facebook.com/sharer.php?u=https://www.artnews.com/a">Share on Facebook</a></li>'
                '<li><a href="https://www.reddit.com/submit?url=https://www.artnews.com/a">Submit to Reddit</a></li>'
                '<li><a href="https://www.linkedin.com/shareArticle?url=https://www.artnews.com/a">Share on LinkedIn</a></li>'
                '<li>Post</li><li>Pin it</li><li>Post to Tumblr</li><li>Email</li><li>Print This Page</li><li>Share on WhatsApp</li>'
                '</ul></div>')

    def test_share_email_print_component_removed_but_discussion_and_links_kept(self):
        html = ('<div class="article-body">' + self.sharing_widget() + '<p>' + self.prose + '</p>'
                '<blockquote>The work is titled “Share on Facebook”.</blockquote>'
                '<p>A reader may <a href="https://www.facebook.com/artist">follow the artist on Facebook</a>.</p>'
                '<figure><img src="/art.jpg"><figcaption>Art print, 2026</figcaption></figure></div>')
        result = extract_article(html, self.source['homepage_url'] + '/a', self.source)
        blocks = json.loads(result['article_blocks_json'])
        self.assertFalse(any(b['type'] == 'list_item' for b in blocks))
        self.assertIn(self.prose, result['article_text'])
        self.assertIn('The work is titled “Share on Facebook”.', result['article_text'])
        self.assertIn('follow the artist on Facebook', result['article_text'])
        self.assertEqual(next(b for b in blocks if b['type'] == 'image')['caption'], 'Art print, 2026')
        self.assertNotIn('Print This Page', result['article_text'])

    def test_share_alias_run_is_dom_proof_not_a_keyword_deletion(self):
        html = '<div class="article-body">' + self.sharing_widget() + '<p>' + self.prose + '</p></div>'
        legacy = html.replace('data-component="social-media"', '').replace('data-alias="social-media__list"', '')
        old = json.loads(extract_article(legacy, self.source['homepage_url'], self.source)['article_blocks_json'])
        indexes = cached_widget_indexes(html, self.source['homepage_url'], self.source, old)
        self.assertEqual(indexes, [9])
        self.assertTrue(widget_deletions_only(html, self.source['homepage_url'], self.source, old, indexes))
        # The same words and URLs in a real list without component evidence stay.
        self.assertIsNone(cached_widget_indexes(legacy, self.source['homepage_url'], self.source, old))

    def test_cleanup_preserves_matching_api_checkpoint_without_api_call(self):
        from backend.ai_translation import configuration, input_hash, source_units
        from backend.article_cleanup import remap_ai_progress
        with TemporaryDirectory() as td:
            store = Store(Path(td) / 'test.db'); store.register_sources([self.source])
            row = content_record(self.source, 'An artist at work', self.source['homepage_url'] + '/a')
            store.ingest_records([row], [], [])
            html = '<div class="article-body">' + self.sharing_widget() + '<p>' + self.prose + '</p></div>'
            legacy = html.replace('data-component="social-media"', '').replace('data-alias="social-media__list"', '')
            old = extract_article(legacy, row['canonical_url'], self.source)
            with store.connect() as db:
                db.execute('UPDATE content SET ' + ','.join(k + '=?' for k in old) + ' WHERE id=?', [*old.values(), row['id']])
            row = store.dataset('live')['content'][0]
            cfg = configuration(); provider = 'contextual-api:gemini:gemini-3.5-flash-lite:direct-v1'
            _, units, _ = source_units(row, cfg['source_characters_per_unit'])
            state = {'schema_version': 1, 'id': row['id'], 'provider': provider, 'source_hash': row['article_hash'],
                     'input_hash': input_hash(row, provider, cfg), 'outputs': {k: '译文:' + text for k, text in units},
                     'retry_after': '2026-10-16T07:15:00+00:00'}
            progress = Path(td) / 'progress'; progress.mkdir()
            path = progress / (row['id'] + '.json'); path.write_text(json.dumps(state))
            clean = extract_article(html, row['canonical_url'], self.source)
            self.assertIsNone(remap_ai_progress(row, clean, [9], {**state, 'source_hash': 'different'}, cfg))
            self.assertIsNone(remap_ai_progress(row, clean, [9], {**state, 'input_hash': 'stale'}, cfg))
            dry = clean_saved_bodies(store, getter=lambda url, src: (html, url), pack_directory=Path(td) / 'packs', progress_directory=progress)
            self.assertEqual(dry['preserved_ai_checkpoint_units'], 2)  # title and real paragraph
            self.assertEqual(json.loads(path.read_text()), state)
            report = clean_saved_bodies(store, apply=True, getter=lambda url, src: (html, url), pack_directory=Path(td) / 'packs', progress_directory=progress)
            saved = store.dataset('live')['content'][0]; checkpoint = json.loads(path.read_text())
            self.assertEqual(report['removed_blocks'], 9)
            self.assertEqual(report['updated_ai_checkpoints'], [row['id']])
            self.assertEqual(checkpoint['outputs']['block:0:text:0'], state['outputs']['block:9:text:0'])
            self.assertEqual(checkpoint['retry_after'], state['retry_after'])
            self.assertEqual(checkpoint['provider'], state['provider'])
            self.assertEqual(checkpoint['source_hash'], saved['article_hash'])
            self.assertEqual(checkpoint['input_hash'], input_hash(saved, provider, cfg))
            self.assertEqual(len(checkpoint['outputs']), 2)
            self.assertEqual(saved['article_text'], self.prose)

    def setUp(self):
        self.source = {'id': 'artnews', 'name': 'ARTnews', 'homepage_url': 'https://www.artnews.com',
                       'source_type': 'media', 'language': 'en', 'channels': ['art'],
                       'adapter': 'rss', 'enabled': True, 'access_status': 'reviewed',
                       'access_method': 'rss', 'verified_at': '2026-10-15'}
        self.prose = ('The artist discusses how newsletters and advertising shape visual culture. '
                      'Her installation includes the words Recommended and Related Articles. '
                      'The exhibition ends on November 13, 2026; admission costs 12 euros.')
        self.html = ('<div class="article-body"><p>' + self.prose + '</p>'
                     '<section class="article-related-links"><h2>Related Articles</h2>'
                     '<h3><a href="/other">UNRELATED CARD</a></h3><img src="/unrelated.jpg"></section>'
                     '<blockquote>“Subscribe” is the title of her artwork.</blockquote>'
                     '<figure><img src="/work.jpg" alt="Artwork"><figcaption><p>Artist credit, 2026</p></figcaption></figure>'
                     '<p>For the programme and tickets, visit the museum.</p></div>')

    def test_widgets_removed_but_words_quotes_captions_and_event_details_kept(self):
        payload = self.html.replace('</div>', '<div class="condensed-newsletter-signup"><p>SIGNUP WIDGET</p></div></div>')
        result = extract_article(payload, self.source['homepage_url'] + '/a', self.source)
        self.assertIn(self.prose, result['article_text'])
        self.assertIn('“Subscribe”', result['article_text'])
        self.assertIn('tickets', result['article_text'])
        self.assertNotIn('UNRELATED CARD', result['article_text'])
        self.assertNotIn('SIGNUP WIDGET', result['article_text'])
        blocks = json.loads(result['article_blocks_json'])
        images = [b for b in blocks if b['type'] == 'image']
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['caption'], 'Artist credit, 2026')
        self.assertFalse(any(b.get('text') == 'Artist credit, 2026' for b in blocks))

    def test_lenscratch_rail_requires_both_heading_and_adjacent_card_structure(self):
        source = {**self.source, 'id': 'lenscratch'}
        rail = '<div class="title-block"><h3>Recommended</h3></div><ul class="news-block-columns-5"><li>UNRELATED RAIL</li></ul>'
        html = '<div class="article-body"><h3>Recommended</h3><p>' + self.prose + '</p>' + rail + '</div>'
        result = extract_article(html, self.source['homepage_url'], source)
        self.assertNotIn('UNRELATED RAIL', result['article_text'])
        self.assertEqual(result['article_text'].count('Recommended'), 2)  # prose and real heading

    def test_official_outer_form_and_rules_are_not_removed(self):
        source = {**self.source, 'source_type': 'official'}
        result = extract_article('<form><div class="article-body"><p>' + self.prose + '</p>'
                                 '<h2>Rules and conditions</h2><p>Deadline: November 13, 2026.</p></div></form>',
                                 self.source['homepage_url'], source)
        self.assertIn(self.prose, result['article_text'])
        self.assertIn('Rules and conditions', result['article_text'])
        self.assertIn('Deadline:', result['article_text'])

    def test_subset_refuses_rewriting_reordering_and_wholesale_emptying(self):
        old = [{'text': 'a'}, {'text': 'b'}, {'text': 'c'}]
        self.assertEqual(subset_indexes(old, [old[0], old[2]]), [0, 2])
        self.assertIsNone(subset_indexes(old, [{'text': 'changed'}, old[2]]))
        self.assertIsNone(subset_indexes(old, [old[2], old[0]]))
        self.assertIsNone(subset_indexes(old, []))

    def test_changed_publisher_prose_is_not_overwritten_by_widget_cleanup(self):
        body = {'type': 'paragraph', 'text': self.prose}
        rail = [{'type': 'heading', 'text': 'Related Articles'},
                {'type': 'heading', 'text': 'UNRELATED CARD', 'links': [
                    {'text': 'UNRELATED CARD', 'url': 'https://www.artnews.com/other'}]},
                {'type': 'image', 'url': 'https://www.artnews.com/unrelated.jpg',
                 'alt': '', 'caption': '', 'credit': 'ARTnews'}]
        end = {'type': 'paragraph', 'text': 'Original ending remains intact.'}
        old = [body, *rail, end]
        edited = self.html.replace('The artist discusses', 'The painter discusses')
        indexes = cached_widget_indexes(edited, self.source['homepage_url'] + '/a', self.source, old)
        self.assertEqual(indexes, [0, 4])
        self.assertEqual([old[i] for i in indexes], [body, end])
        # Same widget-looking block run also occurs in the body: ambiguous, keep.
        self.assertIsNone(cached_widget_indexes(edited, self.source['homepage_url'] + '/a',
                                               self.source, [body, *rail, *rail, end]))

    def test_cached_cleanup_preserves_ai_and_machine_provenance_without_calls(self):
        with TemporaryDirectory() as td:
            store = Store(Path(td) / 'test.db'); store.register_sources([self.source])
            row = content_record(self.source, 'An artist at work', self.source['homepage_url'] + '/a')
            store.ingest_records([row], [], [])
            clean = extract_article(self.html, row['canonical_url'], self.source)
            blocks = json.loads(clean['article_blocks_json'])
            old = [blocks[0], {'type': 'heading', 'text': 'Related Articles'}, *blocks[1:]]
            old_json = json.dumps(old, ensure_ascii=False)
            original_hash = hashlib.sha256(old_json.encode()).hexdigest()
            translated = [{**b, **({'caption': '艺术家，2026'} if b['type'] == 'image'
                                      else {'text': '中文正文 13, 2026, 12。' if i == 0 else '中文引文或活动信息。'})}
                          for i, b in enumerate(old)]
            values = {'article_blocks_json': old_json, 'article_hash': original_hash,
                      'article_text': '\n\n'.join(b['text'] for b in old if b.get('text')),
                      'article_status': 'partial', 'article_reason': 'public_visible_body',
                      'article_author': 'Original author', 'editorial_title_zh': '艺术家工作中',
                      'editorial_excerpt_zh': '', 'editorial_blocks_json': json.dumps(translated, ensure_ascii=False),
                      'editorial_status': 'translated', 'editorial_provider': 'contextual-api:gemini',
                      'editorial_model': 'gemini-3.5-flash-lite', 'editorial_review_json': '{"approved":false,"status":"not_requested","issues":[]}',
                      'article_translation_json': json.dumps(translated, ensure_ascii=False),
                      'article_translation_provider': 'offline-m2m100:fixture',
                      'article_translation_hash': 'old', 'translation_status': 'machine',
                      'translated_title_zh': '艺术家'}
            with store.connect() as db:
                db.execute('UPDATE content SET ' + ','.join(k + '=?' for k in values) + ' WHERE id=?', [*values.values(), row['id']])
            get = lambda url, source: (self.html, url)
            dry = clean_saved_bodies(store, getter=get, pack_directory=Path(td) / 'packs')
            self.assertEqual(dry['changed'], [row['id']])
            self.assertEqual(store.dataset('live')['content'][0]['article_hash'], original_hash)
            result = clean_saved_bodies(store, apply=True, getter=get, pack_directory=Path(td) / 'packs')
            self.assertEqual(result['removed_blocks'], 1)
            self.assertEqual(result['preserved_ai'], 1)
            saved = store.dataset('live')['content'][0]
            self.assertEqual(saved['editorial_model'], 'gemini-3.5-flash-lite')
            self.assertEqual(saved['editorial_status'], 'translated')
            self.assertEqual(saved['editorial_review_json'], values['editorial_review_json'])
            self.assertEqual(saved['article_status'], 'partial')
            self.assertEqual(saved['article_author'], 'Original author')
            self.assertEqual(len(json.loads(saved['editorial_blocks_json'])), len(blocks))
            self.assertTrue(machine_ready(saved))
            self.assertEqual(saved['translation_input_hash'], digest(saved, 'offline-m2m100:fixture'))
            self.assertEqual(json.loads(saved['editorial_blocks_json'])[0]['text'], translated[0]['text'])
