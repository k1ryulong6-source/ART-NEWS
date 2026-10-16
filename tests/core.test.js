const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('../frontend/core.js');
const demo = JSON.parse(fs.readFileSync(new URL('../data/demo.json', 'file://' + __filename), 'utf8'));
const prefs = JSON.parse(fs.readFileSync(new URL('../config/preferences.json', 'file://' + __filename), 'utf8'));

test('Babel reading uses a stable original-article link and refuses demos, missing bodies and unsafe URLs',()=>{
 const row={id:'live-'+'a'.repeat(24),article_hash:'b'.repeat(64),article_blocks_json:'[{"type":"paragraph","text":"Original body"}]',language:'ja'};
 const url=new URL(C.babelReaderUrl(row));
 assert.equal(url.pathname,'/babel/');assert.equal(url.searchParams.get('intermission'),row.id);assert.equal(url.hash,'#reading');
 assert.equal(C.babelReaderUrl({...row,is_demo:true}),'');assert.equal(C.babelReaderUrl({...row,article_blocks_json:null}),'');
 global.CULTURE_BOOTSTRAP={integrations:{babel:{enabled:true,reader_url:'javascript:alert(1)'}}};
 assert.equal(C.babelReaderUrl(row),'');delete global.CULTURE_BOOTSTRAP;
});

test('country, city, category and search filters compose', () => {
  const rows = demo.content.filter(row => C.matches(row, { channel: 'photography', country: 'JP', city: '东京', query: '摄影展' }));
  assert.ok(rows.some(row => row.id === 'demo-photo'));
  assert.ok(!rows.some(row => row.id === 'demo-photo-osaka'));
  assert.ok(!C.matches(demo.events.find(row => row.id === 'demo-film-jp'), { city: '上海' }));
});

test('buzz can be disabled and unverified gossip never enters today', () => {
  const selected = C.selectToday(demo.content, prefs);
  assert.ok(!selected.some(row => row.evidence_status === 'unverified'));
  assert.ok(selected.filter(row => row.kind === 'industry_buzz').length / selected.length <= .1);
  const disabled = C.selectToday(demo.content, { ...prefs, industry_buzz: { ...prefs.industry_buzz, enabled: false } });
  assert.ok(disabled.every(row => row.kind !== 'industry_buzz'));
  const tiny = C.selectToday(demo.content.slice(0, 4), prefs);
  assert.ok(tiny.every(row => row.kind !== 'industry_buzz'));
});

test('Japan date-only countdown is independent of UTC conversion', () => {
  const release = demo.events.find(row => row.id === 'demo-film-jp');
  assert.equal(C.daysBetween('2026-10-13', release.start_date), 3);
  assert.equal(C.eventState(release, '2026-10-13').label, '3 天后开始');
  assert.equal(C.daysBetween('2026-02-30', '2026-03-02'), null);
  assert.equal(C.eventState(demo.events.find(row => row.date_precision === 'month'), '2026-10-13').label, '月份已公布');
});

test('closing date and past exhibits are classified correctly', () => {
  const exhibit = demo.events.find(row => row.id === 'demo-art-kyoto-event');
  assert.equal(C.eventState(exhibit, '2026-10-13').label, '还有 5 天结束');
  assert.equal(C.eventState(exhibit, '2026-10-18').label, '今日结束');
  assert.equal(C.eventState(exhibit, '2026-10-19').label, '已结束');
});

test('import validates references, deduplicates bookmarks and excludes gear', () => {
  const bookmark = { id: 'old-id', content_id: 'demo-film', event_id: null, status: 'seen' };
  const data = C.validateImport({ schema_version: 1, preferences: prefs, bookmarks: [bookmark, bookmark] }, demo, prefs);
  assert.equal(data.bookmarks.length, 1);
  assert.ok(data.preferences.excluded_topics.includes('equipment_review'));
  assert.throws(() => C.validateImport({ schema_version: 1, preferences: prefs, bookmarks: [{ ...bookmark, content_id: 'missing' }] }, demo, prefs));
  assert.throws(() => C.validateImport({ schema_version: 1, preferences: prefs, bookmarks: [{ ...bookmark, event_id: 'demo-film-jp' }] }, demo, prefs));
});

test('external links and text cannot inject executable markup', () => {
  assert.equal(C.safeUrl('javascript:alert(1)'), '');
  assert.equal(C.escape('<script>'), '&lt;script&gt;');
  assert.equal(C.safeUrl('https://example.invalid/a'), 'https://example.invalid/a');
});

test('calendar export uses exclusive end dates and folds Unicode by bytes', () => {
  const exhibit = { ...demo.events.find(row => row.id === 'demo-photo-tokyo'), title_zh: '摄影展'.repeat(40) };
  const monthly = demo.events.find(row => row.date_precision === 'month');
  const result = C.calendarFile([exhibit, monthly]);
  assert.match(result, /DTSTART;VALUE=DATE:20261017/);
  assert.match(result, /DTEND;VALUE=DATE:20261130/);
  assert.equal((result.match(/BEGIN:VEVENT/g) || []).length, 1);
  assert.ok(result.split('\r\n').every(line => Buffer.byteLength(line, 'utf8') <= 75));
});

test('global selection balances sources and channels without a default city bias', () => {
  const rows = Array.from({length: 10}, (_, i) => ({id:'film'+i, source_id:'film-source', channel:'film', city:'东京', title_original:'A movie', kind:'news', published_at:'2026-10-13', evidence_status:'media_reported'}));
  rows.push({id:'art',source_id:'art-source',channel:'art',title_original:'An exhibition',kind:'news',evidence_status:'media_reported'}, {id:'photo',source_id:'photo-source',channel:'photography',title_original:'A photograph',kind:'news',evidence_status:'media_reported'});
  const selected=C.selectToday(rows,{...prefs,interests:[],followed_entities:[],default_city:'东京',news_scope:'global',daily_selection_limit:5});
  assert.ok(selected.some(r => r.id==='art'));
  assert.ok(selected.some(r => r.id==='photo'));
  assert.ok(selected.every(r => r.score===0));
});

test('world region and language filters use story places rather than publisher country', () => {
  const row={language:'es',country:null,geography_status:'mentioned',locations_json:JSON.stringify([{country:'FR',city:'巴黎'},{country:'JP',city:'东京'}])};
  assert.ok(C.matches(row,{country:'FR',city:'巴黎',language:'es'}));
  assert.ok(C.matches(row,{country:'JP'}));
  assert.ok(!C.matches(row,{country:'US'}));
  assert.ok(!C.matches(row,{language:'en'}));
  assert.match(C.locationLabel(row),/^涉及/);
  assert.equal(C.locationLabel({country:null}),'地点未说明');
  assert.ok(!C.matches({country:'JP',geography_status:'mentioned'},{city:'东京'}));
  assert.ok(C.matches({country:'JP',event_type:'cinema_release'},{city:'东京'}));
});

test('event countdown uses local dates across UTC midnight in different regions', () => {
  const instant=new Date('2026-10-14T01:00:00Z');
  assert.equal(C.localDate('America/New_York',instant),'2026-10-13');
  assert.equal(C.localDate('Asia/Tokyo',instant),'2026-10-14');
  assert.equal(C.eventState({date_precision:'day',event_type:'exhibition',start_date:'2026-10-14'},C.localDate('America/New_York',instant)).label,'1 天后开幕');
});

test('today excludes archival publications and uses confirmed calendar dates for undated listings', () => {
  const recent={id:'recent',kind:'news',channel:'art',title_original:'Art today',evidence_status:'media_reported',published_at:'2026-10-12T00:00:00Z'};
  const old={...recent,id:'old',published_at:'2021-01-01T00:00:00Z'};
  const unknown={...recent,id:'unknown',published_at:null,fetched_at:'2026-10-13T00:00:00Z'};
  const listing={...unknown,id:'listing'};
  const context={reference_date:'2026-10-13',content_events:[{content_id:'listing',event_id:'exhibit'}],events:[{id:'exhibit',date_precision:'day',start_date:'2026-10-01',end_date:'2026-11-01',is_demo:1}]};
  const rows=C.selectToday([old,unknown,listing,recent],{...prefs,interests:[],followed_entities:[]},context);
  assert.deepEqual(new Set(rows.map(r=>r.id)),new Set(['recent','listing']));
  assert.ok(!C.isCurrentContent({...recent,published_at:'2027-01-01T00:00:00Z'},'2026-10-13'));
  assert.equal(C.matches(old,{}),true);
});

test('exact screening and deadline exports preserve UTC instants rather than turning them into full days', () => {
  const screening={id:'screen',date_precision:'day',event_type:'festival_screening',start_date:'2026-10-17',start_at:'2026-10-17T11:45:00+01:00',timezone:'Europe/London',title_original:'A film',evidence_url:'https://example.invalid/film'};
  const call={id:'call',date_precision:'day',event_type:'call_deadline',start_date:'2027-01-05',deadline_at:'2027-01-05T16:00:00+00:00',timezone:'UTC',title_original:'Photography call',evidence_url:'https://example.invalid/call'};
  const result=C.calendarFile([screening,call]);
  assert.match(result,/DTSTART:20261017T104500Z/);assert.match(result,/DTSTART:20270105T160000Z/);assert.ok(!result.includes('DTSTART;VALUE=DATE'));
  assert.equal(C.eventState(call,'2027-01-05',new Date('2027-01-05T16:00:01Z')).label,'已截止');
  assert.equal(C.eventState({...call,deadline_at:null,time_status:'conflict'},'2027-01-05',new Date('2027-01-05T10:00:00Z')).label,'今日截止 · 时刻需核对');
});

test('reading prefers completed Chinese and directly falls back to saved original', () => {
  const row = { title_original: 'A photo exhibition', translated_title_zh: '摄影展', translated_excerpt_zh: '城市摄影作品', excerpt_original: 'Original introduction', canonical_url: 'https://example.org/story' };
  assert.equal(C.displayTitle(row), 'A photo exhibition');
  assert.equal(C.readingSummary(row), 'Original introduction');
  row.editorial_status='reviewed'; row.editorial_title_zh='摄影展'; row.editorial_excerpt_zh='城市摄影作品'; row.editorial_blocks_json=JSON.stringify([{type:'paragraph',text:'已校对的正文'}]);
  assert.equal(C.displayTitle(row), '摄影展');
  assert.equal(C.readingSummary(row), '城市摄影作品');
  assert.equal(C.matches(row, { query: '城市摄影' }), true);
  assert.equal(C.safeImageUrl('javascript:alert(1)'), '');
  assert.equal(C.safeImageUrl('https://user:pass@example.org/image.jpg'), '');
  assert.equal(C.safeImageUrl('https://127.0.0.1/image.jpg'), '');
  assert(C.translatedArticleUrl(row).includes(encodeURIComponent(row.canonical_url)));
  assert.equal(C.displayTitle({ ...row, editorial_status: null, title_zh: '人工中文标题' }), '人工中文标题');
});

test('original reader links preserve the source and routes survive refresh and malformed hashes', () => {
  const row = { canonical_url: 'https://source.example/story', original_page_url: 'https://source.example/story?context=original' };
  assert.equal(C.originalPageUrl(row), row.original_page_url);
  assert.equal(C.matches({ ...row, original_embed_status: 'blocked' }, {}), true);
  assert.equal(C.originalPageUrl({ canonical_url: 'javascript:alert(1)' }), '');
  assert.deepEqual(C.parseRoute(C.readerRoute('live-example')), { view: 'reader', id: 'live-example' });
  assert.deepEqual(C.parseRoute('#reader/%broken'), { view: 'today' });
  assert.deepEqual(C.parseRoute('#calendar'), { view: 'calendar' });
});

test('stored body blocks display without executable links and search uses the original body', () => {
  const row = { title_original:'A festival', article_text:'Original body about cinematography', article_blocks_json: JSON.stringify([
    {type:'paragraph',text:'<script>Unsafe markup remains plain text</script>',links:[{text:'bad',url:'javascript:alert(1)'},{text:'source',url:'https://example.com/article'}]},
    {type:'image',url:'data:text/html,bad'}, {type:'image',url:'https://example.com/photo.jpg'}, {type:'script',text:'bad'}
  ]) };
  const blocks = C.articleBlocks(row);
  assert.equal(blocks.length,2); assert.equal(blocks[0].links.length,1);
  assert.equal(blocks[1].url,'https://example.com/photo.jpg');
  assert.ok(C.escape(blocks[0].text).startsWith('&lt;script&gt;'));
  assert.ok(C.matches(row,{query:'cinematography'}));
  assert.deepEqual(C.articleBlocks({article_blocks_json:'broken'}),[]);
});


test('draft or legacy body translation is never presented as reviewed copy', () => {
  const row={title_original:'Original',translated_title_zh:'旧机翻标题',article_translation_json:'[{"type":"paragraph","text":"旧机翻正文"}]',editorial_status:'draft',editorial_title_zh:'未校对标题',editorial_blocks_json:'[{"type":"paragraph","text":"未审核初稿"}]'};
  assert.equal(C.displayTitle(row),'Original');
  assert.deepEqual(C.articleBlocks(row,true),[]);
  row.editorial_status='reviewed';assert.equal(C.displayTitle(row),'未校对标题');assert.equal(C.articleBlocks(row,true)[0].text,'未审核初稿');
});


test('reviewed title-only packs support Chinese search but never imply full-body review', () => {
  const row={id:'headline',language:'en',title_original:'An exhibition',excerpt_original:'Foreign excerpt'};
  globalThis.CULTURE_BOOTSTRAP={headlines:{headline:{source_title:'An exhibition',title_zh:'一场展览'}}};
  assert.equal(C.displayTitle(row),'一场展览'); assert.ok(C.matches(row,{query:'一场展览'}));
  assert.equal(C.editorialReady(row),false); assert.deepEqual(C.articleBlocks(row,true),[]);
  assert.equal(C.displayTitle({...row,title_original:'Updated exhibition'}),'Updated exhibition');
  assert.equal(C.displayTitle({language:'zh',title_original:'中文原生报道'}),'中文原生报道');
  delete globalThis.CULTURE_BOOTSTRAP;
});

test('direct AI translation is readable without pretending a bilingual review and priority filters match', () => {
  const row={id:'direct',title_original:'A story',editorial_status:'translated',editorial_title_zh:'一篇报道',editorial_blocks_json:'[{"type":"paragraph","text":"AI译文"}]'};
  assert.ok(C.editorialReady(row));assert.equal(C.articleBlocks(row,true)[0].text,'AI译文');assert.equal(C.displayTitle(row),'一篇报道');
  globalThis.CULTURE_BOOTSTRAP={priorities:{direct:{source_title:'A story',priority:'P0',label:'紧急'}}};
  assert.equal(C.priorityRank(row),0);assert.ok(C.matches(row,{priority:'P0'}));assert.ok(!C.matches(row,{priority:'P1'}));
  assert.equal(C.priorityOf({...row,title_original:'Updated'}),null);
  delete globalThis.CULTURE_BOOTSTRAP;
});

test('today lowers ordinary foreign exhibitions without hiding inventory or major exhibitions', () => {
  const ordinary={id:'ordinary-exhibit',title_original:'An exhibition',channel:'art',kind:'news',source_id:'a',evidence_status:'media_reported',published_at:'2026-10-14'};
  const major={...ordinary,id:'major-exhibit',source_id:'b',published_at:'2026-10-13'};
  const previous=global.CULTURE_BOOTSTRAP;
  global.CULTURE_BOOTSTRAP={priorities:{[ordinary.id]:{source_title:ordinary.title_original,priority:'P3',exhibition_deprioritized:true,recommendation_penalty:12},[major.id]:{source_title:major.title_original,priority:'P0',recommendation_penalty:0}}};
  try {
    const selected=C.selectToday([ordinary,major],{...prefs,daily_selection_limit:1,interests:[],followed_entities:[]});
    assert.equal(selected[0].id,major.id);
    assert.equal(C.matches(ordinary,{}),true);
    const both=C.selectToday([ordinary,major],{...prefs,daily_selection_limit:2,interests:[],followed_entities:[]});
    assert.equal(both.length,2);assert.match(both.find(r=>r.id===ordinary.id).selection_reason,/稍后阅读/);
  } finally { if(previous===undefined)delete global.CULTURE_BOOTSTRAP;else global.CULTURE_BOOTSTRAP=previous; }
});

test('compact browser payload keeps full original-body search and invalidates its derived text cache',()=>{
  const blocks=JSON.stringify([{type:'paragraph',text:'An unabridged river report.'},{type:'image',url:'https://example.org/a.jpg'},{type:'quote',text:'A second original statement.'}]);
  const row={id:'search',title_original:'A story',article_blocks_json:blocks};
  const full={...row,article_text:'An unabridged river report.\n\nA second original statement.'};
  assert.equal(C.sourceText(row),full.article_text);
  for(const query of ['unabridged river','second original','missing term'])assert.equal(C.matches(row,{query}),C.matches(full,{query}));
  row.article_blocks_json='[{"type":"paragraph","text":"Updated original content."}]';
  assert.equal(C.matches(row,{query:'updated original'}),true);assert.equal(C.matches(row,{query:'unabridged river'}),false);
});

test('verified offline machine copy is readable separately from AI and stale or legacy copy stays hidden',()=>{
 const row={id:'machine',language:'en',title_original:'Original',article_blocks_json:'[{"type":"paragraph","text":"Original body"}]',article_translation_provider:'offline-m2m100:pinned:v1',translation_status:'machine',article_translation_hash:'bound-source',article_translation_json:'[{"type":"paragraph","text":"自动机翻正文","translated":true}]',translated_title_zh:'自动标题',machine_translation_ready:true};
 assert.equal(C.editorialReady(row),false);assert.equal(C.machineReady(row),true);assert.equal(C.articleBlocks(row,true)[0].text,'自动机翻正文');assert.equal(C.displayTitle(row),'自动标题');assert.ok(C.matches(row,{query:'自动机翻正文'}));
 assert.equal(C.machineReady({...row,machine_translation_ready:false}),false);assert.deepEqual(C.articleBlocks({...row,machine_translation_ready:false},true),[]);
 assert.equal(C.machineReady({...row,article_translation_provider:'google-public'}),false);
 const ai={...row,editorial_status:'translated',editorial_title_zh:'AI标题',editorial_blocks_json:'[{"type":"paragraph","text":"AI全文"}]'};
 assert.equal(C.displayTitle(ai),'AI标题');assert.equal(C.articleBlocks(ai,true)[0].text,'AI全文');
});

test('headline readiness rejects machine/title-only/incomplete bodies and respects server validation',()=>{
 const original=JSON.stringify([{type:'paragraph',text:'Original 2026'}]);
 const row={language:'en',article_blocks_json:original,editorial_status:'translated',editorial_title_zh:'中文标题',editorial_blocks_json:JSON.stringify([{type:'paragraph',text:'中文正文2026'}])};
 assert.equal(C.headlineReady(row),true);
 assert.equal(C.headlineReady({...row,editorial_status:null,title_zh:'中文标题'}),false);
 assert.equal(C.headlineReady({...row,editorial_status:null,translation_status:'machine',article_translation_json:row.editorial_blocks_json}),false);
 assert.equal(C.headlineReady({...row,editorial_blocks_json:'[]'}),false);
 assert.equal(C.headlineReady({...row,headline_ready:false}),false);
 assert.equal(C.headlineReady({...row,language:'zh',editorial_status:null,editorial_blocks_json:null}),true);
 assert.equal(C.headlineReady({...row,article_blocks_json:null}),false);
});
