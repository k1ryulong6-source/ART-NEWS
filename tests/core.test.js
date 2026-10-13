const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const C = require('../frontend/core.js');
const demo = JSON.parse(fs.readFileSync(new URL('../data/demo.json', 'file://' + __filename), 'utf8'));
const prefs = JSON.parse(fs.readFileSync(new URL('../config/preferences.json', 'file://' + __filename), 'utf8'));

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

test('reading uses Chinese translations, searches source excerpts and validates photo/fulltext links', () => {
  const row = { title_original: 'A photo exhibition', translated_title_zh: '摄影展', translated_excerpt_zh: '城市摄影作品', excerpt_original: 'Original introduction', canonical_url: 'https://example.org/story' };
  assert.equal(C.displayTitle(row), '摄影展');
  assert.equal(C.readingSummary(row), '城市摄影作品');
  assert.equal(C.matches(row, { query: '城市摄影' }), true);
  assert.equal(C.safeImageUrl('javascript:alert(1)'), '');
  assert.equal(C.safeImageUrl('https://user:pass@example.org/image.jpg'), '');
  assert.equal(C.safeImageUrl('https://127.0.0.1/image.jpg'), '');
  assert(C.translatedArticleUrl(row).includes(encodeURIComponent(row.canonical_url)));
  assert.equal(C.displayTitle({ ...row, title_zh: '人工中文标题' }), '人工中文标题');
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
