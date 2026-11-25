const assert = require('node:assert/strict');
const test = require('node:test');
const Cal = require('../frontend/calendar.js');

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
  assert.ok(!Cal.inArea(film,'tokyo','film'));
  assert.equal(Cal.deduplicate([film,canada,second]).length,3);
  assert.ok(Cal.inArea(slot('national',{event_type:'cinema_release',city:null,venue:null}),'tokyo','cinema_release'));
  assert.ok(!Cal.inArea(slot('osaka',{city:'大阪'}),'tokyo','film'));
});

test('calendar shows only opening and closing edges, keeps month-only titles and leaves canceled dates off the grid', () => {
  const exhibition = slot('exhibition',{event_type:'exhibition',start_at:null,start_date:'2026-11-02',end_date:'2026-11-30'});
  const beyond = {...exhibition,id:'continues',start_date:'2026-10-05',end_date:'2026-12-30'};
  const monthOnly = slot('month-only',{date_precision:'month',start_at:null,event_type:'streaming_release',start_date:'2026-11'});
  const calledOff = slot('cancelled',{status:'cancelled'});
  assert.deepEqual(Cal.calendarEntries([exhibition,beyond,monthOnly,calledOff],'2026-11').map(n=>[n.row.id,n.day,n.label]),[
    ['exhibition','2026-11-02','开展'],['exhibition','2026-11-30','闭展'],['month-only',null,'仅公布月份']
  ]);
});
