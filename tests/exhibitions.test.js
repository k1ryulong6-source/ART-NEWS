const assert = require('node:assert/strict');
const test = require('node:test');
const C = require('../frontend/core.js');
const X = require('../frontend/exhibitions.js');

const today = '2026-11-25';
const row = (id, extra = {}) => ({
  id, title_original: id, country: 'JP', prefecture: '13', venue: id, timezone: 'Asia/Tokyo',
  start_date: '2026-11-18', end_date: '2026-12-20', date_precision: 'day', last_seen: today,
  status: 'scheduled', types: ['installation'], ...extra
});
const filters = { scope: 'JP', prefecture: 'all', medium: 'all', stage: 'all', personal: 'all',
  query: '', sort: 'recommended', today: () => today };

test('a small show closing tomorrow survives independent of importance and canceled or stale dates do not alert', () => {
  const ordinary = row('local', { end_date: '2026-11-26' });
  const big = row('biennale', { flags: ['festival'] });
  const paused = row('cancelled', { end_date: '2026-11-26', status: 'cancelled' });
  const stale = row('stale', { end_date: '2026-11-26', last_seen: '2026-10-11' });
  assert.deepEqual(X.rank(C,[ordinary,big,paused,stale],new Map(),{...filters,stage:'closing'}).map(r => r.id), ['local']);
  assert.equal(X.rank(C,[ordinary,big],new Map(),filters)[0].id,'biennale');
});

test('conflicting credible dates surface the earlier risk and keep the underlying item', () => {
  const exhibit = row('work', { date_conflict: true, evidence: [
    { source:'museum', start:'2026-11-18', end:'2026-12-20', last_seen:today, status:'scheduled' },
    { source:'directory', start:'2026-11-18', end:'2026-11-27', last_seen:today, status:'scheduled' }
  ]});
  assert.equal(X.closingDays(C,exhibit,today),2);
});

test('top 100 fills the ranking in importance order and the upcoming ranking has its own eligible shows', () => {
  const regular = Array.from({length:110},(_,i)=>row(`tokyo-${i}`,{venue:'館A'}));
  const top = row('festival',{flags:['festival'],venue:'館A'});
  const special = row('special',{flags:['special']});
  const future = row('future',{flags:['retrospective'],start_date:'2026-12-02'});
  const next = row('opening-tomorrow',{start_date:'2026-11-26'});
  const all = [...regular,top,special,future,next];
  const active = X.rank(C,all,new Map(),{...filters,stage:'top'});
  assert.equal(active.length,100);
  assert.deepEqual(active.slice(0,2).map(r=>r.id),['festival','special']);
  assert.ok(active.every(r=>r.phase === 'active'));
  assert.deepEqual(X.rank(C,all,new Map(),{...filters,stage:'upcoming',sort:'new'}).map(r=>r.id),['future','opening-tomorrow']);
  assert.equal(X.rank(C,all,new Map(),filters).length,114);
});

test('hidden shows only appear in the dedicated view, including when favorited or otherwise recommended', () => {
  const venue_id = 'venue-' + 'a'.repeat(24);
  const hidden = row('regional-hidden',{venue_id,flags:['festival'],end_date:'2026-11-26'});
  const records = new Map([[hidden.id,{status:'uninterested',favorite:true}]]);
  const venues = new Map([[venue_id,{}]]);
  for (const options of [filters,{...filters,stage:'top'},{...filters,stage:'closing'},{...filters,query:hidden.id},
    {...filters,personal:'favorite'},{...filters,personal:'records'},{...filters,personal:'venues',venues}]) {
    assert.equal(X.rank(C,[hidden],records,options).length,0);
  }
  assert.equal(X.rank(C,[hidden],records,{...filters,personal:'uninterested'})[0].id,hidden.id);
});

test('followed venue promotes newly open and future exhibitions while preserving the general importance grades', () => {
  const venue_id = 'venue-' + 'b'.repeat(24), venues = new Map([[venue_id,{}]]);
  const older = row('older',{venue_id,start_date:'2026-10-01',flags:['retrospective']});
  const newShow = row('new-show',{venue_id});
  const future = row('future',{venue_id,start_date:'2026-12-15'});
  const permanent = row('permanent',{venue_id,flags:['permanent']});
  const all = [older,newShow,future,permanent];
  const result = X.rank(C,all,new Map(),{...filters,personal:'venues',venues});
  assert.deepEqual(result.filter(r=>r.followedNew).map(r=>r.id),['new-show','future']);
  assert.ok(result.slice(0,2).every(r=>r.followedNew));
  assert.equal(X.rank(C,all,new Map(),{...filters,stage:'top',venues})[0].id,'older');
});

test('private backups retain independent favorite, rating and note fields and reject invalid values', () => {
  const value = { format:'culture-desk-exhibition-log-v1', records: [
    { id:'jp-ex-example', status:'visited', favorite:true, rating:4, note:'展厅里的装置', title:'艺术展' }
  ]};
  assert.deepEqual(X.parseLog(value).get('jp-ex-example'), value.records[0]);
  assert.equal(X.parseVenues(value).size,0);
  const venue = {id:'venue-'+'a'.repeat(24),name:'国立新美術館',place:'东京'};
  assert.deepEqual(X.parseVenues({...value,venues:[venue]}).get(venue.id),venue);
  assert.throws(()=>X.parseVenues({...value,venues:[venue,venue]}),/无效/);
  assert.throws(()=>X.parseLog({...value,records:[{...value.records[0],rating:6}]}), /无效/);
  assert.equal(C.parseRoute('#exhibitions').view,'exhibitions');
});
