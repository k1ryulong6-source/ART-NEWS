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


class SplitBodyTests(unittest.TestCase):
    def test_bodies_move_out_with_flags_preview_and_search_text(self):
        from backend.presentation import split_bodies
        blocks=[{'type':'paragraph','text':'Original paragraph.'},{'type':'image','url':'https://example.org/p','caption':'Credit'}]
        row={'id':'live-'+'a'*24,'title_original':'T','article_blocks_json':json.dumps(blocks),'editorial_status':'translated','editorial_title_zh':'标题',
             'editorial_blocks_json':json.dumps([{'type':'paragraph','text':'中文段落'},{'type':'image','caption':'图注'}]),'body_hash':'h','fetched_at':'2026-10-16'}
        plain={'id':'demo','title_original':'No body'}
        index,bodies,search=split_bodies({'content':[row,plain],'events':[]})
        public=index['content'][0]
        for key in ('article_blocks_json','editorial_blocks_json','body_hash','fetched_at'):self.assertNotIn(key,public);self.assertEqual(bodies[row['id']][key],row[key])
        self.assertTrue(public['has_original_body']);self.assertTrue(public['has_editorial_body']);self.assertFalse(public['has_translation_body'])
        self.assertEqual(public['body_preview'],'Original paragraph.');self.assertRegex(public['body_ref'],'^[a-f0-9]{12}$')
        self.assertEqual(search[row['id']],'Original paragraph.\n\n中文段落\n\n图注')
        self.assertEqual(index['content'][1],plain);self.assertNotIn('demo',bodies)

    def test_unsafe_ids_keep_their_body_inline(self):
        from backend.presentation import split_bodies
        row={'id':'../x','article_blocks_json':'[]','article_text':'body'}
        index,bodies,_=split_bodies({'content':[row]})
        self.assertEqual(index['content'][0],row);self.assertEqual(bodies,{})
