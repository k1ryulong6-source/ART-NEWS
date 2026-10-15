import unittest
from backend.ingestion import rss_records
from backend.coverage import reconcile_rss


class SourceFilterTests(unittest.TestCase):
    def test_culture_category_filter_excludes_gear_without_rejecting_artists_or_awards(self):
        source = {'id': 'public', 'name': 'Public', 'channels': ['photography'], 'language': 'de',
                  'source_type': 'media', 'adapter': 'rss', 'include_categories': ['Kultur', 'Bücher'],
                  'exclude_title_regex': 'Imaging World|photokina'}
        items = [('New lens', 'Technik News'), ('CEWE Photo Award', 'Kultur'),
                 ('Photographer collection', 'Bücher'), ('Imaging World fair', 'Kultur')]
        xml = '<rss><channel>' + ''.join('<item><title>' + t + '</title><link>https://example.org/' + str(i) + '</link><category>' + c + '</category></item>' for i, (t, c) in enumerate(items)) + '</channel></rss>'
        records, _, _ = rss_records(source, xml.encode())
        self.assertEqual([r['title_original'] for r in records], ['CEWE Photo Award', 'Photographer collection'])
        report = reconcile_rss({'content': records}, source, xml.encode())
        self.assertEqual(report['eligible'], 2)
        self.assertEqual(report['missing'], [])
        self.assertEqual([r['reason'] for r in report['excluded']], ['source_config_filter'] * 2)
