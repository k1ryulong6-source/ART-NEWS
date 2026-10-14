const {test} = require('node:test');
const assert = require('node:assert/strict');
const C = require('../frontend/core.js');
const UI = require('../frontend/ui.js');
const ui = UI.create({C,artwork:()=>'<div class="source-art">图</div>',saveButton:()=>'<button data-save-id="story">收藏</button>',findBookmark:()=>({id:'saved',status:'seen'}),sourceName:()=>'<script>来源</script>',publicationLabel:()=> '2026.10.14',priorityBadge:()=>''});
const row={id:'story',channel:'art',language:'zh',title_original:'<img src=x>作品展',excerpt_original:'<script>摘要</script>'};
test('presentation API preserves three reading links and independent bookmark controls while escaping copy',()=>{
  assert.equal(UI.version,1);
  const card=ui.card(row,true);
  assert.equal((card.match(/href="#reader\/story"/g)||[]).length,3);
  assert.ok([...card.matchAll(/<a\b[^>]*>[^]*?<\/a>/g)].every(([anchor])=>!anchor.includes('<button')));
  assert.ok(card.includes('&lt;img src=x&gt;'));
  assert.ok(card.includes('&lt;script&gt;来源&lt;/script&gt;'));
  assert.ok(card.includes('data-bookmark-status="saved"'));
  assert.ok(card.includes('value="seen" selected'));
  assert.ok(!ui.heading('<script>标题</script>','说明').includes('<script>'));
  assert.equal((ui.feature(row).match(/href="#reader\/story"/g)||[]).length,4);
});
test('pagination retains a route to the full inventory and bounds first and last controls',()=>{
  assert.equal(ui.pagination(18,1,18),'');
  assert.match(ui.pagination(535,1,18),/data-list-page="0" disabled/);
  assert.match(ui.pagination(535,30,18),/data-list-page="31" disabled/);
  assert.match(ui.pagination(535,30,18),/value="30" selected/);
});

test('frontpage separates a lead and nine distinct stories into newspaper columns without repeating introductions',()=>{
  const rows=Array.from({length:10},(_,n)=>({...row,id:'story-'+n}));
  const html=ui.frontpage(rows,'<aside class="agenda">Dates</aside>');
  assert.match(html,/class="broadsheet"/);assert.match(html,/class="lead-column"/);
  assert.equal((html.match(/data-ui="news-card"/g)||[]).length,9);assert.equal((html.match(/data-ui="lead-story"/g)||[]).length,1);
  for(const r of rows)assert.ok(html.includes(C.readerRoute(r.id)));
  assert.ok(!ui.heading('新闻','冗长介绍').includes('冗长介绍'));
});
