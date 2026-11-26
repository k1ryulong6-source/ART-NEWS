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
const important = {tier:3, programme:3, support:1};

test('a small show closing tomorrow survives independent of importance and canceled or stale dates do not alert', () => {
  const ordinary = row('local', { end_date: '2026-11-26' });
  const big = row('biennale', { recommendation: important });
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
  const top = row('festival',{recommendation:important,venue:'館A'});
  const special = row('special',{recommendation:{tier:2,programme:1,support:1}});
  const future = row('future',{recommendation:important,start_date:'2026-12-02'});
  const next = row('opening-tomorrow',{start_date:'2026-11-26'});
  const all = [...regular,top,special,future,next];
  const active = X.rank(C,all,new Map(),{...filters,stage:'top'});
  assert.equal(active.length,100);
  assert.deepEqual(active.slice(0,2).map(r=>r.id),['festival','special']);
  assert.ok(active.every(r=>r.phase === 'active'));
  assert.deepEqual(X.rank(C,all,new Map(),{...filters,stage:'upcoming',sort:'new'}).map(r=>r.id),['future','opening-tomorrow']);
  assert.equal(X.rank(C,all,new Map(),filters).length,114);
});

test('format words and closing soon do not determine recommendation grades or order', () => {
  const older = row('older',{flags:['festival','special'],start_date:'2026-09-01',end_date:'2026-11-26'});
  const recent = row('recent',{start_date:'2026-11-24'});
  const ranked = X.rank(C,[older,recent],new Map(),{...filters,stage:'top'});
  assert.deepEqual(ranked.map(r=>[r.id,r.importance]),[['recent',1],['older',1]]);
  assert.deepEqual(X.rank(C,[older,recent],new Map(),{...filters,stage:'closing'}).map(r=>r.id),['older']);
});

test('one edition takes one recommendation spot and older personal records can still be opened', () => {
  const primary = row('primary',{duplicate_group:'primary'});
  const alias = row('alias',{duplicate_group:'primary'});
  const items = [alias,primary];
  assert.deepEqual(X.rank(C,items,new Map(),filters).map(r=>r.id),['primary']);
  const saved = new Map([['alias',{status:'want',favorite:true}]]);
  assert.deepEqual(X.rank(C,items,saved,{...filters,stage:'top'}).map(r=>r.id),['alias']);
  assert.deepEqual(X.rank(C,items,saved,{...filters,personal:'favorite'}).map(r=>r.id),['alias']);
  saved.set('alias',{status:'uninterested',favorite:true});
  assert.deepEqual(X.rank(C,items,saved,filters),[]);
  assert.deepEqual(X.rank(C,items,saved,{...filters,personal:'uninterested'}).map(r=>r.id),['alias']);
});

test('confirmed lectures leave exhibition lists and reminders while one-day exhibits remain eligible', () => {
  const dates = {start_date:today,end_date:today};
  const talk = row('talk',{...dates,related_event:'讲座'});
  const show = row('display',dates);
  const saved = new Map([['talk',{favorite:true}]]);
  for (const stage of ['all','top','closing']) {
    assert.deepEqual(X.rank(C,[talk,show],saved,{...filters,stage}).map(r=>r.id),['display']);
  }
  assert.deepEqual(X.rank(C,[talk,show],saved,{...filters,personal:'favorite'}).map(r=>r.id),['talk']);
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
  const older = row('older',{venue_id,start_date:'2026-10-01',recommendation:important});
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
