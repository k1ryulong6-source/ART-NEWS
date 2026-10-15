const {test} = require('node:test');
const assert = require('node:assert/strict');
const C = require('../frontend/core.js');
const UI = require('../frontend/ui.js');
const ui = UI.create({C,artwork:()=>'<div class="source-art">图</div>',saveButton:()=>'<button data-save-id="story">收藏</button>',findBookmark:()=>({id:'saved',status:'seen'}),sourceName:()=>'<script>来源</script>',publicationLabel:()=> '2026.10.14',priorityBadge:()=>''});
const row={id:'story',image_url:'https://example.org/photo.jpg',channel:'art',language:'zh',title_original:'<img src=x>作品展',excerpt_original:'<script>摘要</script>'};
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

test('pending stories preview the saved original safely without claiming translation completion',()=>{
  const pending={id:'foreign',language:'en',title_original:'Original <title>',article_blocks_json:JSON.stringify([{type:'paragraph',text:'Original <body> with details'},{type:'paragraph',text:'Second paragraph'}])};
  assert.equal(C.readingSummary(pending),'Original <body> with details');
  const html=ui.feature(pending);
  assert.match(html,/原文·待译/);assert.match(html,/Original &lt;body&gt; with details/);assert.match(html,/Second paragraph/);
  assert.ok(!html.includes('正文待译'));assert.equal(C.editorialReady(pending),false);
  const translated={...pending,editorial_status:'translated',editorial_title_zh:'中文标题',editorial_blocks_json:JSON.stringify([{type:'paragraph',text:'中文全文'}])};
  assert.match(ui.feature(translated),/中文全文/);assert.ok(!ui.feature(translated).includes('Original &lt;body&gt;'));
});

test('一种关注 links each report through the stable reader route and escapes source copy',()=>{
  const unit={id:'a-kind-of-attention',name:'一种关注',description:'<b>地区</b>',members:[{source_id:'s1',name:'<i>Media</i>',focus_label:'拉美',why:'理由',source_language:'es',homepage_url:'https://example.org/',recent_items:[{id:'live-1',title:'<script>标题</script>',title_original:'Título',published_at:'2026-10-13T00:00:00Z',original_language:'es',reader_path:'#reader/live-1'}]}]};
  const band=ui.attentionBand(unit,()=>null), page=ui.attentionPage(unit,()=>null,()=> '10/15');
  for(const html of [band,page]){assert.ok(html.includes('href="#reader/live-1"'));assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<i>Media'));assert.ok(html.includes('一種關注'));}
  assert.equal(ui.attentionBand({members:[]},()=>null),'');
});
