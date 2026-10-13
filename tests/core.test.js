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
