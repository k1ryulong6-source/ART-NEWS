const assert = require('node:assert/strict');
const test = require('node:test');
const Cal = require('../frontend/calendar.js');
const C = require('../frontend/core.js');

const slot = (id, fields = {}) => ({
  id, title_original:'海辺の映画', event_type:'cinema_screening', country:'JP', city:'东京', venue:'映画館',
  start_date:'2026-11-30', start_at:'2026-11-30T12:00:00+09:00', date_precision:'day',
  evidence_url:'https://example.org/'+id, ...fields
});

test('equal title, local day, room and instant collapse while two slots and other cinemas stay distinct', () => {
  const main = slot('a', {evidence_status:'official_confirmed',auditorium:'スクリーン1'});
  const repeat = slot('b', {start_at:'2026-11-30T03:00:00Z',auditorium:'スクリーン1'});
  const others = [
    slot('later',{start_at:'2026-11-30T16:00:00+09:00',auditorium:'スクリーン1'}),
    slot('other-room',{auditorium:'スクリーン2'}),
    slot('other-place',{venue:'別館',auditorium:'スクリーン1'})
  ];
  const events = Cal.deduplicate([repeat, main, ...others]);
  assert.equal(events.length,4);
  assert.equal(events[0].id,'a');
  assert.equal(events[0].origins.length,2);
});

test('streaming view uses all territories and preserves editions from other platforms and markets', () => {
  const film = slot('apple', {event_type:'streaming_release',platform:'Apple TV',country:'US',market:'美国',start_at:null});
  const canada = {...film,id:'ca',country:'CA',market:'加拿大'};
  const second = {...film,id:'criterion',platform:'Criterion Channel'};
  assert.ok(Cal.inArea(film,'tokyo','streaming_release'));
  assert.ok(Cal.inArea(film,'tokyo','all'));
  assert.ok(!Cal.inArea(film,'tokyo','film'));
  assert.equal(Cal.deduplicate([film,canada,second]).length,3);
  assert.ok(Cal.inArea(slot('national',{event_type:'cinema_release',city:null,venue:null}),'tokyo','cinema_release'));
  assert.ok(!Cal.inArea(slot('osaka',{city:'大阪'}),'tokyo','film'));
});

test('the same Japanese streaming announcement gains its platform and retained poster without duplication', () => {
  const first = slot('legacy',{event_type:'streaming_release',start_at:null,evidence_status:'official_confirmed'});
  const update = {...first,id:'more',source_id:'eiga-releases',market:'日本',platform:'Netflix',
    evidence_status:'media_reported',poster_url:'https://example.org/poster.jpg'};
  const canada = {...update,id:'other',country:'CA',market:'加拿大'};
  const items = Cal.deduplicate([first,update,canada]);
  assert.equal(items.length,2);
  assert.equal(items[0].id,first.id);
  assert.equal(items[0].platform,'Netflix');
  assert.equal(items[0].poster_url,update.poster_url);
});

test('calendar shows only opening and closing edges, keeps month-only titles and leaves canceled dates off the grid', () => {
  const exhibition = slot('exhibition',{event_type:'exhibition',start_at:null,start_date:'2026-11-02',end_date:'2026-11-30'});
  const beyond = {...exhibition,id:'continues',start_date:'2026-10-05',end_date:'2026-12-30'};
  const monthOnly = slot('month-only',{date_precision:'month',start_at:null,event_type:'streaming_release',start_date:'2026-11'});
  const calledOff = slot('cancelled',{status:'cancelled'});
  const photoCall = slot('photo-call',{event_type:'call_deadline'});
  const inCinemas = slot('in-cinemas',{event_type:'cinema_release',start_date:null});
  assert.deepEqual(Cal.calendarEntries([exhibition,beyond,monthOnly,calledOff,photoCall,inCinemas],'2026-11').map(n=>[n.row.id,n.day,n.label]),[
    ['exhibition','2026-11-02','开展'],['exhibition','2026-11-30','闭展'],['month-only',null,'仅公布月份']
  ]);
});

test('film groups combine sessions without merging venues, dates or two editions with the same title', () => {
  const verified = {douban_id:'123',title_zh:'海边的电影',original_title:'The Film by the Sea'};
  const movie = slot('a',{movie:verified,booking_url:'https://example.org/ticket-a'});
  const events = [
    movie, {...movie,id:'b',start_at:'2026-11-30T17:00:00+09:00',booking_url:'https://example.org/ticket-b'},
    {...movie,id:'other-room',venue:'第二映画館'},
    {...movie,id:'other-film',movie:{...verified,douban_id:'456'}},
    {...movie,id:'different-date',start_date:'2026-11-29',start_at:'2026-11-29T12:00:00+09:00'}
  ];
  const groups = Cal.groupSchedule(Cal.calendarEntries(events,'2026-11'));
  assert.equal(groups.length,4);
  assert.deepEqual(groups.find(group=>group.row.id==='a').screenings.map(row=>row.booking_url),
    ['https://example.org/ticket-a','https://example.org/ticket-b']);
  assert.equal(Cal.entryTitle(movie), '海边的电影');
  assert.equal(Cal.entryTitle({...movie,movie:{original_title:'The Film by the Sea'},title_zh:'旧译名'}), 'The Film by the Sea');
  assert.equal(Cal.entryTitle({...movie,movie:undefined,title_zh:'旧译名'}), '海辺の映画');
});

test('grouped screenings retain artwork from later slots and duplicate official sources', () => {
  const first = slot('first',{movie:{douban_id:'123',title_zh:'海边的电影'}});
  const artwork = {douban_id:'123',artwork_url:'https://example.org/still.jpg',artwork_kind:'still'};
  const sameSlot = slot('repeat',{movie:artwork});
  const next = slot('next',{movie:artwork,start_at:'2026-11-30T15:00:00+09:00'});
  const [merged] = Cal.deduplicate([first,sameSlot]);
  assert.equal(merged.movie.title_zh,'海边的电影');
  assert.equal(merged.movie.artwork_url,artwork.artwork_url);
  const [group] = Cal.groupSchedule(Cal.calendarEntries([first,next],'2026-11'));
  assert.equal(group.row.movie.artwork_url,artwork.artwork_url);
  assert.equal(group.screenings.length,2);
});

test('the event reader renders only supplied facts and joins the correct local screening times', t => {
  const previousDocument = global.document;
  global.document = { addEventListener() {} };
  t.after(() => { global.document = previousDocument; });
  const release = slot('release',{event_type:'cinema_release',start_at:null,city:null,venue:null,price_text:null});
  const programme = 'https://example.org/programme';
  const first = slot('first',{timezone:'Asia/Tokyo',source_id:'museum',start_at:'2026-11-30T03:00:00Z',programme_url:programme});
  const last = slot('last',{...first,id:'last',start_at:'2026-11-30T07:30:00Z',booking_url:'https://example.org/ticket'});
  const catalogued = {...release,id:'eiga-showing-123',start_date:null,booking_url:'https://example.org/theatres'};
  const boot = {film_calendar:{items:[first,last],now_showing:[catalogued]}};
  const schedule = Cal.create({C,boot,server:false});
  const dataset = {mode:'live',events:[release]};
  const options = {relatedImage:()=>'',save:''};
  const detail = schedule.detail(dataset,'release',[],options).html;
  assert.match(detail, /2026\.11\.30/);
  assert.doesNotMatch(detail, /待确认|日期精度|原文|calendar-reader-times|calendar-reader-cover/);
  const screenings = schedule.detail(dataset,'last',[],options).html;
  assert.match(screenings, /12:00<\/time>/);
  assert.match(screenings, /16:30<\/time>/);
  assert.match(screenings, /https:\/\/example\.org\/ticket/);
  const showing = schedule.detail(dataset,catalogued.id,[],options).html;
  assert.match(showing, /查场次/);
  assert.doesNotMatch(showing, /2026\.|calendar-reader-times/);
});
