import json, re, tempfile, unittest
from pathlib import Path
from backend.share_pages import article_page, display_title, shareable, summary, write_share_pages

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / 'frontend/index.html').read_text(encoding='utf-8')
SITE = 'https://example.org/'


def row(**extra):
    base = {'id': 'live-' + 'a' * 24, 'title_original': 'Original <Title>', 'excerpt_original': 'Short excerpt.', 'published_at': '2026-10-15T08:00:00Z',
            'image_url': 'https://img.example.org/p.jpg', 'canonical_url': 'https://news.example.org/story'}
    base.update(extra)
    return base


class SharePageTests(unittest.TestCase):
    def test_page_carries_its_own_preview_and_hands_off_to_the_reader(self):
        html = article_page(TEMPLATE, row(), SITE)
        self.assertIn('<base href="../../">', html)
        self.assertIn('#reader/live-' + 'a' * 24, html)
        self.assertIn('<title>Original &lt;Title&gt; · 幕间休息</title>', html)
        self.assertIn('<meta property="og:title" content="Original &lt;Title&gt;">', html)
        self.assertIn('<meta property="og:url" content="https://example.org/a/live-%s/">' % ('a' * 24), html)
        self.assertIn('<meta property="og:image" content="https://img.example.org/p.jpg">', html)
        self.assertNotIn('og:image:width', html)
        self.assertEqual(len(re.findall(r'rel="canonical"', html)), 1)
        self.assertIn('<meta name="description" content="Short excerpt.">', html)
        self.assertIn('<h1>Original &lt;Title&gt;</h1>', html)

    def test_titles_and_summaries_follow_the_reader_priority(self):
        ai = row(editorial_status='translated', editorial_title_zh='中文标题', editorial_blocks_json='[]', editorial_excerpt_zh='中文摘要' * 50)
        self.assertEqual(display_title(ai), '中文标题')
        self.assertEqual(len(summary(ai)), 120)
        self.assertEqual(display_title(row(), {row()['id']: {'source_title': 'Original <Title>', 'title_zh': '校译标题'}}), '校译标题')
        self.assertEqual(summary(row(excerpt_original=None, article_blocks_json=json.dumps([{'type': 'paragraph', 'text': 'Body  text'}]))), 'Body text')

    def test_unsafe_images_fall_back_and_demo_or_odd_ids_get_no_page(self):
        html = article_page(TEMPLATE, row(image_url='http://img.example.org/p.jpg'), SITE)
        self.assertIn('content="https://example.org/og-image.png"', html)
        self.assertEqual(shareable([row(), row(id='demo-x'), row(id='live-../x'), row(id='live-' + 'b' * 24, is_demo=True)]), [row()])

    def test_writes_pages_sitemap_and_robots(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'a/live-stale').mkdir(parents=True)
            count = write_share_pages(out, TEMPLATE, {'content': [row(), row(id='live-' + 'c' * 24, published_at='2026-10-16')]}, 'https://example.org')
            self.assertEqual(count, 2)
            self.assertFalse((out / 'a/live-stale').exists())
            self.assertTrue((out / 'a' / ('live-' + 'a' * 24) / 'index.html').exists())
            sitemap = (out / 'sitemap.xml').read_text()
            self.assertLess(sitemap.index('c' * 24), sitemap.index('a' * 24))
            self.assertIn('<lastmod>2026-10-15</lastmod>', sitemap)
            self.assertIn('Sitemap: https://example.org/sitemap.xml', (out / 'robots.txt').read_text())
            self.assertEqual(write_share_pages(out, TEMPLATE, {'content': [row()]}, None), 0)
