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

test('exhibit highlights limit repeated venues and prefectures, and excluded personal states are searchable', () => {
  const items = [
    row('tokyo-1',{flags:['festival'],venue:'館A'}), row('tokyo-2',{flags:['festival'],venue:'館A'}),
    row('tokyo-3',{flags:['festival']}), row('tokyo-4',{flags:['festival']}),
    row('hiroshima',{flags:['retrospective'],prefecture:'34'}), row('regional-hidden',{flags:['festival'],prefecture:'01'})
  ];
  const records = new Map([['regional-hidden',{status:'uninterested',favorite:true}]]);
  const ranked = X.rank(C,items,records,filters);
  const picks = X.spotlight(ranked);
  assert.ok(picks.some(r => r.id === 'hiroshima'));
  assert.equal(picks.filter(r => r.prefecture === '13').length,2);
  assert.equal(picks.filter(r=>r.venue === '館A').length,1);
  assert.ok(!picks.some(r => r.id === 'regional-hidden'));
  assert.equal(X.rank(C,items,records,{...filters,personal:'uninterested'})[0].id,'regional-hidden');
  assert.equal(X.rank(C,items,records,{...filters,personal:'favorite'})[0].id,'regional-hidden');
});

test('private backups retain independent favorite, rating and note fields and reject invalid values', () => {
  const value = { format:'culture-desk-exhibition-log-v1', records: [
    { id:'jp-ex-example', status:'visited', favorite:true, rating:4, note:'展厅里的装置', title:'艺术展' }
  ]};
  assert.deepEqual(X.parseLog(value).get('jp-ex-example'), value.records[0]);
  assert.throws(()=>X.parseLog({...value,records:[{...value.records[0],rating:6}]}), /无效/);
  assert.equal(C.parseRoute('#exhibitions').view,'exhibitions');
});
