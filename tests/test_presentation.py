import copy,json,unittest
from backend.presentation import browser_snapshot

class BrowserPayloadTests(unittest.TestCase):
    def test_compaction_preserves_original_blocks_translation_provenance_and_archive(self):
        blocks=[{'type':'paragraph','text':'A complete original paragraph.'},{'type':'image','url':'https://example.org/photo','caption':'Source credit'},{'type':'quote','text':'A quoted statement.'}]
        row={'id':'story','article_blocks_json':json.dumps(blocks),'article_text':'A complete original paragraph.\n\nA quoted statement.','editorial_blocks_json':'[{"type":"paragraph","text":"译文"}]','editorial_model':'actual-model','editorial_status':'translated','editorial_draft_json':'draft','article_translation_json':'legacy'}
        source={'content':[row],'events':[{'id':'event'}]};before=copy.deepcopy(source)
        result=browser_snapshot(source)
        self.assertEqual(source,before);self.assertEqual(result['events'],source['events'])
        self.assertNotIn('article_text',result['content'][0]);self.assertNotIn('article_translation_json',result['content'][0])
        for field in ('article_blocks_json','editorial_blocks_json','editorial_model','editorial_status'):self.assertEqual(result['content'][0][field],row[field])

    def test_irregular_or_oversized_blocks_retain_full_search_text(self):
        rows=[{'id':'different','article_text':'Text outside the extracted blocks','article_blocks_json':'[]'}, {'id':'broken','article_text':'Full source','article_blocks_json':'broken'}, {'id':'long','article_text':'\n\n'.join(['p']*2001),'article_blocks_json':json.dumps([{'type':'paragraph','text':'p'}]*2001)}]
        result=browser_snapshot({'content':rows})
        self.assertEqual([r['article_text']for r in result['content']],[r['article_text']for r in rows])
